"""
qc_window.py
------------
Pyqtgraph-based interactive QC window for thermograph data.

The window layout is defined in ``qc_window.ui`` (Qt Designer format).
Open that file in Qt Creator to edit the layout, labels, colours, and
spacing without touching any Python.

Runtime wiring (plot setup, signal connections, flag logic) lives here.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

mtr_logger = logging.getLogger("thermograph_qc_logger")

# ---------------------------------------------------------------------------
# Flag metadata — keep in sync with qc_thermograph_data.py
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

# Path to the .ui file — expected to sit beside this .py file.
_UI_FILE = Path(__file__).parent / "qc_window.ui"


# ---------------------------------------------------------------------------
# LassoItem — freehand polygon selection overlay for pyqtgraph
# ---------------------------------------------------------------------------
class LassoItem(pg.GraphicsObject):
    """Overlay that collects a freehand lasso polygon while the user
    holds the left mouse button, then fires ``sigSelected(indices)``."""

    sigSelected = pg.QtCore.Signal(object)  # emits ndarray of int indices

    def __init__(self, plot_item: pg.PlotItem, xs: np.ndarray, ys: np.ndarray):
        super().__init__()
        self._plot = plot_item
        self._vb = plot_item.getViewBox()
        self._xs = xs   # unix timestamps (data coords)
        self._ys = ys   # y-values (data coords)
        self._verts_data: list[tuple[float, float]] = []
        self._drawing = False
        self._pen = QPen(QColor("red"), 0)   # cosmetic pen — 1 px at any zoom
        self._pen.setStyle(Qt.DashLine)
        plot_item.addItem(self)

    # GraphicsObject protocol ------------------------------------------------

    def boundingRect(self):
        return self._vb.viewRect()

    def paint(self, p, *args):
        if len(self._verts_data) < 2:
            return
        p.setPen(self._pen)
        path = QPainterPath()
        path.moveTo(QPointF(*self._verts_data[0]))
        for x, y in self._verts_data[1:]:
            path.lineTo(QPointF(x, y))
        p.drawPath(path)

    # Mouse events -----------------------------------------------------------

    def _scene_to_data(self, scene_pos) -> tuple[float, float]:
        pt = self._vb.mapSceneToView(scene_pos)
        return pt.x(), pt.y()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._verts_data = [self._scene_to_data(ev.scenePos())]
            self._drawing = True
            self.update()
            ev.accept()
        else:
            ev.ignore()

    def mouseMoveEvent(self, ev):
        if self._drawing:
            self._verts_data.append(self._scene_to_data(ev.scenePos()))
            self.update()
            ev.accept()
        else:
            ev.ignore()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and self._drawing:
            self._drawing = False
            self._verts_data.append(self._verts_data[0])  # close polygon
            self.update()
            self._finish()
            ev.accept()
        else:
            ev.ignore()

    def _finish(self):
        if len(self._verts_data) < 3:
            self._verts_data = []
            self.update()
            return
        poly = QPolygonF([QPointF(x, y) for x, y in self._verts_data])
        selected = [
            i for i, (x, y) in enumerate(zip(self._xs, self._ys, strict=True))
            if poly.containsPoint(QPointF(x, y), Qt.OddEvenFill)
        ]
        self._verts_data = []
        self.update()
        if selected:
            self.sigSelected.emit(np.array(selected, dtype=int))


# ---------------------------------------------------------------------------
# QCWindow
# ---------------------------------------------------------------------------
class QCWindow(QWidget):
    """Interactive QC scatter-plot window.

    Layout comes from ``qc_window.ui``; all plot setup and business logic
    is in this class.

    Parameters
    ----------
    xnums : ndarray
        Unix timestamps for each data point.
    df : DataFrame
        Working data frame. Must contain:
        - ``"Temperature"`` column
        - ``"qualityflag_<display>"`` column for every entry in *param_map*
        - ``"qualityflag"`` alias (synced to the active param)
        - One column per extra parameter (same name as its display key)
    qflag : ndarray
        Initial Temperature flag array (kept for legacy undo path).
    colors_initial : list[str]
        Initial point colours derived from flags.
    qc_start_ts, qc_end_ts : float
        Unix timestamps for the QC window start/end.
    start_datetime_qc, end_datetime_qc : any
        Human-readable QC window bounds (shown in info label).
    instrument : str
        Instrument type string.
    batch_name : str
        Batch identifier string.
    qc_mode_ : str
        Display string for the QC mode label.
    qc_mode_code_ : int
        0 = Initial QC, 1 = Review QC.
    block_next_ : int
        1 = disable the Continue button (mode mismatch).
    idx : int
        1-based index of current file.
    mtr_files : list
        Full list of files in this batch.
    mtr_file : Path
        Current file path.
    organization : str
        Organisation string shown in the title.
    state : dict
        Shared mutable state dict (selection_groups, applied, etc.).
    extra_params : dict
        ``{display_name: (data_col, flag_col)}`` for non-Temperature params.
    """

    closed = pg.QtCore.Signal()

    def __init__(
        self,
        xnums: np.ndarray,
        df: pd.DataFrame,
        qflag: np.ndarray,
        colors_initial: list,
        qc_start_ts: float,
        qc_end_ts: float,
        start_datetime_qc,
        end_datetime_qc,
        instrument: str,
        batch_name: str,
        qc_mode_: str,
        qc_mode_code_: int,
        block_next_: int,
        idx: int,
        mtr_files: list,
        mtr_file,
        organization: str,
        state: dict,
        extra_params: dict,
    ):
        super().__init__()

        # ── Store runtime data ────────────────────────────────────────────
        self._xnums = xnums
        self._df = df
        self._state = state
        self._mtr_file = mtr_file
        self._extra_params = extra_params
        self._param_map: dict = state.get(
            "param_map", {"Temperature": ("TE90_01", "QTE90_01")}
        )
        self._y_col = "Temperature"
        self._flag_col = "qualityflag_Temperature"

        # Snapshot all per-param flag columns at init so Undo can restore them
        self._qflag_snapshots = {
            f"qualityflag_{d}": self._df[f"qualityflag_{d}"].to_numpy().copy()
            for d in self._param_map
        }

        # ── Load UI from .ui file ─────────────────────────────────────────
        loader = QUiLoader()
        ui_widget: QWidget = loader.load(str(_UI_FILE), parentWidget=None)
        if ui_widget is None:
            raise RuntimeError(f"Failed to load UI file: {_UI_FILE}")

        # Embed the loaded widget into self via a wrapper layout
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(ui_widget)

        # ── Grab named widgets from the .ui ──────────────────────────────
        self._lbl_qc_mode: QWidget      = ui_widget.findChild(QWidget, "lbl_qc_mode")
        self._lbl_info: QWidget         = ui_widget.findChild(QWidget, "lbl_info")
        self._grp_flags: QWidget        = ui_widget.findChild(QWidget, "grp_flags")
        self._flags_layout              = self._grp_flags.layout()
        self._y_selector_widget: QWidget = ui_widget.findChild(QWidget, "y_selector_widget")
        self._combo_y_axis: QWidget     = ui_widget.findChild(QWidget, "combo_y_axis")
        self._plot_container: QWidget   = ui_widget.findChild(QWidget, "plot_container")
        self._plot_container_layout     = self._plot_container.layout()
        self.btn_reset_view: QWidget    = ui_widget.findChild(QWidget, "btn_reset_view")
        self.btn_undo: QWidget          = ui_widget.findChild(QWidget, "btn_undo")
        self.btn_export: QWidget        = ui_widget.findChild(QWidget, "btn_export")
        self.btn_continue: QWidget      = ui_widget.findChild(QWidget, "btn_continue")
        self.btn_exit: QWidget          = ui_widget.findChild(QWidget, "btn_exit")

        # ── Window title & size ───────────────────────────────────────────
        self.setWindowTitle(
            f"[{idx}/{len(mtr_files)}] {organization} "
            f"Time Series QC — {mtr_file}"
        )
        self.resize(1400, 700)

        # ── Populate dynamic labels ───────────────────────────────────────
        mode_color = "green" if qc_mode_code_ == 0 else "orange"
        self._lbl_qc_mode.setStyleSheet(
            f"color: {mode_color}; font-size: 13px;"
        )
        self._lbl_qc_mode.setText(f"<b>QC Mode:</b><br>{qc_mode_}")

        self._lbl_info.setText(
            f"<b>Deployed:</b> {start_datetime_qc}<br>"
            f"<b>Recovered:</b> {end_datetime_qc}<br>"
            f"<b>Instrument:</b> {instrument}<br>"
            f"<b>Batch:</b> {batch_name}"
        )

        # ── Flag radio buttons (built dynamically from FLAG_LABELS) ───────
        self._flag_group = QButtonGroup(self)
        for k, label in FLAG_LABELS.items():
            rb = QRadioButton(f"{k}: {label}")
            rb.setStyleSheet(
                f"color: {FLAG_COLORS[k]}; font-weight: bold; "
                f"font-family: serif; font-size: 10px;"
            )
            rb.setProperty("flag_value", k)
            self._flag_group.addButton(rb, k)
            self._flags_layout.addWidget(rb)
            if k == state["current_flag"]:
                rb.setChecked(True)
        self._flag_group.idClicked.connect(self._on_flag_selected)

        # ── Y-axis combo ──────────────────────────────────────────────────
        if extra_params:
            self._combo_y_axis.addItem("Temperature")
            for display_name in extra_params:
                self._combo_y_axis.addItem(display_name)
            self._combo_y_axis.currentTextChanged.connect(self._switch_y_axis)
        else:
            # Hide the whole selector row when there's only one variable
            self._y_selector_widget.setVisible(False)

        # ── Build pyqtgraph plot ──────────────────────────────────────────
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        self._pw = pg.PlotWidget()
        self._pw.setLabel("bottom", "Date / Time")
        self._pw.setLabel("left", "Temperature")
        self._pw.showGrid(x=True, y=True, alpha=0.3)
        self._pw.setTitle(
            f"[{idx}/{len(mtr_files)}] {organization} "
            f"Time Series Data — {mtr_file}"
        )
        self._pw.setMouseEnabled(x=True, y=True)
        self._pw.getPlotItem().setMenuEnabled(True)

        # Date-time axis
        self._pw.setAxisItems({"bottom": pg.DateAxisItem(orientation="bottom")})

        # QC window shading (behind scatter)
        lr = pg.LinearRegionItem(
            [qc_start_ts, qc_end_ts],
            brush=pg.mkBrush(QColor(173, 216, 230, 60)),
            movable=False,
        )
        lr.setZValue(-10)
        self._pw.addItem(lr)

        # Vertical deployment / recovery lines
        self._pw.addItem(pg.InfiniteLine(
            pos=qc_start_ts, angle=90,
            pen=pg.mkPen("b", width=2, style=Qt.DashLine),
            label="Deployment: Start",
            labelOpts={"color": "purple", "rotateAxis": (1, 0)},
        ))
        self._pw.addItem(pg.InfiniteLine(
            pos=qc_end_ts, angle=90,
            pen=pg.mkPen("b", width=2, style=Qt.DashLine),
            label="Recovered: End",
            labelOpts={"color": "purple", "rotateAxis": (1, 0)},
        ))

        # Scatter plot
        brushes = [pg.mkBrush(QColor(c)) for c in colors_initial]
        self._scatter = pg.ScatterPlotItem(
            x=xnums,
            y=df["Temperature"].to_numpy(),
            size=8,
            brush=brushes,
            pen=pg.mkPen(None),
        )
        self._pw.addItem(self._scatter)
        self._state["scatter"] = self._scatter

        # Fit view to data extents (suppress InfiniteLine auto-range expansion)
        temps = df["Temperature"].to_numpy()
        x_margin = (xnums.max() - xnums.min()) * 0.03 or 86400
        y_margin = (temps.max() - temps.min()) * 0.05 or 1.0
        self._x_range = (xnums.min() - x_margin, xnums.max() + x_margin)
        self._y_range = (temps.min() - y_margin, temps.max() + y_margin)
        self._pw.setXRange(*self._x_range, padding=0)
        self._pw.setYRange(*self._y_range, padding=0)
        self._pw.getPlotItem().enableAutoRange(enable=False)

        # Lasso overlay
        self._lasso = LassoItem(
            self._pw.getPlotItem(),
            xnums,
            df["Temperature"].to_numpy(),
        )
        self._lasso.sigSelected.connect(self._on_lasso_select)

        # Click-to-select
        self._scatter.sigClicked.connect(self._on_points_clicked)

        # Insert plot widget into the container defined in the .ui file
        self._plot_container_layout.addWidget(self._pw)

        # ── Button state & connections ────────────────────────────────────
        if block_next_ == 1:
            self.btn_continue.setEnabled(False)

        self.btn_reset_view.clicked.connect(self._click_reset_view)
        self.btn_undo.clicked.connect(self._click_deselect_all)
        self.btn_export.clicked.connect(lambda: self._export_dataframe(mtr_file))
        self.btn_continue.clicked.connect(self._click_continue)
        self.btn_exit.clicked.connect(self._click_exit)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _click_reset_view(self):
        self._pw.setXRange(*self._x_range, padding=0)
        self._pw.setYRange(*self._y_range, padding=0)

    def _switch_y_axis(self, col_name: str):
        """Switch the plotted variable and the active flag column."""
        self._y_col = col_name
        self._flag_col = f"qualityflag_{col_name}"
        self._state["active_display"] = col_name

        # Sync the qualityflag alias
        self._df["qualityflag"] = self._df[self._flag_col].copy()

        ys = self._current_ys()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]
        self._scatter.setData(x=self._xnums, y=ys, brush=brushes,
                              pen=pg.mkPen(None), size=8)
        self._lasso._ys = ys

        valid = ys[~np.isnan(ys.astype(float))]
        if valid.size:
            y_margin = (valid.max() - valid.min()) * 0.05 or 1.0
            self._y_range = (valid.min() - y_margin, valid.max() + y_margin)
            self._pw.setYRange(*self._y_range, padding=0)
        self._pw.setLabel("left", col_name)
        mtr_logger.info(f"Y-axis switched to: {col_name} (flag col: {self._flag_col})")

    def _current_ys(self) -> np.ndarray:
        """Y-values for the currently displayed column."""
        if self._y_col == "Temperature":
            return self._df["Temperature"].to_numpy()
        return (
            self._df[self._y_col].to_numpy()
            if self._y_col in self._df.columns
            else self._df["Temperature"].to_numpy()
        )

    def _on_flag_selected(self, flag_id: int):
        self._state["current_flag"] = flag_id
        mtr_logger.info(f"Current flag set to {flag_id}")

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
        mtr_logger.info(
            f"Selected {len(indices)} point(s) via LASSO — "
            f"flag {self._state['current_flag']} on {self._y_col}"
        )
        self._apply_flags_to_points(indices)
        sel_vals = self._current_ys()[indices]
        self._state["selection_groups"].append(pd.DataFrame({
            "DateTime": self._df.index[indices],
            self._y_col: sel_vals,
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    def _on_points_clicked(self, _plot, points):
        indices = np.array([p.index() for p in points], dtype=int)
        if indices.size == 0:
            return
        mtr_logger.info(
            f"Selected {len(indices)} point(s) via click — "
            f"flag {self._state['current_flag']} on {self._y_col}"
        )
        self._apply_flags_to_points(indices)
        sel_vals = self._current_ys()[indices]
        self._state["selection_groups"].append(pd.DataFrame({
            "DateTime": self._df.index[indices],
            self._y_col: sel_vals,
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    def _click_deselect_all(self):
        self._state["selection_groups"].clear()
        mtr_logger.info("Undo All Selections clicked — restoring original flags.")
        for fc, snap in self._qflag_snapshots.items():
            self._df[fc] = snap.copy()
        self._df["qualityflag"] = self._df[self._flag_col].copy()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]
        self._scatter.setBrush(brushes)
        self._lasso._ys = self._current_ys()
        self._state["scatter"] = self._scatter

    def _click_continue(self):
        self._state["applied"] = True
        mtr_logger.info("Continue clicked.")
        self.close()

    def _click_exit(self):
        self._state["user_exited"] = True
        self._state["exit_requested"] = True
        mtr_logger.info("Exit clicked — exit_requested set True.")
        self.close()

    def _export_dataframe(self, mtr_file):
        self._state["applied"] = True
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export DataFrame to CSV",
            f"{Path(mtr_file).stem}_QC_Export.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not export_path:
            return
        try:
            df_export = self._df.copy()
            df_export.reset_index(inplace=True)
            df_export.rename(columns={"index": "SEQ_INDEX"}, inplace=True)
            df_export.to_csv(export_path, index=False)
            mtr_logger.info(f"DataFrame exported to {export_path}")
            QMessageBox.information(
                self,
                "Export Successful",
                f"✅ DataFrame exported successfully to:\n{export_path}",
            )
        except Exception as exc:
            mtr_logger.error(f"Failed to export DataFrame: {exc}")
            QMessageBox.critical(
                self, "Export Failed", f"❌ Failed to export DataFrame:\n{exc}"
            )

    def closeEvent(self, ev):
        self.closed.emit()
        super().closeEvent(ev)
