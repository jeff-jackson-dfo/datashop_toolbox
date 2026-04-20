"""
qc_ctd_data.py
--------------
Interactive visual QC tool for CTD ODF files.

Key differences from qc_thermograph_data.py:
  - Plot is a profile view: Pressure (or Depth) on the Y-axis (inverted,
    so surface is at the top), and a selectable parameter on the X-axis
    (default: Temperature).
  - No metadata file is required or used.  The QC window covers the full
    cast; no deploy/recover masking is applied.
  - No organisation-specific branching (DFO BIO / FSRS).
  - Input selection dialog has no metadata file picker.
"""

import json
import logging
import os
import pathlib
import re
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

# from datashop_toolbox.gui.qc_window import QCWindow
from datashop_toolbox.log_window import LogWindowCTDQC, SafeConsoleFilter
from datashop_toolbox.odfhdr import OdfHeader  # CTD ODF reader

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
log_dir = Path.cwd() / "logs"
log_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"datashop_CTD_QC_log_{timestamp}.txt"

ctd_logger = logging.getLogger("ctd_qc_logger")
ctd_logger.setLevel(logging.INFO)
ctd_logger.propagate = False
if not ctd_logger.handlers:
    _ch = logging.StreamHandler()
    _ch.addFilter(SafeConsoleFilter())
    _ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    ctd_logger.addHandler(_ch)
    _fh = logging.FileHandler(log_file, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    ctd_logger.addHandler(_fh)
    ctd_logger.info("Logger file initialized.")

# Module-level exit flag
exit_requested = False

# ---------------------------------------------------------------------------
# QC flag tables (identical to thermograph tool)
# ---------------------------------------------------------------------------
FLAG_LABELS: dict[int, str] = {
    0: "No QC",
    1: "Correct",
    2: "Inconsistent",
    3: "Doubtful",
    4: "Erroneous",
    5: "Modified",
}

FLAG_COLORS: dict[int, str] = {
    0: "#808080",
    1: "#02590F",
    2: "#B59410",
    3: "#8B008B",
    4: "#FF0000",
    5: "#00008B",
}

# Preferred pressure / depth column names (checked in order)
_PRES_CANDIDATES = ["PRES_01", "PRES_02", "DEPH_01", "DEPH_02"]

# Preferred temperature column names (used as default x-axis)
_TEMP_CANDIDATES = ["TEMP_01", "TE90_01", "TEMP_02"]


# ---------------------------------------------------------------------------
# Input selection dialog  (no metadata file)
# ---------------------------------------------------------------------------
class CTDInputDialog(QMainWindow):
    """Simple input dialog for CTD QC: operator name, input/output folders,
    wildcard, and review-mode selection.  No metadata file required."""

    def __init__(self, review_mode: bool):
        super().__init__()
        self.review_mode = review_mode
        self.setWindowTitle(
            "CTD QC Toolbox — ODF Quality Flagging "
            f"({'Review' if review_mode else 'Initial'} QC Mode)"
        )
        self.resize(650, 280)

        # Persistent storage
        _base = Path(__file__).resolve().parent / "temporary"
        _base.mkdir(parents=True, exist_ok=True)
        self._meta_store = _base / ".last_ctd_qc_reviewer.json"

        # Attributes read by the caller
        self.line_edit_text = ""
        self.input_data_folder = ""
        self.output_data_folder = ""
        self.wildcard_string = "*.ODF"
        self.result = None

        # ── Widgets ──────────────────────────────────────────────────────
        _lbl_font_size = 11

        self._name_lbl = QLabel(
            "QC reviewer name:" if review_mode else "QC operator name:"
        )
        self._name_edit = QLineEdit()
        self._name_edit.setFixedHeight(28)
        self._name_edit.editingFinished.connect(self._on_name_edited)

        self._remember_cb = QCheckBox(
            "Remember last reviewer name" if review_mode else "Remember last operator name"
        )

        input_lbl_text = (
            "Select folder containing Step_2_Assign_QFlag ODF files (previously flagged):"
            if review_mode
            else "Select folder containing Step_1_Create_ODF files (unflagged):"
        )
        self._input_lbl = QLabel(input_lbl_text)
        self._input_btn = QPushButton("Choose ODF Input Folder")
        self._input_btn.setFixedSize(200, 36)
        self._input_btn.clicked.connect(self._choose_input)
        self._input_path = QLineEdit()
        self._input_path.setReadOnly(True)

        self._output_lbl = QLabel("Select output folder to save QC ODF files:")
        self._output_btn = QPushButton("Choose Output Folder")
        self._output_btn.setFixedSize(200, 36)
        self._output_btn.clicked.connect(self._choose_output)
        self._output_path = QLineEdit()
        self._output_path.setReadOnly(True)

        self._wc_lbl = QLabel("File wildcard (e.g. *.ODF):")
        self._wc_edit = QLineEdit("*.ODF")
        self._wc_edit.setFixedWidth(160)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self._btn_box = QDialogButtonBox(buttons)
        self._btn_box.accepted.connect(self._on_accept)
        self._btn_box.rejected.connect(self._on_reject)

        # ── Layout ───────────────────────────────────────────────────────
        layout = QVBoxLayout()

        row_name = QHBoxLayout()
        row_name.addWidget(self._name_lbl)
        row_name.addStretch()
        row_name.addWidget(self._remember_cb)
        layout.addLayout(row_name)
        layout.addWidget(self._name_edit)

        row_in_lbl = QHBoxLayout()
        row_in_lbl.addWidget(self._input_lbl)
        layout.addLayout(row_in_lbl)
        row_in = QHBoxLayout()
        row_in.addWidget(self._input_btn)
        row_in.addWidget(self._input_path)
        layout.addLayout(row_in)

        row_out_lbl = QHBoxLayout()
        row_out_lbl.addWidget(self._output_lbl)
        layout.addLayout(row_out_lbl)
        row_out = QHBoxLayout()
        row_out.addWidget(self._output_btn)
        row_out.addWidget(self._output_path)
        layout.addLayout(row_out)

        row_wc = QHBoxLayout()
        row_wc.addWidget(self._wc_lbl)
        row_wc.addWidget(self._wc_edit)
        row_wc.addStretch()
        layout.addLayout(row_wc)

        row_btns = QHBoxLayout()
        row_btns.addStretch()
        row_btns.addWidget(self._btn_box)
        row_btns.addStretch()
        layout.addLayout(row_btns)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._load_saved()

    def _on_name_edited(self):
        self.line_edit_text = self._name_edit.text().strip()

    def _choose_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Select ODF input folder")
        if folder:
            self.input_data_folder = folder
            self._input_path.setText(folder)

    def _choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select QC output folder")
        if folder:
            self.output_data_folder = folder
            self._output_path.setText(folder)

    def _on_accept(self):
        self.line_edit_text = self._name_edit.text().strip()
        self.wildcard_string = self._wc_edit.text().strip() or "*.ODF"
        if not self.line_edit_text:
            QMessageBox.warning(self, "Missing input", "Please enter an operator/reviewer name.")
            return
        if not self.input_data_folder:
            QMessageBox.warning(self, "Missing input", "Please select an ODF input folder.")
            return
        if not self.output_data_folder:
            QMessageBox.warning(self, "Missing input", "Please select an output folder.")
            return
        if self._remember_cb.isChecked():
            self._save_name()
        else:
            self._clear_saved()
        self.result = "accept"
        self.close()

    def _on_reject(self):
        self.result = "reject"
        self.close()

    def _save_name(self):
        try:
            data = {"remember": True, "name": self.line_edit_text}
            self._meta_store.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _clear_saved(self):
        try:
            if self._meta_store.exists():
                self._meta_store.unlink()
        except Exception:
            pass

    def _load_saved(self):
        try:
            if not self._meta_store.exists():
                return
            data = json.loads(self._meta_store.read_text(encoding="utf-8"))
            if data.get("remember") and data.get("name"):
                self._name_edit.setText(data["name"])
                self.line_edit_text = data["name"]
                self._remember_cb.setChecked(True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Lasso selection overlay
# ---------------------------------------------------------------------------
class LassoItem(pg.GraphicsObject):
    """Freehand lasso selection drawn in data coordinates (red dashed line)."""

    sigSelected = pg.QtCore.Signal(object)  # emits ndarray of int indices

    def __init__(self, plot_item: pg.PlotItem, xs: np.ndarray, ys: np.ndarray):
        super().__init__()
        self._plot = plot_item
        self._vb = plot_item.getViewBox()
        self._xs = xs
        self._ys = ys
        self._verts: list[tuple[float, float]] = []
        self._drawing = False
        self._pen = QPen(QColor("red"), 0)
        self._pen.setStyle(Qt.DashLine)
        plot_item.addItem(self)

    def boundingRect(self):
        return self._vb.viewRect()

    def paint(self, p, *args):
        if len(self._verts) < 2:
            return
        p.setPen(self._pen)
        path = QPainterPath()
        path.moveTo(QPointF(*self._verts[0]))
        for x, y in self._verts[1:]:
            path.lineTo(QPointF(x, y))
        p.drawPath(path)

    def _scene_to_data(self, scene_pos) -> tuple[float, float]:
        pt = self._vb.mapSceneToView(scene_pos)
        return pt.x(), pt.y()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._verts = [self._scene_to_data(ev.scenePos())]
            self._drawing = True
            self.update()
            ev.accept()
        else:
            ev.ignore()

    def mouseMoveEvent(self, ev):
        if self._drawing:
            self._verts.append(self._scene_to_data(ev.scenePos()))
            self.update()
            ev.accept()
        else:
            ev.ignore()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and self._drawing:
            self._drawing = False
            self._verts.append(self._verts[0])
            self.update()
            self._finish()
            ev.accept()
        else:
            ev.ignore()

    def _finish(self):
        if len(self._verts) < 3:
            self._verts = []
            self.update()
            return
        poly = QPolygonF([QPointF(x, y) for x, y in self._verts])
        selected = [
            i for i, (x, y) in enumerate(zip(self._xs, self._ys, strict=True))
            if poly.containsPoint(QPointF(x, y), Qt.OddEvenFill)
        ]
        self._verts = []
        self.update()
        if selected:
            self.sigSelected.emit(np.array(selected, dtype=int))


# ---------------------------------------------------------------------------
# CTD QC window
# ---------------------------------------------------------------------------
class CTDQCWindow(QWidget):
    """Profile-view QC window for CTD data.

    Y-axis : pressure (or depth) — inverted so surface is at the top.
    X-axis : selectable parameter, default Temperature.

    Lasso and click selection, flag radio buttons, undo, export, and
    continue/exit buttons behave identically to the thermograph QC window.
    """

    closed = pg.QtCore.Signal()

    def __init__(
        self,
        df: pd.DataFrame,
        pres_col: str,
        x_col_default: str,
        colors_initial: list,
        instrument: str,
        station: str,
        event_num: str,
        qc_mode_: str,
        qc_mode_code_: int,
        block_next_: int,
        idx: int,
        ctd_files: list,
        ctd_file,
        organization: str,
        state: dict,
        x_param_map: dict,
    ):
        super().__init__()

        self._df = df
        self._pres_col = pres_col          # column to use as Y (pressure/depth)
        self._x_col = x_col_default        # currently displayed x-axis param
        self._flag_col = f"qualityflag_{x_col_default}"
        self._state = state
        self._ctd_file = ctd_file
        self._x_param_map = x_param_map    # {display: (data_col, flag_col)}
        self._param_map = state.get("param_map", {})

        # Snapshot all flag columns for undo
        self._qflag_snapshots = {
            f"qualityflag_{d}": self._df[f"qualityflag_{d}"].to_numpy().copy()
            for d in self._param_map
        }

        self.setWindowTitle(
            f"[{idx}/{len(ctd_files)}] {organization} CTD Profile QC — {ctd_file.name}"
        )
        self.resize(1200, 750)

        # ── Root layout: plot (left panel) | controls (right panel) ───────
        root = QHBoxLayout(self)

        # ── Left panel: profile plot ──────────────────────────────────
        left_panel = QVBoxLayout()
        root.addLayout(left_panel, stretch=5)

        # Build pyqtgraph plot
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        self._pw = pg.PlotWidget()
        self._pw.setLabel("bottom", x_col_default)
        self._pw.setLabel("left", pres_col)
        self._pw.showGrid(x=True, y=True, alpha=0.3)
        self._pw.setTitle(
            f"[{idx}/{len(ctd_files)}] {organization} CTD Profile — "
            f"Station: {station}  Event: {event_num}  Instrument: {instrument}"
        )
        self._pw.setMouseEnabled(x=True, y=True)
        self._pw.getPlotItem().setMenuEnabled(True)

        # Invert y-axis so pressure increases downward (surface at top)
        self._pw.getPlotItem().invertY(True)

        # Initial scatter: x = selected param, y = pressure
        pres = df[pres_col].to_numpy()
        xs_init = df[x_col_default].to_numpy()
        brushes = [pg.mkBrush(QColor(c)) for c in colors_initial]
        self._scatter = pg.ScatterPlotItem(
            x=xs_init,
            y=pres,
            size=8,
            brush=brushes,
            pen=pg.mkPen(None),
        )
        self._pw.addItem(self._scatter)
        self._state["scatter"] = self._scatter

        # Fit view to data
        self._pres_data = pres
        x_margin, y_margin = self._compute_margins(xs_init, pres)
        self._x_range = (xs_init.min() - x_margin, xs_init.max() + x_margin)
        self._y_range = (pres.min() - y_margin, pres.max() + y_margin)
        self._pw.setXRange(*self._x_range, padding=0)
        self._pw.setYRange(*self._y_range, padding=0)
        self._pw.getPlotItem().enableAutoRange(enable=False)

        # Lasso (x=param value, y=pressure)
        self._lasso = LassoItem(self._pw.getPlotItem(), xs_init, pres)
        self._lasso.sigSelected.connect(self._on_lasso_select)
        self._scatter.sigClicked.connect(self._on_points_clicked)

        left_panel.addWidget(self._pw)

        # ── Right panel - controls ────────────────────────────────────────
        right_panel = QVBoxLayout()
        root.addLayout(right_panel, stretch=1)

        # QC mode label
        mode_color = "green" if qc_mode_code_ == 0 else "green"
        lbl_mode = QLabel(f"<b>QC Mode:</b><br>{qc_mode_}")
        lbl_mode.setStyleSheet(f"color: {mode_color}; font-size: 16px;")
        lbl_mode.setWordWrap(True)
        right_panel.addWidget(lbl_mode)

        # File info
        lbl_info = QLabel(
            f"<b>Station:</b> {station}<br>"
            f"<b>Event:</b> {event_num}<br>"
            f"<b>Instrument:</b> {instrument}<br>"
            f"<b>Y-axis:</b> {pres_col}"
        )
        lbl_info.setStyleSheet("color: navy; font-size: 16px;")
        lbl_info.setWordWrap(True)
        right_panel.addWidget(lbl_info)

        # X-axis selector
        x_row = QHBoxLayout()
        x_lbl = QLabel("<b>X-axis variable:</b>")
        x_lbl.setStyleSheet("font-size: 16px; color: navy;")
        self._x_combo = QComboBox()
        self._x_combo.setStyleSheet("font-size: 16px; font-weight: bold;")
        for display_name in x_param_map:
            self._x_combo.addItem(display_name)
        self._x_combo.setCurrentText(x_col_default)
        self._x_combo.currentTextChanged.connect(self._switch_x_axis)
        x_row.addWidget(x_lbl)
        x_row.addWidget(self._x_combo)
        x_row.addStretch()
        right_panel.addLayout(x_row)

        right_panel.addSpacing(12)

        # Flag radio buttons
        grp = QGroupBox("Assign QC for Selected Points:")
        grp.setStyleSheet("QGroupBox { font-weight: bold; color: navy; font-size: 16px; }")
        grp_layout = QVBoxLayout(grp)
        self._flag_group = QButtonGroup(self)
        for k, label in FLAG_LABELS.items():
            rb = QRadioButton(f"{k}: {label}")
            rb.setStyleSheet(
                f"color: {FLAG_COLORS[k]}; font-weight: bold; "
                f"font-family: serif; font-size: 16px;"
            )
            self._flag_group.addButton(rb, k)
            grp_layout.addWidget(rb)
            if k == state["current_flag"]:
                rb.setChecked(True)
        self._flag_group.idClicked.connect(self._on_flag_selected)
        right_panel.addWidget(grp)

        right_panel.addStretch()

        # Buttons
        def _btn(text, color):
            b = QPushButton(text)
            b.setStyleSheet(f"background-color: {color}; font-size: 16px; font-weight: bold; padding: 6px;")
            return b

        self._btn_reset = _btn("Reset View", "#e8e8ff")
        self._btn_undo = _btn("Undo All Selections", "lightblue")
        self._btn_export = _btn("Export DataFrame", "lightgrey")
        self._btn_continue = _btn("Continue Next >>", "lightgreen")
        self._btn_exit = _btn("Exit", "salmon")

        if block_next_ == 1:
            self._btn_continue.setEnabled(False)

        for b in (self._btn_reset, self._btn_undo, self._btn_export,
                  self._btn_continue, self._btn_exit):
            right_panel.addWidget(b)

        self._btn_reset.clicked.connect(self._click_reset_view)
        self._btn_undo.clicked.connect(self._click_deselect_all)
        self._btn_export.clicked.connect(lambda: self._export_dataframe(ctd_file))
        self._btn_continue.clicked.connect(self._click_continue)
        self._btn_exit.clicked.connect(self._click_exit)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_margins(xs, ys):
        x_margin = (xs.max() - xs.min()) * 0.05 if xs.size > 1 else 1.0
        y_margin = (ys.max() - ys.min()) * 0.05 if ys.size > 1 else 1.0
        return x_margin or 0.5, y_margin or 0.5

    def _current_xs(self) -> np.ndarray:
        return (
            self._df[self._x_col].to_numpy()
            if self._x_col in self._df.columns
            else self._df.iloc[:, 0].to_numpy()
        )

    # ── Slots ────────────────────────────────────────────────────────────────

    def _click_reset_view(self):
        self._pw.setXRange(*self._x_range, padding=0)
        self._pw.setYRange(*self._y_range, padding=0)

    def _switch_x_axis(self, display_name: str):
        """Switch the x-axis to a different parameter and its flag column."""
        self._x_col = display_name
        self._flag_col = f"qualityflag_{display_name}"
        self._state["active_display"] = display_name
        self._df["qualityflag"] = self._df[self._flag_col].copy()

        xs = self._current_xs()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]
        self._scatter.setData(
            x=xs, y=self._pres_data, brush=brushes, pen=pg.mkPen(None), size=8
        )
        self._lasso._xs = xs
        self._lasso._ys = self._pres_data

        x_margin, _ = self._compute_margins(xs, self._pres_data)
        self._x_range = (xs.min() - x_margin, xs.max() + x_margin)
        self._pw.setXRange(*self._x_range, padding=0)
        self._pw.setLabel("bottom", display_name)
        ctd_logger.info(f"X-axis switched to: {display_name} (flag col: {self._flag_col})")

    def _on_flag_selected(self, flag_id: int):
        self._state["current_flag"] = flag_id
        ctd_logger.info(f"Current flag set to {flag_id}")

    def _apply_flags_to_points(self, indices: np.ndarray):
        flag = self._state["current_flag"]
        self._df.iloc[indices, self._df.columns.get_loc(self._flag_col)] = flag
        self._df["qualityflag"] = self._df[self._flag_col].copy()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]
        self._scatter.setBrush(brushes)
        self._state["scatter"] = self._scatter

    def _on_lasso_select(self, indices: np.ndarray):
        if indices.size == 0:
            return
        ctd_logger.info(
            f"Lasso: {len(indices)} point(s) selected — "
            f"flag {self._state['current_flag']} on {self._x_col}"
        )
        self._apply_flags_to_points(indices)
        xs = self._current_xs()
        self._state["selection_groups"].append(pd.DataFrame({
            self._x_col: xs[indices],
            self._pres_col: self._pres_data[indices],
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    def _on_points_clicked(self, _plot, points):
        indices = np.array([p.index() for p in points], dtype=int)
        if indices.size == 0:
            return
        ctd_logger.info(
            f"Click: {len(indices)} point(s) selected — "
            f"flag {self._state['current_flag']} on {self._x_col}"
        )
        self._apply_flags_to_points(indices)
        xs = self._current_xs()
        self._state["selection_groups"].append(pd.DataFrame({
            self._x_col: xs[indices],
            self._pres_col: self._pres_data[indices],
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    def _click_deselect_all(self):
        self._state["selection_groups"].clear()
        ctd_logger.info("Undo All Selections — restoring original flags.")
        for fc, snap in self._qflag_snapshots.items():
            self._df[fc] = snap.copy()
        self._df["qualityflag"] = self._df[self._flag_col].copy()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]
        self._scatter.setBrush(brushes)
        self._lasso._xs = self._current_xs()
        self._state["scatter"] = self._scatter

    def _click_continue(self):
        self._state["applied"] = True
        ctd_logger.info("Continue clicked.")
        self.close()

    def _click_exit(self):
        self._state["user_exited"] = True
        self._state["exit_requested"] = True
        ctd_logger.info("Exit clicked — exit_requested set True.")
        self.close()

    def _export_dataframe(self, ctd_file):
        self._state["applied"] = True
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export DataFrame to CSV",
            f"{Path(ctd_file).stem}_QC_Export.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not export_path:
            return
        try:
            df_export = self._df.copy()
            df_export.reset_index(inplace=True)
            df_export.rename(columns={"index": "SEQ_INDEX"}, inplace=True)
            df_export.to_csv(export_path, index=False)
            ctd_logger.info(f"DataFrame exported to {export_path}")
            QMessageBox.information(
                self, "Export Successful",
                f"✅ DataFrame exported successfully to:\n{export_path}",
            )
        except Exception as exc:
            ctd_logger.error(f"Failed to export DataFrame: {exc}")
            QMessageBox.critical(
                self, "Export Failed", f"❌ Failed to export DataFrame:\n{exc}"
            )

    def closeEvent(self, ev):
        self.closed.emit()
        super().closeEvent(ev)


# ---------------------------------------------------------------------------
# Output folder preparation
# ---------------------------------------------------------------------------
def prepare_output_folder(in_folder_path: str, out_folder_path: str, qc_operator: str) -> str:
    base_name_input = "Step_1_Create_ODF"
    in_folder_path = str(Path(in_folder_path).resolve())
    out_folder_path = str(Path(out_folder_path).resolve())

    base_name_output = "Step_2_Assign_QFlag"
    out_odf_path = Path(out_folder_path) / base_name_output
    out_odf_path = Path(out_odf_path).resolve()

    if base_name_input.lower() in in_folder_path.lower():
        if (not out_odf_path.exists()) and (out_odf_path != Path(in_folder_path)):
            ctd_logger.info("Initial QC Mode: Creating output folder Step_2_Assign_QFlag")
            out_odf_path.mkdir(parents=True, exist_ok=False)
            ctd_logger.info(f"Created output folder: {out_odf_path}")
        else:
            ctd_logger.info("Initial QC Mode: Overwriting existing output folder Step_2_Assign_QFlag")
            try:
                shutil.rmtree(out_odf_path)
                out_odf_path.mkdir(parents=True, exist_ok=False)
                ctd_logger.warning(f"Overwriting existing folder: {out_odf_path}")
            except Exception as e:
                ctd_logger.error(f"Could not clear folder: {e}")
                out_odf_path.mkdir(parents=True, exist_ok=True)
    else:
        ctd_logger.info("Review QC Mode: Creating Step_3_Review_QFlag folder.")
        now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"Step_3_Review_QFlag_{qc_operator.strip().title()}_{now_ts}"
        out_odf_path = Path(out_folder_path) / new_name
        out_odf_path.mkdir(parents=True, exist_ok=False)
        ctd_logger.info(f"Created review output folder: {out_odf_path}")

    return str(out_odf_path)


# ---------------------------------------------------------------------------
# Core QC loop
# ---------------------------------------------------------------------------
def qc_ctd_data(
    in_folder_path: str,
    wildcard: str,
    out_folder_path: str,
    qc_operator: str,
    review_mode: bool,
) -> dict:
    """Iterate over ODF files, show the CTD profile QC window for each, and
    write the flagged ODF back to disk."""

    global exit_requested
    exit_requested = False
    batch_result = {"finished": False}
    qc_mode_user = 1 if review_mode else 0

    cwd = Path.cwd()
    try:
        os.chdir(in_folder_path)
        ctd_logger.info(f"Changed working dir to: {in_folder_path}")
    except Exception as e:
        ctd_logger.exception(f"Cannot change directory: {e}")
        return batch_result

    ctd_files = list(Path.cwd().glob(wildcard))
    ctd_logger.info(f"Found {len(ctd_files)} ODF file(s) matching '{wildcard}'")

    if not ctd_files:
        ctd_logger.warning("No ODF files found.")
        os.chdir(cwd)
        return batch_result

    out_odf_path = prepare_output_folder(in_folder_path, out_folder_path, qc_operator)
    ctd_logger.info(f"Output folder: {out_odf_path}")
    os.chdir(cwd)

    state: dict = {}

    for idx, ctd_file in enumerate(ctd_files, start=1):
        if exit_requested:
            ctd_logger.warning("Exit requested — stopping QC loop.")
            break

        ctd_file_name = ctd_file.name
        ctd_logger.info(f"Reading file {idx}/{len(ctd_files)}: {ctd_file}")

        full_path = str(pathlib.Path(in_folder_path, ctd_file))
        try:
            ctd = OdfHeader()
            ctd.read_odf(full_path)
        except Exception as e:
            ctd_logger.exception(f"Failed to read ODF {full_path}: {e}")
            continue

        # ── Extract data frame ────────────────────────────────────────────
        orig_df = ctd.data.data_frame
        orig_df_stored = orig_df.copy()
        orig_df = orig_df.copy()
        orig_df.reset_index(drop=True, inplace=True)
        orig_df = pd.DataFrame(orig_df)

        # ── Verify filename ───────────────────────────────────────────────
        file_name = f"{ctd.generate_file_spec()}.ODF"
        if file_name != ctd_file_name:
            ctd_logger.warning(
                f"Filename mismatch: header '{file_name}' vs actual '{ctd_file_name}'"
            )
            batch_result["finished"] = False
            return batch_result
        ctd_logger.info(f"Filename verified: {ctd_file_name}")

        # ── Header metadata ───────────────────────────────────────────────
        organization = ctd.cruise_header.organization
        instrument = ctd.instrument_header.instrument_type
        station = getattr(ctd.event_header, "station_name", "—") or "—"
        event_num = getattr(ctd.event_header, "event_number", "—") or "—"
        ctd_logger.info(f"Organization: {organization}  Station: {station}  Event: {event_num}")

        # ── Identify pressure / depth column ─────────────────────────────
        pres_col = None
        for candidate in _PRES_CANDIDATES:
            if candidate in orig_df.columns:
                pres_col = candidate
                break
        if pres_col is None:
            ctd_logger.warning(
                f"No pressure/depth column found in {ctd_file_name}. "
                f"Columns present: {list(orig_df.columns)}. Skipping file."
            )
            continue
        ctd_logger.info(f"Using '{pres_col}' as the Y-axis (pressure/depth).")

        # ── Discover all plottable parameter→flag pairs ───────────────────
        _time_cols = {c for c in orig_df.columns if c.upper().startswith("SYTM")}
        _skip_as_y = {pres_col}  # pressure column is the y-axis, not an x-axis option

        param_map: dict = {}
        for col in orig_df.columns:
            if col in _time_cols or col in _skip_as_y:
                continue
            # Skip flag columns (those whose name without the leading Q is a data column)
            if col.upper().startswith("Q") and col[1:] in orig_df.columns:
                continue
            try:
                arr = pd.to_numeric(orig_df[col], errors="coerce")
                if not arr.notna().any():
                    continue
            except Exception:
                continue
            flag_col = "Q" + col
            if flag_col not in orig_df.columns:
                orig_df[flag_col] = np.zeros(len(orig_df), dtype=int)
                ctd_logger.info(f"Created missing flag column {flag_col} for {col}")
            # Friendly display name
            if col in _TEMP_CANDIDATES:
                display = "Temperature"
            elif col.startswith('QCFF'):
                continue
            elif col.startswith('CNDC') or col.startswith('COND'):
                display = 'Conductivity'
            elif col.startswith('PSAL'):
                display = 'Salinity'
            elif col.startswith('DENS'):
                display = 'Density'
            elif col.startswith('SIGP'):
                display = 'Potential Density'
            elif col.startswith('SIGT'):
                display = 'Density Anomaly'
            elif col.startswith('POTM'):
                display = 'Potential Temperature'
            elif col.startswith('FLOR'):
                display = 'Fluorescence'
            elif col.startswith('CDOM'):
                display = 'CDOM'
            elif col.startswith('TURB'):
                display = 'Turbidity'
            elif col.startswith('CNTR'):
                display = 'Scan Count'
            elif col.startswith('SNCNTR'):
                display = 'Count of averaged records in bin'
            else:
                display = col
            param_map[display] = (col, flag_col)

        if not param_map:
            ctd_logger.warning(f"No plottable parameters found in {ctd_file_name}. Skipping.")
            continue

        # Also ensure the pressure column has a flag column (for write-back consistency)
        pres_flag_col = "Q" + pres_col
        if pres_flag_col not in orig_df.columns:
            orig_df[pres_flag_col] = np.zeros(len(orig_df), dtype=int)

        # ── Build working DataFrame ───────────────────────────────────────
        pres_arr = pd.to_numeric(orig_df[pres_col], errors="coerce").to_numpy()
        df = pd.DataFrame({pres_col: pres_arr})
        for display, (data_col, flag_col) in param_map.items():
            df[display] = pd.to_numeric(orig_df[data_col], errors="coerce").to_numpy()
            df[f"qualityflag_{display}"] = orig_df[flag_col].to_numpy().astype(int)

        # Choose default x-axis: prefer Temperature, else first available
        if "Temperature" in param_map:
            x_col_default = "Temperature"
        else:
            x_col_default = next(iter(param_map))

        # qualityflag alias — always mirrors the active param's flags
        df["qualityflag"] = df[f"qualityflag_{x_col_default}"].copy()

        # ── Determine QC mode ─────────────────────────────────────────────
        # Check the default x-axis parameter's flags for previous QC
        has_previous_qc = np.any(df[f"qualityflag_{x_col_default}"] != 0)

        if (not has_previous_qc) and (qc_mode_user == 0):
            qc_mode_ = " QC Mode - Initial\n(No Previous QC Flags)"
            qc_mode_code_ = 0
            block_next_ = 0
        elif (not has_previous_qc) and (qc_mode_user == 1):
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            ctd_logger.warning("QC Mode Mismatch: Review mode selected but no previous flags.")
            QMessageBox.warning(
                None, "QC Mode Mismatch",
                "⚠️ You selected Review QC Mode but no previous flags were found.\n\n"
                "Please run Initial QC Mode first.\n\nThis file will not proceed.",
            )
        elif has_previous_qc and (qc_mode_user == 1):
            qc_mode_ = " QC Mode - Review\n(With Previous QC Flags)"
            qc_mode_code_ = 1
            block_next_ = 0
        else:
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            ctd_logger.warning("QC Mode Mismatch: Initial mode selected but flags already exist.")
            QMessageBox.warning(
                None, "QC Mode Mismatch",
                "⚠️ You selected Initial QC Mode but existing flags were found.\n\n"
                "Please select Review QC Mode to modify existing flags.\n\n"
                "This file will not proceed.",
            )

        ctd_logger.info(f"QC Mode: {qc_mode_.strip()}")

        # Initial flag assignment for Initial QC mode (flag entire cast = 1,
        # no deploy/recover masking for CTD)
        if qc_mode_code_ == 0:
            for d in param_map:
                fc = f"qualityflag_{d}"
                df[fc] = 1  # whole cast is valid by default
            df["qualityflag"] = df[f"qualityflag_{x_col_default}"].copy()

        colors_initial = [
            FLAG_COLORS.get(int(f), "#808080") for f in df[f"qualityflag_{x_col_default}"]
        ]

        # ── State dict ────────────────────────────────────────────────────
        state.clear()
        state.update({
            "selection_groups": [],
            "applied": False,
            "user_exited": False,
            "exit_requested": False,
            "current_flag": 4,
            "param_map": param_map,
            "active_display": x_col_default,
        })

        # ── Show QC window ────────────────────────────────────────────────
        qc_win = CTDQCWindow(
            df=df,
            pres_col=pres_col,
            x_col_default=x_col_default,
            colors_initial=colors_initial,
            instrument=instrument,
            station=station,
            event_num=str(event_num),
            qc_mode_=qc_mode_,
            qc_mode_code_=qc_mode_code_,
            block_next_=block_next_,
            idx=idx,
            ctd_files=ctd_files,
            ctd_file=ctd_file,
            organization=organization,
            state=state,
            x_param_map=param_map,
        )

        if block_next_ == 1:
            try:
                Path(out_odf_path).rmdir()
            except Exception:
                pass

        qc_win.show()
        app = QApplication.instance()
        if app:
            app.processEvents()
            app.processEvents()

        ctd_logger.info(
            "CTD QC Tips:\n"
            "- Use the Lasso tool (click and drag) to select points in the profile.\n"
            "- Click individual points to select them.\n"
            "- Choose the desired quality flag BEFORE selecting points.\n"
            "- Switch the X-axis variable using the combo box above the plot.\n"
            "- Flags apply to the currently displayed parameter only.\n"
            "- Click 'Continue Next >>' to save and move to the next file.\n"
            "- Click 'Exit' to stop immediately."
        )

        # Busy-wait loop — keeps the main GUI responsive
        while qc_win.isVisible() and not state["exit_requested"]:
            if app:
                app.processEvents()
            time.sleep(0.05)

        if state["exit_requested"]:
            exit_requested = True

        # ── Write back flags ──────────────────────────────────────────────
        if state["applied"]:
            if len(orig_df) != len(df):
                ctd_logger.error(
                    f"Size mismatch: orig_df {len(orig_df)} rows vs df {len(df)} rows. Skipping write."
                )
            else:
                if state["selection_groups"]:
                    combined_indices = np.unique(
                        np.concatenate([g["idx"].to_numpy() for g in state["selection_groups"]])
                    ).astype(int)
                else:
                    combined_indices = np.array([], dtype=int)

                ctd_logger.info(
                    f"{len(combined_indices)} unique point(s) flagged across all x-axis variables."
                )

                for display, (_data_col, flag_col) in param_map.items():
                    df_fc = f"qualityflag_{display}"
                    if qc_mode_code_ == 0:
                        # Initial mode: all points get flag=1, then overwrite selected
                        orig_df[flag_col] = 1
                        if len(combined_indices) > 0:
                            orig_df.iloc[
                                combined_indices, orig_df.columns.get_loc(flag_col)
                            ] = df.iloc[combined_indices][df_fc].to_numpy()
                    elif qc_mode_code_ == 1:
                        # Review mode: only overwrite selected points
                        if len(combined_indices) > 0:
                            orig_df.iloc[
                                combined_indices, orig_df.columns.get_loc(flag_col)
                            ] = df.iloc[combined_indices][df_fc].to_numpy()

        # ── Log flag changes ──────────────────────────────────────────────
        orig_df_after = orig_df.copy()
        total_changed = 0
        for display, (_data_col, flag_col) in param_map.items():
            if flag_col not in orig_df_stored.columns:
                continue
            after = orig_df_after[flag_col].to_numpy().astype(int)
            before = orig_df_stored[flag_col].to_numpy().astype(int)
            mask = before != after
            n = mask.sum()
            total_changed += n
            if n > 0:
                ctd_logger.info(f"  [{display} / {flag_col}] {n} flag(s) changed:")
                for (b, a), cnt in Counter(zip(before[mask], after[mask], strict=True)).items():
                    ctd_logger.info(f"    Flag {b} → {a}: {cnt}")
            else:
                ctd_logger.info(f"  [{display} / {flag_col}] No changes.")

        if total_changed == 0:
            ctd_logger.info(f"No quality flag changes for {ctd_file}")
        else:
            ctd_logger.info(f"Total flags changed for {ctd_file}: {total_changed}")

        # ── Write ODF ─────────────────────────────────────────────────────
        try:
            ctd.data.data_frame = orig_df
            ctd.add_history()
            if qc_mode_code_ == 0:
                ctd.add_to_history(
                    f"APPLIED QUALITY CODE FLAGGING AND PERFORMED INITIAL VISUAL QC BY {qc_operator.upper()}"
                )
            else:
                ctd.add_to_history(
                    f"REVIEWED AND UPDATED QUALITY CODE FLAGGING BY {qc_operator.upper()}"
                )
            ctd.update_odf()
            file_spec = ctd.generate_file_spec()

            if "__" in file_spec or not event_num or event_num == "—":
                match = re.search(r"_(\d{1,4})_", ctd_file_name)
                if match:
                    en = match.group(1).zfill(3)
                    parts = file_spec.split("__")
                    if len(parts) == 2:
                        file_spec = f"{parts[0]}_{en}_{parts[1]}"
                    else:
                        file_spec = f"{file_spec.replace('.ODF', '')}_{en}.ODF"
                else:
                    raise ValueError(
                        f"Could not determine event number from filename: {ctd_file_name}"
                    )

            ctd.file_specification = file_spec
            out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
            ctd_logger.info(f"Writing [{idx}/{len(ctd_files)}]: {out_file}")
            ctd.write_odf(str(out_file), version=2.0)
            ctd_logger.info(f"Saved [{idx}/{len(ctd_files)}]: {out_file}")
        except Exception as e:
            ctd_logger.exception(f"Failed writing QC ODF for {ctd_file}: {e}")

    # ── Completion ────────────────────────────────────────────────────────
    if not exit_requested and idx == len(ctd_files):
        ctd_logger.info(f"QC complete — all {len(ctd_files)} file(s) processed.")
        batch_result["finished"] = True
    elif exit_requested:
        ctd_logger.info(f"QC interrupted after {idx}/{len(ctd_files)} file(s).")
        batch_result["finished"] = False
    else:
        batch_result["finished"] = False

    return batch_result


# ---------------------------------------------------------------------------
# Input selection wrapper
# ---------------------------------------------------------------------------
def main_select_inputs(review_mode: bool):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    dlg = CTDInputDialog(review_mode=review_mode)
    dlg.show()

    while dlg.isVisible():
        app.processEvents()
        time.sleep(0.05)

    if dlg.result == "accept":
        return (
            dlg.input_data_folder,
            dlg.output_data_folder,
            dlg.line_edit_text,
            dlg.wildcard_string,
        )
    return None, None, None, None


# ---------------------------------------------------------------------------
# Public entry point (called by the log window Start button)
# ---------------------------------------------------------------------------
def run_qc_ctd_data(
    input_path: str,
    output_path: str,
    qc_operator: str,
    review_mode: bool,
    wildcard: str,
) -> dict:
    ctd_logger.info(f"Starting CTD QC by {qc_operator} on {input_path}")
    result = qc_ctd_data(input_path, wildcard, output_path, qc_operator, review_mode)
    if result["finished"]:
        ctd_logger.info("CTD QC completed successfully.")
    else:
        ctd_logger.warning("CTD QC did not complete — check logs.")
    return result


# ---------------------------------------------------------------------------
# Log-window start button handler
# ---------------------------------------------------------------------------
def start_qc_process(log_ui: LogWindowCTDQC, review_mode: bool):
    global exit_requested
    exit_requested = False
    ctd_logger.info("Start QC button clicked.")

    review_mode = log_ui.radio_opt.isChecked()
    ctd_logger.info("Review QC Mode selected." if review_mode else "Initial QC Mode selected.")

    input_path, output_path, operator, wildcard = main_select_inputs(review_mode)
    if not input_path or not output_path or not operator:
        ctd_logger.info("QC start aborted: missing required inputs.")
        return

    ctd_logger.info(
        "CTD QC Inputs:\n"
        f"  • QC Operator : {operator.strip().title()}\n"
        f"  • Input Path  : {input_path}\n"
        f"  • Output Path : {output_path}\n"
        f"  • Wildcard    : {wildcard}\n"
    )
    run_qc_ctd_data(input_path, output_path, operator, review_mode, wildcard)


# ---------------------------------------------------------------------------
# Exit handler
# ---------------------------------------------------------------------------
def exit_program(app):
    global exit_requested
    exit_requested = True
    ctd_logger.info("Exit Program clicked.")
    for h in ctd_logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    app.quit()


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------
def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    log_window = LogWindowCTDQC()
    log_window.show()
    if log_window.qtext_handler not in ctd_logger.handlers:
        ctd_logger.addHandler(log_window.qtext_handler)
    ctd_logger.info("CTD QC Log window initialized.")

    log_window.radio_opt.setEnabled(True)

    log_window.radio_opt.toggled.connect(
        lambda checked: ctd_logger.info(
            f"QC Reviewer Mode radio button is {'checked' if checked else 'unchecked'}"
        )
    )
    log_window.btn_start.clicked.connect(
        lambda: start_qc_process(log_window, log_window.radio_opt.isChecked())
    )
    log_window.btn_exit.clicked.connect(lambda: exit_program(app))
    ctd_logger.info("Application started. Click 'Start Visual QC Process' to begin.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
