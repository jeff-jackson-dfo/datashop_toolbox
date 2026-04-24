"""
qc_odf_data.py
--------------
Unified interactive visual QC tool for ODF files.

Supports two data types, selected automatically based on the ODF file content
(instrument type / available columns):

  Thermograph (time-series)
  ─────────────────────────
  • Plot    : Temperature (or any numeric parameter) vs. Date/Time
  • X-axis  : Unix-timestamp axis with DateAxisItem formatting
  • Y-axis  : Selectable via combo box (Temperature is default)
  • Extras  : Deploy/Recover shaded region + vertical lines;
              optional metadata file for DFO BIO / FSRS organisations.

  CTD (profile)
  ─────────────
  • Plot    : Selectable parameter on the X-axis vs. Pressure/Depth on the Y-axis
              (Y inverted so surface is at top)
  • X-axis  : Selectable via combo box (Temperature is default)
  • Y-axis  : Pressure or Depth column
  • Extras  : No metadata or deploy/recover masking required.

Shared infrastructure (identical for both types)
─────────────────────────────────────────────────
  • LassoItem        – freehand polygon selection drawn in data coordinates
  • QCWindow         – main interactive window with flag radio buttons, undo,
                       export, continue, and exit controls
  • FLAG_LABELS / FLAG_COLORS – QC flag definitions
  • prepare_output_folder     – Step_2 / Step_3 folder logic
  • Logging setup             – file + console handler, SafeConsoleFilter
  • LogWindow                 – unified log window with data-type radio selector
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
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pyqtgraph as pg
import pytz
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

# datashop_toolbox imports – keep originals so existing callers are unaffected
from datashop_toolbox.log_window import SafeConsoleFilter
from datashop_toolbox.odfhdr import OdfHeader  # CTD ODF reader
from datashop_toolbox.thermograph import ThermographHeader  # Thermograph ODF reader

# Optional – thermograph tool needs the metadata-picker sub-window
try:
    from datashop_toolbox import select_metadata_file_and_data_folder
except ImportError:
    select_metadata_file_and_data_folder = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_dir = Path.cwd() / "logs"
log_dir.mkdir(exist_ok=True)
_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"datashop_QC_log_{_ts}.txt"

logger = logging.getLogger("odf_qc_logger")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    _ch = logging.StreamHandler()
    _ch.addFilter(SafeConsoleFilter())
    _ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(_ch)
    _fh = logging.FileHandler(log_file, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.info("Logger initialized.")

# ---------------------------------------------------------------------------
# Timezone helpers (thermograph only)
# ---------------------------------------------------------------------------
ATLANTIC_TZ = pytz.timezone("Canada/Atlantic")
UTC = pytz.UTC

# ---------------------------------------------------------------------------
# Global exit flag
# ---------------------------------------------------------------------------
exit_requested = False

# ---------------------------------------------------------------------------
# QC flag tables
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

# Preferred column name candidates for CTD pressure/depth and temperature
_PRES_CANDIDATES = ["PRES_01", "PRES_02", "DEPH_01", "DEPH_02"]
_TEMP_CANDIDATES = ["TEMP_01", "TE90_01", "TEMP_02"]


# ===========================================================================
# Shared: LassoItem
# ===========================================================================
class LassoItem(pg.GraphicsObject):
    """Freehand lasso selection overlay drawn in data coordinates (red dashed
    line).  Fires ``sigSelected(indices)`` on mouse release."""

    sigSelected = pg.QtCore.Signal(object)  # emits ndarray of int indices

    def __init__(self, plot_item: pg.PlotItem, xs: np.ndarray, ys: np.ndarray):
        super().__init__()
        self._plot = plot_item
        self._vb = plot_item.getViewBox()
        self._xs = xs
        self._ys = ys
        self._verts: list[tuple[float, float]] = []
        self._drawing = False
        self._enabled = True
        self._pen = QPen(QColor("red"), 0)
        self._pen.setStyle(Qt.DashLine)
        plot_item.addItem(self)

    # ── Enable / disable (for zoom/pan mode hand-off) ──────────────────────
    def pause(self):
        self._enabled = False
        self._drawing = False
        self._verts = []
        self.update()
        self.setAcceptedMouseButtons(Qt.NoButton)

    def resume(self):
        self._enabled = True
        self.setAcceptedMouseButtons(Qt.LeftButton)

    # ── GraphicsObject required overrides ──────────────────────────────────
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

    # ── Mouse events ───────────────────────────────────────────────────────
    def _scene_to_data(self, scene_pos):
        pt = self._vb.mapSceneToView(scene_pos)
        return pt.x(), pt.y()

    def mousePressEvent(self, ev):
        if not self._enabled:
            ev.ignore()
            return
        if ev.button() == Qt.LeftButton:
            self._verts = [self._scene_to_data(ev.scenePos())]
            self._drawing = True
            self.update()
            ev.accept()
        else:
            ev.ignore()

    def mouseMoveEvent(self, ev):
        if not self._enabled:
            ev.ignore()
            return
        if self._drawing:
            self._verts.append(self._scene_to_data(ev.scenePos()))
            self.update()
            ev.accept()
        else:
            ev.ignore()

    def mouseReleaseEvent(self, ev):
        if not self._enabled:
            ev.ignore()
            return
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


# ===========================================================================
# Shared: QCWindow
# ===========================================================================
class QCWindow(QWidget):
    """Unified interactive QC window.

    Behaviour differs by ``mode``:
      ``"thermograph"``  – time-series plot (X = timestamps, Y = parameter)
      ``"ctd"``          – profile plot (X = parameter, Y = pressure, Y inverted)

    All flagging, lasso/click selection, undo, export, and navigation controls
    are identical for both modes.
    """

    closed = pg.QtCore.Signal()

    def __init__(
        self,
        mode: str,          # "thermograph" or "ctd"
        df: pd.DataFrame,
        state: dict,
        # --- thermograph-specific ---
        xnums: np.ndarray | None = None,          # unix timestamps
        qc_start_ts: float | None = None,
        qc_end_ts: float | None = None,
        start_datetime_qc=None,
        end_datetime_qc=None,
        batch_name: str = "",
        # --- ctd-specific ---
        pres_col: str | None = None,
        x_col_default: str | None = None,
        station: str = "—",
        event_num: str = "—",
        # --- shared ---
        colors_initial: list | None = None,
        instrument: str = "",
        organization: str = "",
        qc_mode_: str = "",
        qc_mode_code_: int = 0,
        block_next_: int = 0,
        idx: int = 1,
        file_list: list | None = None,
        current_file=None,
        param_map: dict | None = None,
    ):
        super().__init__()

        # Set modality to block the rest of the application
        self.setWindowModality(Qt.WindowModality.ApplicationModal)        

        self._mode = mode
        self._df = df
        self._state = state
        self._param_map = param_map or state.get("param_map", {})
        self._block_next_ = block_next_
        self._current_file = current_file
        file_list = file_list or []

        # ── Mode-specific attribute aliases ────────────────────────────────
        if mode == "thermograph":
            self._xnums = xnums
            self._y_col = "Temperature"
            self._flag_col = "qualityflag_Temperature"
        else:  # ctd
            self._pres_col = pres_col
            self._pres_data = df[pres_col].to_numpy()
            self._x_col = x_col_default
            self._flag_col = f"qualityflag_{x_col_default}"

        # Snapshot all per-param flag columns for undo
        self._qflag_snapshots = {
            f"qualityflag_{d}": self._df[f"qualityflag_{d}"].to_numpy().copy()
            for d in self._param_map
        }

        # ── Window title ───────────────────────────────────────────────────
        if mode == "thermograph":
            self.setWindowTitle(
                f"[{idx}/{len(file_list)}] {organization} "
                f"Time-Series QC — {current_file}"
            )
            self.resize(1400, 700)
        else:
            self.setWindowTitle(
                f"[{idx}/{len(file_list)}] {organization} "
                f"CTD Profile QC — {getattr(current_file, 'name', current_file)}"
            )
            self.resize(1200, 750)

        # ── Root layout ────────────────────────────────────────────────────
        root = QHBoxLayout(self)

        # ── Build pyqtgraph plot ───────────────────────────────────────────
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        self._pw = pg.PlotWidget()
        self._pw.showGrid(x=True, y=True, alpha=0.3)
        self._pw.setMouseEnabled(x=True, y=True)
        self._pw.getPlotItem().setMenuEnabled(True)
        self._vb = self._pw.getViewBox()

        if mode == "thermograph":
            self._pw.setLabel("bottom", "Date / Time")
            self._pw.setLabel("left", "Temperature")
            self._pw.setTitle(
                f"[{idx}/{len(file_list)}] {organization} "
                f"Time-Series — {current_file}"
            )
            axis = pg.DateAxisItem(orientation="bottom")
            self._pw.setAxisItems({"bottom": axis})
            self._vb.setMouseMode(pg.ViewBox.RectMode)

            # Deploy/Recover shaded region + lines
            lr = pg.LinearRegionItem(
                [qc_start_ts, qc_end_ts],
                brush=pg.mkBrush(QColor(173, 216, 230, 60)),
                movable=False,
            )
            lr.setZValue(-10)
            self._pw.addItem(lr)
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

            # Scatter: X = timestamps, Y = Temperature
            brushes = [pg.mkBrush(QColor(c)) for c in (colors_initial or [])]
            self._scatter = pg.ScatterPlotItem(
                x=xnums, y=df["Temperature"].to_numpy(),
                size=8, brush=brushes, pen=pg.mkPen(None),
            )
            self._pw.addItem(self._scatter)
            self._state["scatter"] = self._scatter

            # Fit view
            x_margin = (xnums.max() - xnums.min()) * 0.03 or 86400
            temps = df["Temperature"].to_numpy()
            y_margin = (temps.max() - temps.min()) * 0.05 or 1.0
            self._pw.setXRange(xnums.min() - x_margin, xnums.max() + x_margin, padding=0)
            self._pw.setYRange(temps.min() - y_margin, temps.max() + y_margin, padding=0)
            self._pw.getPlotItem().enableAutoRange(enable=False)
            self._x_range = (xnums.min() - x_margin, xnums.max() + x_margin)
            self._y_range = (temps.min() - y_margin, temps.max() + y_margin)

            # Lasso: X = timestamps, Y = Temperature
            self._lasso = LassoItem(self._pw.getPlotItem(), xnums, df["Temperature"].to_numpy())

        else:  # ctd
            self._pw.setLabel("bottom", x_col_default)
            self._pw.setLabel("left", pres_col)
            self._pw.setTitle(
                f"[{idx}/{len(file_list)}] {organization} CTD Profile — "
                f"Station: {station}  Event: {event_num}  Instrument: {instrument}"
            )
            self._pw.getPlotItem().invertY(True)

            pres = self._pres_data
            xs_init = df[x_col_default].to_numpy()
            brushes = [pg.mkBrush(QColor(c)) for c in (colors_initial or [])]
            self._scatter = pg.ScatterPlotItem(
                x=xs_init, y=pres, size=8, brush=brushes, pen=pg.mkPen(None),
            )
            self._pw.addItem(self._scatter)
            self._state["scatter"] = self._scatter

            x_margin, y_margin = self._compute_margins(xs_init, pres)
            self._x_range = (xs_init.min() - x_margin, xs_init.max() + x_margin)
            self._y_range = (pres.min() - y_margin, pres.max() + y_margin)
            self._pw.setXRange(*self._x_range, padding=0)
            self._pw.setYRange(*self._y_range, padding=0)
            self._pw.getPlotItem().enableAutoRange(enable=False)

            # Lasso: X = param, Y = pressure
            self._lasso = LassoItem(self._pw.getPlotItem(), xs_init, pres)

        # Wire up selection signals
        self._scatter.sigClicked.connect(self._on_points_clicked)
        self._lasso.sigSelected.connect(self._on_lasso_select)

        # ── Left panel ─────────────────────────────────────────────────────
        left_panel = QVBoxLayout()
        root.addLayout(left_panel, stretch=5)
        left_panel.addWidget(self._pw)

        # ── Right panel ────────────────────────────────────────────────────
        right_panel = QVBoxLayout()
        root.addLayout(right_panel, stretch=1)

        # QC mode label
        lbl_mode = QLabel(f"<b>QC Mode:</b><br>{qc_mode_}")
        lbl_mode.setStyleSheet("color: green; font-size: 16px;")
        lbl_mode.setWordWrap(True)
        right_panel.addWidget(lbl_mode)

        # Info block
        if mode == "thermograph":
            info_html = (
                f"<b>Deployed:</b> {start_datetime_qc}<br>"
                f"<b>Recovered:</b> {end_datetime_qc}<br>"
                f"<b>Instrument:</b> {instrument}<br>"
                f"<b>Batch:</b> {batch_name}"
            )
        else:
            info_html = (
                f"<b>Station:</b> {station}<br>"
                f"<b>Event:</b> {event_num}<br>"
                f"<b>Instrument:</b> {instrument}<br>"
                f"<b>Y-axis:</b> {pres_col}"
            )
        lbl_info = QLabel(info_html)
        lbl_info.setStyleSheet("color: navy; font-size: 16px;")
        lbl_info.setWordWrap(True)
        right_panel.addWidget(lbl_info)

        right_panel.addSpacing(12)

        # ── Axis-variable selector (mode-specific) ─────────────────────────
        if mode == "thermograph":
            extra_params = {d: v for d, v in self._param_map.items()
                            if d != "Temperature"}
            if extra_params:
                row = QHBoxLayout()
                lbl = QLabel("<b>Y-axis variable:</b>")
                lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: navy;")
                self._axis_combo = QComboBox()
                self._axis_combo.setStyleSheet("font-size: 16px;")
                self._axis_combo.addItem("Temperature")
                for name in extra_params:
                    self._axis_combo.addItem(name)
                self._axis_combo.currentTextChanged.connect(self._switch_axis)
                row.addWidget(lbl)
                row.addWidget(self._axis_combo)
                row.addStretch()
                right_panel.addLayout(row)
        else:
            row = QHBoxLayout()
            lbl = QLabel("<b>X-axis variable:</b>")
            lbl.setStyleSheet("font-size: 16px; color: navy;")
            self._axis_combo = QComboBox()
            self._axis_combo.setStyleSheet("font-size: 16px; font-weight: bold;")
            for name in self._param_map:
                self._axis_combo.addItem(name)
            self._axis_combo.setCurrentText(x_col_default)
            self._axis_combo.currentTextChanged.connect(self._switch_axis)
            row.addWidget(lbl)
            row.addWidget(self._axis_combo)
            row.addStretch()
            right_panel.addLayout(row)

        right_panel.addSpacing(12)

        # ── Flag radio buttons ─────────────────────────────────────────────
        grp = QGroupBox("Assign Quality Codes for Selected Points:")
        grp.setStyleSheet("QGroupBox { font-weight: bold; color: navy; font-size: 16px; }")
        grp_layout = QVBoxLayout(grp)
        self._flag_group = QButtonGroup(self)
        for k, label in FLAG_LABELS.items():
            rb = QRadioButton(f"{k}: {label}")
            rb.setStyleSheet(
                f"color: {FLAG_COLORS[k]}; font-weight: bold; "
                f"font-family: serif; font-size: 16px;"
            )
            rb.setProperty("flag_value", k)
            self._flag_group.addButton(rb, k)
            grp_layout.addWidget(rb)
            if k == state["current_flag"]:
                rb.setChecked(True)
        self._flag_group.idClicked.connect(self._on_flag_selected)
        right_panel.addWidget(grp)

        right_panel.addStretch()

        # ── Buttons ────────────────────────────────────────────────────────
        def _btn(text, color):
            b = QPushButton(text)
            b.setStyleSheet(
                f"background-color: {color}; font-size: 16px; "
                f"font-weight: bold; padding: 6px;"
            )
            return b

        # Interaction mode buttons (CTD and thermograph both get these)
        self._btn_lasso    = _btn("⬤  Lasso",       "#ffcc66")
        self._btn_zoom_box = _btn("⬛  Zoom Box",    "#9999ff")
        self._btn_pan      = _btn("✥  Pan",          "#00ffcc")
        self._btn_reset    = _btn("⟲  Reset View",  "#e8e8ff")
        self._btn_undo     = _btn("Undo All Selections", "#66ccff")
        self._btn_export   = _btn("Export DataFrame",    "#ffb3e6")
        self._btn_continue = _btn("Continue Next >>",    "#ccff99")
        self._btn_exit     = _btn("Exit",                "salmon")

        if block_next_ == 1:
            self._btn_continue.setEnabled(False)

        for b in (self._btn_lasso, self._btn_zoom_box, self._btn_pan,
                  self._btn_reset, self._btn_undo, self._btn_export,
                  self._btn_continue, self._btn_exit):
            right_panel.addWidget(b)

        self._btn_lasso.clicked.connect(self._click_lasso)
        self._btn_zoom_box.clicked.connect(self._click_zoom_box)
        self._btn_pan.clicked.connect(self._click_pan)
        self._btn_reset.clicked.connect(self._click_reset_view)
        self._btn_undo.clicked.connect(self._click_deselect_all)
        self._btn_export.clicked.connect(lambda: self._export_dataframe(self._current_file))
        self._btn_continue.clicked.connect(self._click_continue)
        self._btn_exit.clicked.connect(self._click_exit)

        # Start in lasso mode
        self._click_lasso()

    # =======================================================================
    # Helpers
    # =======================================================================
    @staticmethod
    def _compute_margins(xs, ys):
        xm = (xs.max() - xs.min()) * 0.05 if xs.size > 1 else 1.0
        ym = (ys.max() - ys.min()) * 0.05 if ys.size > 1 else 1.0
        return xm or 0.5, ym or 0.5

    def _current_active_col(self) -> str:
        """Return the name of the column currently plotted on the selectable axis."""
        if self._mode == "thermograph":
            return getattr(self, "_y_col", "Temperature")
        else:
            return getattr(self, "_x_col", "Temperature")

    def _current_xs(self) -> np.ndarray:
        """X-values for the current scatter (thermograph: timestamps; CTD: param)."""
        if self._mode == "thermograph":
            return self._xnums
        col = self._x_col
        return (
            self._df[col].to_numpy() if col in self._df.columns
            else self._df.iloc[:, 0].to_numpy()
        )

    def _current_ys(self) -> np.ndarray:
        """Y-values for the current scatter (thermograph: param; CTD: pressure)."""
        if self._mode == "thermograph":
            col = getattr(self, "_y_col", "Temperature")
            return (
                self._df[col].to_numpy() if col in self._df.columns
                else self._df["Temperature"].to_numpy()
            )
        return self._pres_data

    # =======================================================================
    # Interaction mode management
    # =======================================================================
    def _set_button_active(self, active_btn):
        nav = {
            self._btn_lasso:    "#ffcc66",
            self._btn_zoom_box: "#9999ff",
            self._btn_pan:      "#00ffcc",
        }
        for btn, color in nav.items():
            style = (
                f"background-color: {color}; font-size: 16px; font-weight: bold; "
                f"padding: 6px; border: 3px solid #222222;"
                if btn is active_btn else
                f"background-color: {color}; font-size: 16px; font-weight: bold; padding: 6px;"
            )
            btn.setStyleSheet(style)

    def _click_lasso(self):
        self._lasso.resume()
        self._vb.setMouseMode(pg.ViewBox.PanMode)
        self._vb.setMouseEnabled(x=False, y=False)
        self._set_button_active(self._btn_lasso)
        logger.info("Lasso mode activated.")

    def _click_zoom_box(self):
        self._lasso.pause()
        self._vb.setMouseEnabled(x=True, y=True)
        self._vb.setMouseMode(pg.ViewBox.RectMode)
        self._set_button_active(self._btn_zoom_box)
        logger.info("Zoom Box mode activated.")

    def _click_pan(self):
        self._lasso.pause()
        self._vb.setMouseEnabled(x=True, y=True)
        self._vb.setMouseMode(pg.ViewBox.PanMode)
        self._set_button_active(self._btn_pan)
        logger.info("Pan mode activated.")

    # =======================================================================
    # Axis switching
    # =======================================================================
    def _switch_axis(self, col_name: str):
        """Handle Y-axis switch (thermograph) or X-axis switch (CTD)."""
        self._flag_col = f"qualityflag_{col_name}"
        self._state["active_display"] = col_name
        self._df["qualityflag"] = self._df[self._flag_col].copy()

        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]

        if self._mode == "thermograph":
            self._y_col = col_name
            ys = self._current_ys()
            self._scatter.setData(
                x=self._xnums, y=ys, brush=brushes, pen=pg.mkPen(None), size=8,
            )
            self._lasso._ys = ys
            valid = ys[~np.isnan(ys.astype(float))]
            if valid.size:
                y_margin = (valid.max() - valid.min()) * 0.05 or 1.0
                self._y_range = (valid.min() - y_margin, valid.max() + y_margin)
                self._pw.setYRange(*self._y_range, padding=0)
            self._pw.setLabel("left", col_name)

        else:  # ctd
            self._x_col = col_name
            xs = self._current_xs()
            self._scatter.setData(
                x=xs, y=self._pres_data, brush=brushes, pen=pg.mkPen(None), size=8,
            )
            self._lasso._xs = xs
            self._lasso._ys = self._pres_data
            x_margin, _ = self._compute_margins(xs, self._pres_data)
            self._x_range = (xs.min() - x_margin, xs.max() + x_margin)
            self._pw.setXRange(*self._x_range, padding=0)
            self._pw.setLabel("bottom", col_name)

        logger.info(f"Axis switched to: {col_name} (flag col: {self._flag_col})")

    # =======================================================================
    # Flag assignment
    # =======================================================================
    def _on_flag_selected(self, flag_id: int):
        self._state["current_flag"] = flag_id
        logger.info(f"Current flag set to {flag_id}")

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

    # =======================================================================
    # Selection events
    # =======================================================================
    def _on_lasso_select(self, indices: np.ndarray):
        if indices.size == 0:
            return
        active = self._current_active_col()
        logger.info(
            f"Lasso: {len(indices)} point(s) selected — "
            f"flag {self._state['current_flag']} on {active}"
        )
        self._apply_flags_to_points(indices)
        self._state["selection_groups"].append(pd.DataFrame({
            active: self._current_ys()[indices] if self._mode == "thermograph"
                    else self._current_xs()[indices],
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    def _on_points_clicked(self, _plot, points):
        indices = np.array([p.index() for p in points], dtype=int)
        if indices.size == 0:
            return
        active = self._current_active_col()
        logger.info(
            f"Click: {len(indices)} point(s) selected — "
            f"flag {self._state['current_flag']} on {active}"
        )
        self._apply_flags_to_points(indices)
        self._state["selection_groups"].append(pd.DataFrame({
            active: self._current_ys()[indices] if self._mode == "thermograph"
                    else self._current_xs()[indices],
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    # =======================================================================
    # Button slots
    # =======================================================================
    def _click_reset_view(self):
        self._pw.setXRange(*self._x_range, padding=0)
        self._pw.setYRange(*self._y_range, padding=0)

    def _click_deselect_all(self):
        self._state["selection_groups"].clear()
        logger.info("Undo All Selections — restoring original flags.")
        for fc, snap in self._qflag_snapshots.items():
            self._df[fc] = snap.copy()
        self._df["qualityflag"] = self._df[self._flag_col].copy()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]
        self._scatter.setBrush(brushes)
        if self._mode == "thermograph":
            self._lasso._ys = self._current_ys()
        else:
            self._lasso._xs = self._current_xs()
        self._state["scatter"] = self._scatter

    def _click_continue(self):
        self._state["applied"] = True
        logger.info("Continue clicked.")
        self.close()

    def _click_exit(self):
        global exit_requested
        self._state["user_exited"] = True
        self._state["exit_requested"] = True
        exit_requested = True
        logger.info("Exit clicked — exit_requested set True.")
        self.close()

    def _export_dataframe(self, current_file):
        self._state["applied"] = True
        stem = Path(str(current_file)).stem
        export_path, _ = QFileDialog.getSaveFileName(
            self, "Export DataFrame to CSV",
            f"{stem}_QC_Export.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not export_path:
            return
        try:
            df_export = self._df.copy()
            df_export.reset_index(inplace=True)
            df_export.rename(columns={"index": "SEQ_INDEX"}, inplace=True)
            df_export.to_csv(export_path, index=False)
            logger.info(f"DataFrame exported to {export_path}")
            QMessageBox.information(
                self, "Export Successful",
                f"✅ DataFrame exported successfully to:\n{export_path}",
            )
        except Exception as exc:
            logger.error(f"Failed to export DataFrame: {exc}")
            QMessageBox.critical(
                self, "Export Failed", f"❌ Failed to export DataFrame:\n{exc}",
            )

    def closeEvent(self, ev):
        self.closed.emit()
        super().closeEvent(ev)


# ===========================================================================
# Shared: Input selection dialog
# ===========================================================================
class InputDialog(QMainWindow):
    """Unified input dialog.

    ``mode``         : ``"thermograph"`` or ``"ctd"``
    ``review_mode``  : True → Review QC, False → Initial QC
    """

    def __init__(self, mode: str, review_mode: bool):
        super().__init__()
        self._mode = mode
        self.review_mode = review_mode
        label_map = {
            "thermograph": "Thermograph / MTR",
            "ctd": "CTD",
        }
        self.setWindowTitle(
            f"Datashop QC Toolbox — {label_map.get(mode, mode)} ODF Quality Flagging "
            f"({'Review' if review_mode else 'Initial'} QC Mode)"
        )
        self.resize(680, 320 if mode == "thermograph" else 280)
        
        # Set modality to block the rest of the application
        self.setWindowModality(Qt.WindowModality.ApplicationModal)        

        _base = Path(__file__).resolve().parent / "temporary"
        _base.mkdir(parents=True, exist_ok=True)
        self._meta_store = _base / f".last_{mode}_qc_reviewer.json"

        # Public attributes read by caller
        self.line_edit_text = ""
        self.input_data_folder = ""
        self.output_data_folder = ""
        self.wildcard_string = "*.ODF"
        self.metadata_file = ""          # thermograph only
        self.generate_batch = ""         # thermograph only
        self.result = None

        # ── Widgets ──────────────────────────────────────────────────────
        self._name_lbl = QLabel(
            "QC reviewer name:" if review_mode else "QC operator name:"
        )
        self._name_edit = QLineEdit()
        self._name_edit.setFixedHeight(28)
        self._name_edit.editingFinished.connect(
            lambda: setattr(self, "line_edit_text", self._name_edit.text().strip())
        )

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

        btns = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self._btn_box = QDialogButtonBox(btns)
        self._btn_box.accepted.connect(self._on_accept)
        self._btn_box.rejected.connect(self._on_reject)

        # Thermograph-specific: metadata file + batch name
        if mode == "thermograph":
            self._meta_lbl = QLabel("Select metadata file (optional for DFO BIO, required for FSRS):")
            self._meta_btn = QPushButton("Choose Metadata File")
            self._meta_btn.setFixedSize(200, 36)
            self._meta_btn.clicked.connect(self._choose_metadata)
            self._meta_path = QLineEdit()
            self._meta_path.setReadOnly(True)

            self._batch_lbl = QLabel("Batch name (optional):")
            self._batch_edit = QLineEdit()
            self._batch_edit.setFixedHeight(28)

        # ── Layout ───────────────────────────────────────────────────────
        layout = QVBoxLayout()

        row_name = QHBoxLayout()
        row_name.addWidget(self._name_lbl)
        row_name.addStretch()
        row_name.addWidget(self._remember_cb)
        layout.addLayout(row_name)
        layout.addWidget(self._name_edit)

        layout.addWidget(self._input_lbl)
        row_in = QHBoxLayout()
        row_in.addWidget(self._input_btn)
        row_in.addWidget(self._input_path)
        layout.addLayout(row_in)

        layout.addWidget(self._output_lbl)
        row_out = QHBoxLayout()
        row_out.addWidget(self._output_btn)
        row_out.addWidget(self._output_path)
        layout.addLayout(row_out)

        if mode == "thermograph":
            layout.addWidget(self._meta_lbl)
            row_meta = QHBoxLayout()
            row_meta.addWidget(self._meta_btn)
            row_meta.addWidget(self._meta_path)
            layout.addLayout(row_meta)

            layout.addWidget(self._batch_lbl)
            layout.addWidget(self._batch_edit)

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

    # ── Folder / file pickers ─────────────────────────────────────────────
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

    def _choose_metadata(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select metadata file", "",
            "Excel / CSV Files (*.xlsx *.xls *.csv);;All Files (*)",
        )
        if path:
            self.metadata_file = path
            self._meta_path.setText(path)

    # ── Accept / reject ───────────────────────────────────────────────────
    def _on_accept(self):
        self.line_edit_text = self._name_edit.text().strip()
        self.wildcard_string = self._wc_edit.text().strip() or "*.ODF"
        if self._mode == "thermograph":
            self.generate_batch = self._batch_edit.text().strip()
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

    # ── Persistent name storage ───────────────────────────────────────────
    def _save_name(self):
        try:
            self._meta_store.write_text(
                json.dumps({"remember": True, "name": self.line_edit_text}), encoding="utf-8"
            )
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


# ===========================================================================
# Shared: Log window
# ===========================================================================
class LogWindow(QWidget):
    """Unified log window with data-type selector, QC mode radio, Start and
    Exit buttons, and a scrolling log text area.

    Mirrors the interface of LogWindowThermographQC / LogWindowCTDQC but is
    a single class used for both data types.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Datashop ODF QC Toolbox")
        self.resize(900, 550)

        import logging

        from PySide6.QtWidgets import QTextEdit

        layout = QVBoxLayout(self)

        # ── Data-type selector ────────────────────────────────────────────
        dtype_box = QGroupBox("Data Type")
        dtype_box.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        dtype_layout = QHBoxLayout(dtype_box)
        self._rb_thermograph = QRadioButton("Thermograph / MTR (time-series)")
        self._rb_ctd = QRadioButton("CTD (profile)")
        self._rb_thermograph.setChecked(True)
        dtype_layout.addWidget(self._rb_thermograph)
        dtype_layout.addWidget(self._rb_ctd)
        layout.addWidget(dtype_box)

        # ── QC mode selector ──────────────────────────────────────────────
        mode_box = QGroupBox("QC Mode")
        mode_box.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        mode_layout = QHBoxLayout(mode_box)
        self.radio_opt = QRadioButton("Enable As QC Reviewer Mode")
        self.radio_initial = QRadioButton("Initial QC Mode")
        self.radio_initial.setChecked(True)
        mode_layout.addWidget(self.radio_initial)
        mode_layout.addWidget(self.radio_opt)
        layout.addWidget(mode_box)

        # ── Log area ──────────────────────────────────────────────────────
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setStyleSheet("font-family: Courier; font-size: 12px;")
        layout.addWidget(self._log_edit)

        # ── Control buttons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶  Start Visual QC Process")
        self.btn_start.setStyleSheet(
            "background-color: #4CAF50; color: white; font-size: 16px; "
            "font-weight: bold; padding: 8px;"
        )
        self.btn_exit = QPushButton("✖  Exit Program")
        self.btn_exit.setStyleSheet(
            "background-color: salmon; font-size: 16px; font-weight: bold; padding: 8px;"
        )
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_exit)
        layout.addLayout(btn_row)

        # ── Qt logging handler that appends to _log_edit ──────────────────
        class _QtHandler(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self._w = widget

            def emit(self, record):
                try:
                    msg = self.format(record)
                    self._w.append(msg)
                except Exception:
                    pass

        self.qtext_handler = _QtHandler(self._log_edit)
        self.qtext_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                              datefmt="%H:%M:%S")
        )

    @property
    def selected_data_type(self) -> str:
        return "thermograph" if self._rb_thermograph.isChecked() else "ctd"


# ===========================================================================
# Shared: prepare_output_folder
# ===========================================================================
def prepare_output_folder(
    in_folder_path: str, out_folder_path: str, qc_operator: str
) -> str:
    base_name_input = "Step_1_Create_ODF"
    in_folder_path = str(Path(in_folder_path).resolve())
    out_folder_path = str(Path(out_folder_path).resolve())

    base_name_output = "Step_2_Assign_QFlag"
    out_odf_path = Path(out_folder_path) / base_name_output
    out_odf_path = out_odf_path.resolve()

    if base_name_input.lower() in in_folder_path.lower():
        if (not out_odf_path.exists()) and (out_odf_path != Path(in_folder_path)):
            logger.info("Initial QC Mode: Creating output folder Step_2_Assign_QFlag")
            out_odf_path.mkdir(parents=True, exist_ok=False)
            logger.info(f"Created output folder: {out_odf_path}")
        else:
            logger.info("Initial QC Mode: Overwriting existing output folder Step_2_Assign_QFlag")
            try:
                shutil.rmtree(out_odf_path)
                out_odf_path.mkdir(parents=True, exist_ok=False)
                logger.warning(f"Overwriting existing folder: {out_odf_path}")
            except Exception as e:
                logger.error(f"Could not clear folder: {e}")
                out_odf_path.mkdir(parents=True, exist_ok=True)
    else:
        logger.info("Review QC Mode: Creating Step_3_Review_QFlag folder.")
        now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"Step_3_Review_QFlag_{qc_operator.strip().title()}_{now_ts}"
        out_odf_path = Path(out_folder_path) / new_name
        out_odf_path.mkdir(parents=True, exist_ok=False)
        logger.info(f"Created review output folder: {out_odf_path}")

    return str(out_odf_path)


# ===========================================================================
# Thermograph helpers
# ===========================================================================
def _parse_datetime(date_str, time_str):
    date_formats = [
        "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
        "%b-%d-%y", "%B-%d-%y", "%d-%b-%y", "%d-%B-%y",
    ]
    time_formats = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]
    if pd.isna(date_str) or date_str.strip() == "":
        return pd.NaT
    if pd.isna(time_str) or time_str.strip() == "":
        time_str = "12:00"
    dt_date = None
    for fmt in date_formats:
        try:
            dt_date = datetime.strptime(date_str, fmt).date()
            break
        except ValueError:
            continue
    if dt_date is None:
        return pd.NaT
    dt_time = None
    for fmt in time_formats:
        try:
            dt_time = datetime.strptime(time_str, fmt).time()
            break
        except ValueError:
            continue
    if dt_time is None:
        dt_time = datetime.strptime("12:00", "%H:%M").time()
    return f"{dt_date.strftime('%Y-%m-%d')} {dt_time.strftime('%H:%M:%S')}"


def _parse_to_utc(dt_str, tz_mode):
    if pd.isna(dt_str) or str(dt_str).strip() == "":
        return pd.NaT
    dt_str = re.sub(r"/[A-Z]{3}$", "", str(dt_str)).strip()
    try:
        dt = pd.to_datetime(dt_str, errors="coerce")
    except Exception:
        return pd.NaT
    if pd.isna(dt):
        return pd.NaT
    if tz_mode.lower() == "local":
        if dt.tzinfo is None:
            dt = ATLANTIC_TZ.localize(dt)
        return dt.astimezone(UTC)
    else:
        if dt.tzinfo is None:
            return UTC.localize(dt)
        return dt.astimezone(UTC)


def _validate_bio_metadata(meta: pd.DataFrame) -> bool:
    if meta is None or meta.empty:
        return False
    cols = set(meta.columns)
    if not ({"ID", "gauge"} & cols):
        logger.warning("Metadata invalid: neither 'ID' nor 'gauge' column found.")
        return False
    if not {"deploy", "recover"}.issubset(cols):
        logger.warning("Metadata invalid: 'deploy' and/or 'recover' column missing.")
        return False
    tz_candidates = {
        "instrument time zone", "Instrument Time Zone", "time zone",
        "Time zone", "Time Zone", "timezone", "TimeZone",
    }
    if not (tz_candidates & cols):
        logger.warning("Metadata invalid: no recognized time-zone column found.")
        return False
    return True


# ===========================================================================
# Thermograph QC core loop
# ===========================================================================
def qc_thermograph_data(
    in_folder_path: str,
    wildcard: str,
    out_folder_path: str,
    qc_operator: str,
    metadata_file_path: str,
    review_mode: bool,
    batch_name: str,
) -> dict:
    global exit_requested
    exit_requested = False
    batch_result = {"finished": False}
    qc_mode_user = 1 if review_mode else 0

    cwd = Path.cwd()
    try:
        os.chdir(in_folder_path)
        logger.info(f"Changed working dir to: {in_folder_path}")
    except Exception as e:
        logger.exception(f"Cannot change directory: {e}")
        return batch_result

    mtr_files = list(Path.cwd().glob(wildcard))
    if not mtr_files:
        logger.warning("No ODF files found in selected folder.")
        os.chdir(cwd)
        return batch_result

    out_odf_path = prepare_output_folder(in_folder_path, out_folder_path, qc_operator)
    os.chdir(cwd)

    state: dict = {}

    for idx, mtr_file in enumerate(mtr_files, start=1):
        if exit_requested:
            logger.warning("Exit requested — stopping QC loop.")
            break

        mtr_file_name = mtr_file.name
        logger.info(f"Reading file {idx}/{len(mtr_files)}: {mtr_file}")
        full_path = str(pathlib.Path(in_folder_path, mtr_file))

        try:
            mtr = ThermographHeader()
            mtr.read_odf(full_path)
        except Exception as e:
            logger.exception(f"Failed to read ODF {full_path}: {e}")
            continue

        orig_df = mtr.data.data_frame
        orig_df_stored = orig_df.copy()
        orig_df = orig_df.copy()
        orig_df.reset_index(drop=True, inplace=True)
        orig_df = pd.DataFrame(orig_df)

        temp = orig_df["TE90_01"].to_numpy()
        sytm = orig_df["SYTM_01"].str.lower().str.strip("'")

        # Build param_map
        _time_cols = {c for c in orig_df.columns if c.upper().startswith("SYTM")}
        param_map: dict = {}
        for col in orig_df.columns:
            if col in _time_cols:
                continue
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
                logger.info(f"Created missing flag column {flag_col} for {col}")
            if col == "TE90_01":
                display = "Temperature"
            elif col == "PRES_01":
                display = "Pressure"
            elif col == "DEPH_01":
                display = "Depth"
            else:
                display = col
            param_map[display] = (col, flag_col)

        _primary_data_col, _primary_flag_col = param_map.get(
            "Temperature", ("TE90_01", "QTE90_01")
        )
        # qflag = orig_df[_primary_flag_col].to_numpy().astype(int)

        try:
            dt = pd.to_datetime(sytm, format="%d-%b-%Y %H:%M:%S.%f")
        except Exception:
            dt = pd.to_datetime(sytm, infer_datetime_format=True, errors="coerce")

        df = pd.DataFrame({"Temperature": temp}, index=dt)
        for display, (data_col, flag_col) in param_map.items():
            if display == "Temperature":
                df["qualityflag_Temperature"] = orig_df[flag_col].to_numpy().astype(int)
            else:
                if display == "Pressure":
                    orig_df[data_col] = (orig_df[data_col] - 101.325) * 0.1
                df[display] = pd.to_numeric(orig_df[data_col], errors="coerce").to_numpy()
                df[f"qualityflag_{display}"] = orig_df[flag_col].to_numpy().astype(int)
        df["qualityflag"] = df["qualityflag_Temperature"].copy()

        state["df"] = df
        state["param_map"] = param_map
        state["active_display"] = "Temperature"

        # Header metadata
        file_name = f"{mtr._file_specification}.ODF"
        if file_name != mtr_file_name:
            logger.warning(f"Filename mismatch: Header '{file_name}' vs Actual '{mtr_file_name}'")
            batch_result["finished"] = False
            return batch_result
        logger.info(f"Filename verified: {mtr_file_name}")

        organization = mtr.cruise_header.organization
        start_datetime = mtr.event_header.start_date_time
        end_datetime = mtr.event_header.end_date_time
        event_num = mtr.event_header.event_number
        if event_num in (None, "", "NA", "NaN"):
            event_num = None
            logger.warning(f"Event number is invalid for {mtr_file}.")
        if event_num is None:
            match = re.search(r"_(\d{1,4})_", file_name)
            if match:
                event_num = match.group(1)
                logger.info(f"Event number extracted from filename: {event_num}")
            else:
                logger.warning(f"Could not determine event number: {file_name}")
        gauge_serial_number = mtr.instrument_header.serial_number
        instrument = mtr.instrument_header.instrument_type
        list_organization = ["DFO BIO", "FSRS"]

        if organization not in list_organization:
            logger.warning(f"Organization '{organization}' not recognized for {mtr_file}.")
            break

        # Metadata loading
        meta = None
        if organization == "FSRS":
            if not metadata_file_path or not Path(metadata_file_path).is_file():
                QMessageBox.critical(None, "Missing Metadata File",
                    "❌ FSRS processing requires a valid metadata file.")
                logger.error("FSRS selected but metadata_file_path is missing.")
                batch_result["finished"] = False
                return batch_result
            try:
                meta = mtr.read_metadata(metadata_file_path, organization)
                meta["date"] = meta["date"].astype(str)
                meta["time"] = meta["time"].astype(str)
                meta["time"] = meta["time"].where(
                    meta["time"].notna() & (meta["time"] != ""), "12:00"
                )
                meta["datetime"] = meta.apply(
                    lambda row: _parse_datetime(row["date"], row["time"]), axis=1
                )
                logger.info(f"Metadata loaded (FSRS): {metadata_file_path}")
            except Exception as e:
                QMessageBox.critical(None, "Metadata Read Error",
                    f"❌ Failed to read metadata:\n{e}")
                logger.exception(f"Failed to read metadata: {metadata_file_path}")
                batch_result["finished"] = False
                return batch_result

        if organization == "DFO BIO":
            if metadata_file_path and Path(metadata_file_path).is_file():
                try:
                    meta_tmp = mtr.read_metadata(metadata_file_path, organization)
                    if not _validate_bio_metadata(meta_tmp):
                        meta = None
                        logger.warning("Metadata failed validation; proceeding without it.")
                    else:
                        meta = meta_tmp
                        tz_col = next(
                            c for c in meta.columns
                            if c.lower().replace(" ", "") in {"instrumenttimezone", "timezone"}
                        )
                        meta["deploy_utc"] = meta.apply(
                            lambda r, _tz=tz_col: _parse_to_utc(r["deploy"], r[_tz]), axis=1
                        )
                        meta["recover_utc"] = meta.apply(
                            lambda r, _tz=tz_col: _parse_to_utc(r["recover"], r[_tz]), axis=1
                        )
                        logger.info(f"Metadata loaded (DFO BIO): {metadata_file_path}")
                except Exception as e:
                    logger.warning(f"Metadata could not be read: {e}. Proceeding without it.")
                    meta = None
            else:
                meta = None
                logger.info("No metadata file provided; proceeding without metadata.")

        # Deploy/recover window determination (unchanged from original)
        start_datetime_qc = start_datetime
        end_datetime_qc = end_datetime

        if organization == "FSRS":
            meta_subset = meta[meta["gauge"] == int(gauge_serial_number)]
            if not meta_subset.empty:
                if "datetime" in meta_subset.columns and not meta_subset["datetime"].isna().all():
                    meta_subset = meta_subset.copy()
                    meta_subset["datetime"] = pd.to_datetime(meta_subset["datetime"], errors="coerce")
                    meta_subset = meta_subset.dropna(subset=["datetime", "soak_days"])
                    if not meta_subset.empty:
                        idx_s = meta_subset["datetime"].idxmin()
                        start_datetime_qc = meta_subset.loc[idx_s, "datetime"] - pd.to_timedelta(
                            meta_subset.loc[idx_s, "soak_days"], unit="D"
                        )
                        idx_e = meta_subset["datetime"].idxmax()
                        end_datetime_qc = meta_subset.loc[idx_e, "datetime"]
                elif "date" in meta_subset.columns and not meta_subset["date"].isna().all():
                    meta_subset = meta_subset.copy()
                    meta_subset["date"] = pd.to_datetime(meta_subset["date"], errors="coerce")
                    meta_subset = meta_subset.dropna(subset=["date", "soak_days"])
                    if not meta_subset.empty:
                        idx_s = meta_subset["date"].idxmin()
                        start_datetime_qc = meta_subset.loc[idx_s, "date"] - pd.to_timedelta(
                            meta_subset.loc[idx_s, "soak_days"], unit="D"
                        )
                        idx_e = meta_subset["date"].idxmax()
                        end_datetime_qc = meta_subset.loc[idx_e, "date"]

        if organization == "DFO BIO":
            dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.0
            temp_rate = df["Temperature"].diff() / dt_minutes
            temp_rate = temp_rate.replace([np.inf, -np.inf], np.nan)
            temp_diff = df["Temperature"].diff()
            df["temp_rate"] = temp_rate
            df["temp_diff"] = temp_diff

            drop_threshold, rise_threshold, temp_jump_mag = -0.2, 0.2, 2.0

            def _best(candidates, key):
                return max(candidates, key=lambda x: x[key], default=None)

            dep_rate = [{"time": t, "severity": abs(temp_rate.loc[t]),
                         "temp_drop": abs(temp_diff.loc[t]) if not pd.isna(temp_diff.loc[t]) else 0.0}
                        for t in df.index[temp_rate < drop_threshold]]
            dep_jump = [{"time": t, "severity": abs(temp_diff.loc[t]),
                         "temp_drop": abs(temp_diff.loc[t])}
                        for t in df.index[temp_diff <= -temp_jump_mag]]
            br = _best(dep_rate, "severity")
            bj = _best(dep_jump, "severity")
            if br and bj:
                start_in_water = (br["time"] if br["time"] == bj["time"]
                                  else (bj["time"] if bj["temp_drop"] > br["temp_drop"]
                                        else (br["time"] if bj["temp_drop"] < br["temp_drop"]
                                              else min(br["time"], bj["time"]))))
            elif br:
                start_in_water = br["time"]
            elif bj:
                start_in_water = bj["time"]
            else:
                start_in_water = df.index[0]

            rec_rate = [{"time": t, "severity": abs(df.loc[t, "temp_rate"]),
                         "temp_rise": abs(df.loc[t, "temp_diff"]) if pd.notna(df.loc[t, "temp_diff"]) else 0.0}
                        for t in df.index[df["temp_rate"] > rise_threshold]]
            rec_jump = [{"time": t, "severity": abs(df.loc[t, "temp_diff"]),
                         "temp_rise": abs(df.loc[t, "temp_diff"])}
                        for t in df.index[df["temp_diff"] >= temp_jump_mag]]
            br = _best(rec_rate, "severity")
            bj = _best(rec_jump, "severity")
            if br and bj:
                end_in_water = (br["time"] if br["time"] == bj["time"]
                                else (bj["time"] if bj["temp_rise"] > br["temp_rise"]
                                      else (br["time"] if bj["temp_rise"] < br["temp_rise"]
                                            else max(br["time"], bj["time"]))))
            elif br:
                end_in_water = br["time"]
            elif bj:
                end_in_water = bj["time"]
            else:
                end_in_water = df.index[-1]

            if end_in_water <= start_in_water:
                start_in_water = df.index[0]
                end_in_water = df.index[-1]

            if meta is None:
                start_datetime_qc = pd.to_datetime(start_in_water)
                end_datetime_qc = pd.to_datetime(end_in_water)
            else:
                meta = meta.copy()
                meta_subset = (meta[meta["ID"] == int(gauge_serial_number)]
                               if "ID" in meta.columns else pd.DataFrame())
                if meta_subset.empty:
                    start_datetime_qc = pd.to_datetime(start_in_water, errors="coerce")
                    end_datetime_qc = pd.to_datetime(end_in_water, errors="coerce")
                else:
                    tol = timedelta(minutes=60)
                    meta_subset = meta_subset.copy()
                    if "deploy_utc" in meta_subset.columns and not meta_subset["deploy_utc"].isna().all():
                        meta_subset["deploy_utc"] = pd.to_datetime(meta_subset["deploy_utc"], errors="coerce")
                        s_meta = meta_subset["deploy_utc"].min()
                        if s_meta.tzinfo is not None:
                            s_meta = s_meta.tz_convert("UTC").tz_localize(None)
                        s_dt = pd.to_datetime(start_datetime, errors="coerce")
                        start_datetime_qc = start_in_water if (s_meta - s_dt) > tol else s_meta
                    else:
                        start_datetime_qc = pd.to_datetime(start_in_water, errors="coerce")
                    if "recover_utc" in meta_subset.columns and not meta_subset["recover_utc"].isna().all():
                        meta_subset["recover_utc"] = pd.to_datetime(meta_subset["recover_utc"], errors="coerce")
                        e_meta = meta_subset["recover_utc"].max()
                        if e_meta.tzinfo is not None:
                            e_meta = e_meta.tz_convert("UTC").tz_localize(None)
                        e_dt = pd.to_datetime(end_datetime, errors="coerce")
                        end_datetime_qc = end_in_water if (e_dt - e_meta) > tol else e_meta
                    else:
                        end_datetime_qc = pd.to_datetime(end_in_water, errors="coerce")

        logger.info(f"QC window: {start_datetime_qc} → {end_datetime_qc}")
        qc_start_ts = pd.to_datetime(start_datetime_qc).timestamp()
        qc_end_ts = pd.to_datetime(end_datetime_qc).timestamp()

        # QC mode detection
        has_previous_qc = np.any(df["qualityflag_Temperature"] != 0)
        if (not has_previous_qc) and qc_mode_user == 0:
            qc_mode_ = " QC Mode - Initial\n(No Previous QC Flags)"
            qc_mode_code_ = 0
            block_next_ = 0
        elif (not has_previous_qc) and qc_mode_user == 1:
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            logger.warning("QC Mode Mismatch: Review selected but no previous flags.")
            QMessageBox.warning(None, "QC Mode Mismatch",
                "⚠️ You selected Review QC Mode but no previous flags were found.\n\n"
                "Please run Initial QC Mode first.\n\nThis file will not proceed.")
        elif has_previous_qc and qc_mode_user == 1:
            qc_mode_ = " QC Mode - Review\n(With Previous QC Flags)"
            qc_mode_code_ = 1
            block_next_ = 0
        else:
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            logger.warning("QC Mode Mismatch: Initial selected but flags already exist.")
            QMessageBox.warning(None, "QC Mode Mismatch",
                "⚠️ You selected Initial QC Mode but existing flags were found.\n\n"
                "Please select Review QC Mode.\n\nThis file will not proceed.")

        logger.info(f"QC Mode: {qc_mode_.strip()}")

        xnums = np.array([pd.Timestamp(t).timestamp() for t in df.index])
        before_qc_mask = df.index < start_datetime_qc
        after_qc_mask = df.index > end_datetime_qc

        if qc_mode_code_ == 0:
            _all_flag_cols = [f"qualityflag_{d}" for d in param_map]
            for _fc in _all_flag_cols:
                df.loc[df.index < start_datetime_qc, _fc] = 4
                df.loc[df.index > end_datetime_qc, _fc] = 4
                _in_water = (df.index >= start_datetime_qc) & (df.index <= end_datetime_qc)
                df.loc[_in_water & ~df[_fc].isin([4]), _fc] = 1
            df["qualityflag"] = df["qualityflag_Temperature"].copy()
        else:
            df["qualityflag"] = df["qualityflag_Temperature"].copy()

        colors_initial = [FLAG_COLORS.get(int(f), "#808080") for f in df["qualityflag"]]

        state.clear()
        state.update({
            "selection_groups": [],
            "applied": False,
            "user_exited": False,
            "exit_requested": False,
            "current_flag": 4,
            "param_map": param_map,
            "active_display": "Temperature",
        })

        qc_win = QCWindow(
            mode="thermograph",
            df=df,
            state=state,
            xnums=xnums,
            qc_start_ts=qc_start_ts,
            qc_end_ts=qc_end_ts,
            start_datetime_qc=start_datetime_qc,
            end_datetime_qc=end_datetime_qc,
            batch_name=batch_name,
            colors_initial=colors_initial,
            instrument=instrument,
            organization=organization,
            qc_mode_=qc_mode_,
            qc_mode_code_=qc_mode_code_,
            block_next_=block_next_,
            idx=idx,
            file_list=mtr_files,
            current_file=mtr_file,
            param_map=param_map,
        )

        if block_next_ == 1:
            try:
                Path(out_odf_path).rmdir()
            except Exception:
                pass

        qc_win.show()
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.processEvents()
            app_inst.processEvents()

        logger.info(
            "QC Tips:\n"
            "  - Lasso: click and drag to select multiple points.\n"
            "  - Click individual points to select them.\n"
            "  - Choose the desired quality flag BEFORE selecting points.\n"
            "  - Click 'Continue Next >>' to apply flags and proceed.\n"
            "  - Click 'Exit' to stop immediately."
        )

        while qc_win.isVisible() and not state["exit_requested"]:
            if app_inst:
                app_inst.processEvents()
            time.sleep(0.05)

        if state["exit_requested"]:
            exit_requested = True

        # Write back flags
        if state["applied"]:
            if len(orig_df) != len(df):
                raise ValueError(
                    f"Size mismatch: orig_df {len(orig_df)} vs df {len(df)} rows."
                )
            combined_indices = (
                np.unique(np.concatenate([g["idx"].to_numpy()
                                          for g in state["selection_groups"]])).astype(int)
                if state["selection_groups"] else np.array([], dtype=int)
            )
            logger.info(f"Total of {len(combined_indices)} unique points flagged.")
            for display, (_data_col, flag_col) in param_map.items():
                df_flag_col = f"qualityflag_{display}"
                if len(combined_indices) == 0:
                    if qc_mode_code_ == 0:
                        orig_df[flag_col] = 1
                        orig_df.loc[before_qc_mask, flag_col] = 4
                        orig_df.loc[after_qc_mask, flag_col] = 4
                else:
                    if qc_mode_code_ == 0:
                        orig_df[flag_col] = 1
                        orig_df.loc[before_qc_mask, flag_col] = 4
                        orig_df.loc[after_qc_mask, flag_col] = 4
                        orig_df.iloc[combined_indices,
                                     orig_df.columns.get_loc(flag_col)] = \
                            df.iloc[combined_indices][df_flag_col].to_numpy()
                    elif qc_mode_code_ == 1:
                        orig_df.loc[before_qc_mask, flag_col] = 4
                        orig_df.loc[after_qc_mask, flag_col] = 4
                        orig_df.iloc[combined_indices,
                                     orig_df.columns.get_loc(flag_col)] = \
                            df.iloc[combined_indices][df_flag_col].to_numpy()

        # Log flag changes
        orig_df_after_qc = orig_df.copy()
        total_changed = 0
        for display, (_data_col, flag_col) in param_map.items():
            if flag_col not in orig_df_stored.columns:
                continue
            after = orig_df_after_qc[flag_col].to_numpy().astype(int)
            before = orig_df_stored[flag_col].to_numpy().astype(int)
            mask = before != after
            n = mask.sum()
            total_changed += n
            if n > 0:
                logger.info(f"  [{display} / {flag_col}] {n} flag(s) changed:")
                for (b, a), cnt in Counter(
                    zip(before[mask], after[mask], strict=True)
                ).items():
                    logger.info(f"    Flag {b} → {a}: {cnt}")
            else:
                logger.info(f"  [{display} / {flag_col}] No changes.")
        if total_changed == 0:
            logger.info(f"No quality flag changes for {mtr_file}")
        else:
            logger.info(f"Total flags changed for {mtr_file}: {total_changed}")

        # Write ODF
        try:
            mtr.data.data_frame = orig_df
            mtr.add_history()
            mtr.add_to_history(
                f"APPLIED QUALITY CODE FLAGGING AND PERFORMED INITIAL VISUAL QC BY {qc_operator.upper()}"
                if qc_mode_code_ == 0 else
                f"REVIEWED AND UPDATED QUALITY CODE FLAGGING BY {qc_operator.upper()}"
            )
            mtr.update_odf()
            file_spec = mtr.generate_file_spec()
            event_num_w = getattr(mtr.event_header, "event_number", None)
            if "__" in file_spec or event_num_w is None:
                match = re.search(r"_(\d{1,4})_", mtr_file_name)
                if match:
                    en = match.group(1).zfill(3)
                    parts = file_spec.split("__")
                    file_spec = (f"{parts[0]}_{en}_{parts[1]}" if len(parts) == 2
                                 else f"{file_spec.replace('.ODF', '')}_{en}.ODF")
                else:
                    raise ValueError(
                        f"Could not determine event number from filename: {mtr_file_name}"
                    )
            mtr.file_specification = file_spec
            out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
            logger.info(f"Writing [{idx}/{len(mtr_files)}]: {out_file}")
            mtr.write_odf(str(out_file), version=2.0)
            logger.info(f"Saved [{idx}/{len(mtr_files)}]: {out_file}")
        except Exception as e:
            logger.exception(f"Failed writing QC ODF for {mtr_file}: {e}")

    # End loop
    if not exit_requested and idx == len(mtr_files):
        logger.info(f"QC process completed for all {len(mtr_files)} files.")
        batch_result["finished"] = True
    elif exit_requested:
        logger.info(f"QC process interrupted ({idx} of {len(mtr_files)} files)")
    else:
        pass

    return batch_result


# ===========================================================================
# CTD QC core loop
# ===========================================================================
def qc_ctd_data(
    in_folder_path: str,
    wildcard: str,
    out_folder_path: str,
    qc_operator: str,
    review_mode: bool,
) -> dict:
    global exit_requested
    exit_requested = False
    batch_result = {"finished": False}
    qc_mode_user = 1 if review_mode else 0

    cwd = Path.cwd()
    try:
        os.chdir(in_folder_path)
        logger.info(f"Changed working dir to: {in_folder_path}")
    except Exception as e:
        logger.exception(f"Cannot change directory: {e}")
        return batch_result

    ctd_files = list(Path.cwd().glob(wildcard))
    logger.info(f"Found {len(ctd_files)} ODF file(s) matching '{wildcard}'")
    if not ctd_files:
        logger.warning("No ODF files found.")
        os.chdir(cwd)
        return batch_result

    out_odf_path = prepare_output_folder(in_folder_path, out_folder_path, qc_operator)
    logger.info(f"Output folder: {out_odf_path}")
    os.chdir(cwd)

    state: dict = {}

    for idx, ctd_file in enumerate(ctd_files, start=1):
        if exit_requested:
            logger.warning("Exit requested — stopping QC loop.")
            break

        ctd_file_name = ctd_file.name
        logger.info(f"Reading file {idx}/{len(ctd_files)}: {ctd_file}")
        full_path = str(pathlib.Path(in_folder_path, ctd_file))
        try:
            ctd = OdfHeader()
            ctd.read_odf(full_path)
        except Exception as e:
            logger.exception(f"Failed to read ODF {full_path}: {e}")
            continue

        orig_df = ctd.data.data_frame
        orig_df_stored = orig_df.copy()
        orig_df = orig_df.copy()
        orig_df.reset_index(drop=True, inplace=True)
        orig_df = pd.DataFrame(orig_df)

        # Filename verification
        file_name = f"{ctd.generate_file_spec()}.ODF"
        if file_name != ctd_file_name:
            logger.warning(f"Filename mismatch: '{file_name}' vs '{ctd_file_name}'")
            batch_result["finished"] = False
            return batch_result
        logger.info(f"Filename verified: {ctd_file_name}")

        organization = ctd.cruise_header.organization
        instrument = ctd.instrument_header.instrument_type
        station = getattr(ctd.event_header, "station_name", "—") or "—"
        event_num = getattr(ctd.event_header, "event_number", "—") or "—"
        logger.info(f"Organization: {organization}  Station: {station}  Event: {event_num}")

        # Pressure/depth column
        pres_col = next((c for c in _PRES_CANDIDATES if c in orig_df.columns), None)
        if pres_col is None:
            logger.warning(
                f"No pressure/depth column found in {ctd_file_name}. "
                f"Columns: {list(orig_df.columns)}. Skipping."
            )
            continue
        logger.info(f"Using '{pres_col}' as Y-axis.")

        # Build param_map
        _time_cols = {c for c in orig_df.columns if c.upper().startswith("SYTM")}
        _skip_as_y = {pres_col}
        param_map: dict = {}
        for col in orig_df.columns:
            if col in _time_cols or col in _skip_as_y:
                continue
            if col.upper().startswith("Q") and col[1:] in orig_df.columns:
                continue
            if col.upper().startswith("QCFF"):
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
                logger.info(f"Created missing flag column {flag_col} for {col}")
            if col in _TEMP_CANDIDATES:
                display = "Temperature"
            elif col.startswith(("CNDC", "COND")):
                display = "Conductivity"
            elif col.startswith("PSAL"):
                display = "Salinity"
            elif col.startswith("DENS"):
                display = "Density"
            elif col.startswith("SIGP"):
                display = "Potential Density"
            elif col.startswith("SIGT"):
                display = "Density Anomaly"
            elif col.startswith("POTM"):
                display = "Potential Temperature"
            elif col.startswith("FLOR"):
                display = "Fluorescence"
            elif col.startswith("CDOM"):
                display = "CDOM"
            elif col.startswith("TURB"):
                display = "Turbidity"
            elif col.startswith("CNTR"):
                display = "Scan Count"
            elif col.startswith("SNCNTR"):
                display = "Count of averaged records in bin"
            else:
                display = col
            param_map[display] = (col, flag_col)

        if not param_map:
            logger.warning(f"No plottable parameters in {ctd_file_name}. Skipping.")
            continue

        pres_flag_col = "Q" + pres_col
        if pres_flag_col not in orig_df.columns:
            orig_df[pres_flag_col] = np.zeros(len(orig_df), dtype=int)

        pres_arr = pd.to_numeric(orig_df[pres_col], errors="coerce").to_numpy()
        df = pd.DataFrame({pres_col: pres_arr})
        for display, (data_col, flag_col) in param_map.items():
            df[display] = pd.to_numeric(orig_df[data_col], errors="coerce").to_numpy()
            df[f"qualityflag_{display}"] = orig_df[flag_col].to_numpy().astype(int)

        x_col_default = "Temperature" if "Temperature" in param_map else next(iter(param_map))
        df["qualityflag"] = df[f"qualityflag_{x_col_default}"].copy()

        # QC mode detection
        has_previous_qc = np.any(df[f"qualityflag_{x_col_default}"] != 0)
        if (not has_previous_qc) and qc_mode_user == 0:
            qc_mode_ = " QC Mode - Initial\n(No Previous QC Flags)"
            qc_mode_code_ = 0
            block_next_ = 0
        elif (not has_previous_qc) and qc_mode_user == 1:
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            logger.warning("QC Mode Mismatch: Review mode but no previous flags.")
            QMessageBox.warning(None, "QC Mode Mismatch",
                "⚠️ You selected Review QC Mode but no previous flags were found.\n\n"
                "Please run Initial QC Mode first.\n\nThis file will not proceed.")
        elif has_previous_qc and qc_mode_user == 1:
            qc_mode_ = " QC Mode - Review\n(With Previous QC Flags)"
            qc_mode_code_ = 1
            block_next_ = 0
        else:
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            logger.warning("QC Mode Mismatch: Initial mode but flags already exist.")
            QMessageBox.warning(None, "QC Mode Mismatch",
                "⚠️ You selected Initial QC Mode but existing flags were found.\n\n"
                "Please select Review QC Mode.\n\nThis file will not proceed.")

        logger.info(f"QC Mode: {qc_mode_.strip()}")

        if qc_mode_code_ == 0:
            for d in param_map:
                df[f"qualityflag_{d}"] = 1
            df["qualityflag"] = df[f"qualityflag_{x_col_default}"].copy()

        colors_initial = [
            FLAG_COLORS.get(int(f), "#808080")
            for f in df[f"qualityflag_{x_col_default}"]
        ]

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

        qc_win = QCWindow(
            mode="ctd",
            df=df,
            state=state,
            pres_col=pres_col,
            x_col_default=x_col_default,
            station=station,
            event_num=str(event_num),
            colors_initial=colors_initial,
            instrument=instrument,
            organization=organization,
            qc_mode_=qc_mode_,
            qc_mode_code_=qc_mode_code_,
            block_next_=block_next_,
            idx=idx,
            file_list=ctd_files,
            current_file=ctd_file,
            param_map=param_map,
        )

        if block_next_ == 1:
            try:
                Path(out_odf_path).rmdir()
            except Exception:
                pass

        qc_win.show()
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.processEvents()
            app_inst.processEvents()

        logger.info(
            "CTD QC Tips:\n"
            "  - Use Lasso to select points in the profile.\n"
            "  - Click individual points to select them.\n"
            "  - Choose the desired quality flag BEFORE selecting points.\n"
            "  - Switch the X-axis variable using the combo box.\n"
            "  - Flags apply to the currently displayed parameter only.\n"
            "  - Click 'Continue Next >>' to save and move to the next file.\n"
            "  - Click 'Exit' to stop immediately."
        )

        while qc_win.isVisible() and not state["exit_requested"]:
            if app_inst:
                app_inst.processEvents()
            time.sleep(0.05)

        if state["exit_requested"]:
            exit_requested = True

        # Write back flags
        if state["applied"]:
            if len(orig_df) != len(df):
                logger.error(
                    f"Size mismatch: orig_df {len(orig_df)} vs df {len(df)} rows. Skipping."
                )
            else:
                combined_indices = (
                    np.unique(np.concatenate([g["idx"].to_numpy()
                                              for g in state["selection_groups"]])).astype(int)
                    if state["selection_groups"] else np.array([], dtype=int)
                )
                logger.info(
                    f"{len(combined_indices)} unique point(s) flagged across all x-axis variables."
                )
                for display, (_data_col, flag_col) in param_map.items():
                    df_fc = f"qualityflag_{display}"
                    if qc_mode_code_ == 0:
                        orig_df[flag_col] = 1
                        if len(combined_indices) > 0:
                            orig_df.iloc[combined_indices,
                                         orig_df.columns.get_loc(flag_col)] = \
                                df.iloc[combined_indices][df_fc].to_numpy()
                    elif qc_mode_code_ == 1:
                        if len(combined_indices) > 0:
                            orig_df.iloc[combined_indices,
                                         orig_df.columns.get_loc(flag_col)] = \
                                df.iloc[combined_indices][df_fc].to_numpy()

        # Log flag changes
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
                logger.info(f"  [{display} / {flag_col}] {n} flag(s) changed:")
                for (b, a), cnt in Counter(
                    zip(before[mask], after[mask], strict=True)
                ).items():
                    logger.info(f"    Flag {b} → {a}: {cnt}")
            else:
                logger.info(f"  [{display} / {flag_col}] No changes.")
        if total_changed == 0:
            logger.info(f"No quality flag changes for {ctd_file}")
        else:
            logger.info(f"Total flags changed for {ctd_file}: {total_changed}")

        # Write ODF
        try:
            ctd.data.data_frame = orig_df
            ctd.add_history()
            ctd.add_to_history(
                f"APPLIED QUALITY CODE FLAGGING AND PERFORMED INITIAL VISUAL QC BY {qc_operator.upper()}"
                if qc_mode_code_ == 0 else
                f"REVIEWED AND UPDATED QUALITY CODE FLAGGING BY {qc_operator.upper()}"
            )
            ctd.update_odf()
            file_spec = ctd.generate_file_spec()
            if "__" in file_spec or not event_num or event_num == "—":
                match = re.search(r"_(\d{1,4})_", ctd_file_name)
                if match:
                    en = match.group(1).zfill(3)
                    parts = file_spec.split("__")
                    file_spec = (f"{parts[0]}_{en}_{parts[1]}" if len(parts) == 2
                                 else f"{file_spec.replace('.ODF', '')}_{en}.ODF")
                else:
                    raise ValueError(
                        f"Could not determine event number from filename: {ctd_file_name}"
                    )
            ctd.file_specification = file_spec
            out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
            logger.info(f"Writing [{idx}/{len(ctd_files)}]: {out_file}")
            ctd.write_odf(str(out_file), version=2.0)
            logger.info(f"Saved [{idx}/{len(ctd_files)}]: {out_file}")
        except Exception as e:
            logger.exception(f"Failed writing QC ODF for {ctd_file}: {e}")

    # End loop
    if not exit_requested and idx == len(ctd_files):
        logger.info(f"CTD QC complete — all {len(ctd_files)} file(s) processed.")
        batch_result["finished"] = True
    elif exit_requested:
        logger.info(f"CTD QC interrupted after {idx}/{len(ctd_files)} file(s).")
    return batch_result


# ===========================================================================
# Input selection wrapper (shared)
# ===========================================================================
def main_select_inputs(mode: str, review_mode: bool):
    """Open the input dialog and return collected values.

    Returns for thermograph: (input, output, operator, metadata, batch, wildcard)
    Returns for CTD:         (input, output, operator, wildcard)
    """
    app_inst = QApplication.instance() or QApplication(sys.argv)
    app_inst.setStyle("Fusion")

    dlg = InputDialog(mode=mode, review_mode=review_mode)
    dlg.show()

    while dlg.isVisible():
        app_inst.processEvents()
        time.sleep(0.05)

    if dlg.result != "accept":
        if mode == "thermograph":
            return None, None, None, None, None, None
        return None, None, None, None

    if mode == "thermograph":
        return (
            dlg.input_data_folder,
            dlg.output_data_folder,
            dlg.line_edit_text,
            dlg.metadata_file,
            dlg.generate_batch,
            dlg.wildcard_string,
        )
    return (
        dlg.input_data_folder,
        dlg.output_data_folder,
        dlg.line_edit_text,
        dlg.wildcard_string,
    )


# ===========================================================================
# Public entry points
# ===========================================================================
def run_qc_thermograph_data(
    input_path: str,
    output_path: str,
    qc_operator: str,
    metadata_file_path: str,
    review_mode: bool,
    batch_name: str,
    wildcard: str,
) -> dict:
    logger.info(f"Starting Thermograph QC by {qc_operator} on {input_path}")
    result = qc_thermograph_data(
        input_path, wildcard, output_path,
        qc_operator, metadata_file_path, review_mode, batch_name,
    )
    if result["finished"]:
        logger.info("Thermograph QC completed successfully.")
        logger.info("Finished batch — click Start QC for a new batch.")
    else:
        logger.warning("Thermograph QC did not complete — check logs.")
    return result


def run_qc_ctd_data(
    input_path: str,
    output_path: str,
    qc_operator: str,
    review_mode: bool,
    wildcard: str,
) -> dict:
    logger.info(f"Starting CTD QC by {qc_operator} on {input_path}")
    result = qc_ctd_data(input_path, wildcard, output_path, qc_operator, review_mode)
    if result["finished"]:
        logger.info("CTD QC completed successfully.")
    else:
        logger.warning("CTD QC did not complete — check logs.")
    return result


# ===========================================================================
# Log-window Start button handler
# ===========================================================================
def start_qc_process(log_ui: LogWindow):
    global exit_requested
    exit_requested = False
    mode = log_ui.selected_data_type
    review_mode = log_ui.radio_opt.isChecked()

    logger.info(f"Start QC clicked — mode: {mode}, review: {review_mode}")

    if mode == "thermograph":
        input_path, output_path, operator, metadata_file_path, batch_name, wildcard = (
            main_select_inputs(mode, review_mode)
        )
        if not input_path or not output_path or not operator:
            logger.info("QC start aborted: missing required inputs.")
            return
        logger.info(
            "Thermograph QC Inputs:\n"
            f"  • QC Operator : {operator.strip().title()}\n"
            f"  • Input Path  : {input_path}\n"
            f"  • Output Path : {output_path}\n"
            f"  • Metadata    : {metadata_file_path}\n"
            f"  • Batch       : {batch_name}\n"
            f"  • Wildcard    : {wildcard}\n"
        )
        run_qc_thermograph_data(
            input_path, output_path, operator,
            metadata_file_path, review_mode, batch_name, wildcard,
        )
    else:  # ctd
        input_path, output_path, operator, wildcard = (
            main_select_inputs(mode, review_mode)
        )
        if not input_path or not output_path or not operator:
            logger.info("QC start aborted: missing required inputs.")
            return
        logger.info(
            "CTD QC Inputs:\n"
            f"  • QC Operator : {operator.strip().title()}\n"
            f"  • Input Path  : {input_path}\n"
            f"  • Output Path : {output_path}\n"
            f"  • Wildcard    : {wildcard}\n"
        )
        run_qc_ctd_data(input_path, output_path, operator, review_mode, wildcard)


# ===========================================================================
# Exit handler
# ===========================================================================
def exit_program(app_inst):
    global exit_requested
    exit_requested = True
    logger.info("Exit Program clicked.")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    app_inst.quit()


# ===========================================================================
# main()
# ===========================================================================
def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    log_window = LogWindow()
    log_window.show()

    if log_window.qtext_handler not in logger.handlers:
        logger.addHandler(log_window.qtext_handler)

    logger.info("Datashop ODF QC Toolbox started.")
    logger.info("Select a data type, choose a QC mode, then click 'Start Visual QC Process'.")

    log_window.radio_opt.toggled.connect(
        lambda checked: logger.info(
            f"QC Reviewer Mode is {'enabled' if checked else 'disabled'}"
        )
    )
    log_window._rb_thermograph.toggled.connect(
        lambda checked: logger.info(
            f"Data type set to {'Thermograph' if checked else 'CTD'}"
        )
    )
    log_window.btn_start.clicked.connect(lambda: start_qc_process(log_window))
    log_window.btn_exit.clicked.connect(lambda: exit_program(app))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
