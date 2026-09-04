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
    9: "Missing",
}

FLAG_COLORS: dict[int, str] = {
    0: "#808080",
    1: "#158726",
    2: "#AFB10D",
    3: "#E28112",
    4: "#FF0000",
    5: "#00008B",
    9: "#8B008B",
}

# Preferred column name candidates for CTD pressure/depth and temperature
_PRES_CANDIDATES = ["PRES_01", "PRES_02", "DEPH_01", "DEPH_02"]
_TEMP_CANDIDATES = ["TEMP_01", "TE90_01", "TEMP_02"]


# ===========================================================================
# Shared: LassoItem
# ===========================================================================
class LassoItem(pg.GraphicsObject):
    """Freehand lasso selector.

    The lasso selector is drawn as a red dashed line in data coordinates.
    It can test against one *or more* overlaid point sets at once (e.g. a
    down-cast and an up-cast plotted together), and always emits a list of
    index arrays — one per point set, in the same order the point sets were
    supplied — via sigSelected on mouse release.
    """
    sigSelected = pg.QtCore.Signal(object)  # emits list[np.ndarray] of int indices

    def __init__(self, plot_item: pg.PlotItem, xs: np.ndarray, ys: np.ndarray):
        """Initialize the lasso selector.

        Args:
            plot_item: Plot to draw the lasso on and hit-test against.
            xs: Initial x-coordinates of the point set to hit-test.
            ys: Initial y-coordinates of the point set to hit-test.
        """
        super().__init__()
        self._plot = plot_item
        self._vb = plot_item.getViewBox()
        self.set_point_sets((xs, ys))
        self._verts: list[tuple[float, float]] = []
        self._drawing = False
        self._enabled = True
        self._pen = QPen(QColor("red"), 0)
        self._pen.setStyle(Qt.DashLine)
        plot_item.addItem(self)

    # ── Point-set management ────────────────────────────────────────────────
    def set_point_sets(self, point_sets):
        """Replace the data the lasso hit-tests against.

        Accepts either a single ``(xs, ys)`` tuple, or a list of such tuples
        — one per overlaid data series. Internally always stored as a list.

        Args:
            point_sets: A single ``(xs, ys)`` tuple, or a list of
                ``(xs, ys)`` tuples, one per overlaid data series.
        """
        if (
            isinstance(point_sets, tuple)
            and len(point_sets) == 2
            and not isinstance(point_sets[0], (list, tuple))
        ):
            point_sets = [point_sets]
        self._point_sets = [(np.asarray(xs), np.asarray(ys)) for xs, ys in point_sets]

    # ── Enable / disable (for zoom/pan mode hand-off) ──────────────────────
    def pause(self):
        """Disable the lasso and discard any in-progress selection."""
        self._enabled = False
        self._drawing = False
        self._verts = []
        self.update()
        self.setAcceptedMouseButtons(Qt.NoButton)

    def resume(self):
        """Re-enable the lasso for left-button drawing."""
        self._enabled = True
        self.setAcceptedMouseButtons(Qt.LeftButton)

    # ── GraphicsObject required overrides ──────────────────────────────────
    def boundingRect(self):
        """Return the current view's bounding rectangle.

        Returns:
            The view box's current visible rectangle, in data
            coordinates.
        """
        return self._vb.viewRect()

    def paint(self, p, *args):
        """Paint the in-progress lasso outline.

        Args:
            p: ``QPainter`` to draw with.
            *args: Unused extra Qt paint arguments.
        """
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
        """Convert a scene position to data coordinates.

        Args:
            scene_pos: Scene-space position to convert.

        Returns:
            An ``(x, y)`` tuple in data coordinates.
        """
        pt = self._vb.mapSceneToView(scene_pos)
        return pt.x(), pt.y()

    def mousePressEvent(self, ev):
        """Start a new lasso outline on a left-button press.

        Args:
            ev: The mouse press event.
        """
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
        """Extend the in-progress lasso outline as the mouse moves.

        Args:
            ev: The mouse move event.
        """
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
        """Close the lasso outline and finalize the selection on release.

        Args:
            ev: The mouse release event.
        """
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
        """Hit-test the closed lasso polygon and emit :attr:`sigSelected`.

        Builds a closed polygon from the accumulated vertices and, for
        each point set registered via :meth:`set_point_sets`, finds
        the indices of points lying inside it. Emits
        :attr:`sigSelected` with the list of per-point-set index
        arrays if any point set has at least one match; polygons with
        fewer than 3 vertices are discarded without emitting.
        """
        if len(self._verts) < 3:
            self._verts = []
            self.update()
            return
        poly = QPolygonF([QPointF(x, y) for x, y in self._verts])
        results: list[np.ndarray] = []
        any_selected = False
        for xs, ys in self._point_sets:
            selected = [
                i for i, (x, y) in enumerate(zip(xs, ys, strict=True))
                if not (np.isnan(x) or np.isnan(y))
                and poly.containsPoint(QPointF(x, y), Qt.OddEvenFill)
            ]
            if selected:
                any_selected = True
            results.append(np.array(selected, dtype=int))
        self._verts = []
        self.update()
        if any_selected:
            self.sigSelected.emit(results)


# ===========================================================================
# Shared: QCWindow
# ===========================================================================
class QCWindow(QWidget):
    """Unified interactive QC window.

    Behaviour differs by mode — thermograph plots time-series data with
    timestamps on X and the parameter on Y; CTD plots a profile with the
    parameter on X and inverted pressure on Y.

    All flagging, lasso/click selection, undo, export, and navigation
    controls are identical for both modes.

    Args:
        mode (str): Plotting mode. Either ``"thermograph"`` or ``"ctd"``.
    """

    closed = pg.QtCore.Signal()

    def __init__(
        self,
        mode: str,          # "thermograph" or "ctd"
        df: pd.DataFrame | None,
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
        ctd_profiles: list[dict] | None = None,
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
        """Initialise the QC window and build all UI components.

            Args:
                mode: Plotting mode. Either `"thermograph"` for a time-series
                    plot or `"ctd"` for a pressure-profile plot.
                df: The dataset to display and flag.
                state: Shared application state passed in from the caller,
                    used to persist flags and UI settings across navigation.
                xnums: Unix timestamps corresponding to each row in `df`.
                    Required when `mode="thermograph"`.
                qc_start_ts: Unix timestamp marking the start of the QC window.
                    Thermograph mode only.
                qc_end_ts: Unix timestamp marking the end of the QC window.
                    Thermograph mode only.
                start_datetime_qc: Display-formatted start datetime for the QC
                    window label. Thermograph mode only.
                end_datetime_qc: Display-formatted end datetime for the QC
                    window label. Thermograph mode only.
                batch_name: Human-readable label for the current batch, shown
                    in the window title. Thermograph mode only.
                pres_col: Column name in `df` containing pressure values
                    (Y-axis). Required when `mode="ctd"` and `ctd_profiles`
                    is not supplied (legacy single-profile call).
                x_col_default: Column name to use as the default X-axis
                    parameter on first render. CTD mode only.
                station: Station identifier shown in the window title.
                    Defaults to `"—"` when not applicable.
                event_num: Event number shown in the window title.
                    Defaults to `"—"` when not applicable.
                ctd_profiles: List of one-or-more profile dicts to overlay
                    simultaneously in CTD mode — typically a down-cast and
                    an up-cast from the same station/event. Each dict needs
                    at minimum: `df`, `pres_col`, `param_map`,
                    `current_file`, and `colors_initial`; `cast_label` and
                    `symbol` are filled in automatically if omitted. When
                    `mode="ctd"` this is required; `df`/`pres_col` above are
                    then ignored (kept only for backwards compatibility).
                colors_initial: Per-point colour list matching the row order
                    of `df`. If `None`, a default palette is applied.
                instrument: Instrument identifier included in export metadata.
                organization: Organisation name included in export metadata.
                qc_mode_: Active QC mode label (e.g. `"auto"`, `"manual"`).
                qc_mode_code_: Numeric code corresponding to `qc_mode_`.
                block_next_: When non-zero, navigation to the next file is
                    blocked until outstanding flags are resolved.
                idx: Index of the current file within `file_list`. Defaults to `1`.
                file_list: Ordered list of file paths for batch navigation.
                    `None` disables prev/next controls.
                current_file: Path or identifier of the file currently loaded.
                param_map: Mapping of internal column names to display labels.
                    `None` causes raw column names to be shown.
            """
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

            # Snapshot all per-param flag columns for undo
            self._qflag_snapshots = {
                f"qualityflag_{d}": self._df[f"qualityflag_{d}"].to_numpy().copy()
                for d in self._param_map
            }

        elif mode == "ctd":
            self._profiles: list[dict] = ctd_profiles or []
            if not self._profiles:
                raise ValueError(
                    "QCWindow(mode='ctd') requires at least one entry in ctd_profiles."
                )
            primary = self._profiles[0]

            # X-axis parameters common to every overlaid profile — switching
            # the axis must stay valid for all of them at once.
            self._common_params = [
                d for d in primary["param_map"]
                if all(d in p["param_map"] for p in self._profiles)
            ] or list(primary["param_map"])

            self._x_col = (
                x_col_default if x_col_default in self._common_params
                else "Temperature" if "Temperature" in self._common_params
                else self._common_params[0]
            )
            self._flag_col = f"qualityflag_{self._x_col}"

            _SYMBOLS = ["o", "t", "s", "d", "+", "x", "star", "p"]
            for i, prof in enumerate(self._profiles):
                prof.setdefault("symbol", _SYMBOLS[i % len(_SYMBOLS)])
                prof.setdefault(
                    "cast_label",
                    Path(str(prof.get("current_file", f"Profile {i + 1}"))).stem,
                )
                prof["visible"] = True
                prof["pres_data"] = prof["df"][prof["pres_col"]].to_numpy()
                prof["qflag_snapshots"] = {
                    f"qualityflag_{d}": prof["df"][f"qualityflag_{d}"].to_numpy().copy()
                    for d in prof["param_map"]
                }

            # Backward-compat aliases (primary profile) for shared code paths
            self._df = primary["df"]
            self._pres_col = primary["pres_col"]
            self._pres_data = primary["pres_data"]

        # ── Window title ───────────────────────────────────────────────────
        if mode == "thermograph":
            self.setWindowTitle(
                f"[{idx}/{len(file_list)}] {organization} "
                f"Time-Series QC — {current_file}"
            )
            self.resize(1400, 700)
        elif mode == "ctd":
            cast_summary = (
                ", ".join(p["cast_label"] for p in self._profiles)
                if len(self._profiles) > 1 else ""
            )
            fname_display = ", ".join(
                Path(str(p["current_file"])).name for p in self._profiles
            )
            self.setWindowTitle(
                f"[{idx}/{len(file_list)}] {organization} "
                f"CTD Profile QC"
                f"{f' — {cast_summary}' if cast_summary else ''} — {fname_display}"
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

        elif mode == "ctd":

            self._pw.setLabel("bottom", self._x_col)
            pres_labels = sorted({p["pres_col"] for p in self._profiles})
            self._pw.setLabel("left", " / ".join(pres_labels))
            title_suffix = (
                f"<br><span style='font-size:9pt'>"
                f"{' &nbsp;|&nbsp; '.join(p['cast_label'] for p in self._profiles)}"
                f"</span>"
                if len(self._profiles) > 1 else ""
            )
            self._pw.setTitle(
                f"[{idx}/{len(file_list)}] {organization} CTD Profile — "
                f"Station: {station}  Event: {event_num}  "
                f"Instrument: {instrument}{title_suffix}"
            )
            self._pw.getPlotItem().invertY(True)

            if len(self._profiles) > 1:
                self._pw.addLegend(offset=(10, 10))

            for prof in self._profiles:
                xs_init = self._profile_xs(prof)
                colors = prof.get("colors_initial") or []
                brushes = (
                    [pg.mkBrush(QColor(c)) for c in colors]
                    if colors else pg.mkBrush(QColor(FLAG_COLORS[0]))
                )
                scatter = pg.PlotDataItem(
                    x=xs_init, y=prof["pres_data"],
                    symbol=prof["symbol"], symbolSize=8, symbolBrush=brushes,
                    symbolPen=pg.mkPen(None),
                    pen=pg.mkPen("k" if len(self._profiles) == 1 else "#888888", width=1),
                    connect="finite", name=prof["cast_label"],
                )
                self._pw.addItem(scatter)
                prof["scatter"] = scatter

            self._scatter = self._profiles[0]["scatter"]  # backward-compat alias
            self._state["scatter"] = self._scatter
            self._state["scatters"] = [p["scatter"] for p in self._profiles]

            all_xs = np.concatenate([self._profile_xs(p) for p in self._profiles])
            all_pres = np.concatenate([p["pres_data"] for p in self._profiles])
            x_margin, y_margin = self._compute_margins(all_xs, all_pres)
            valid_xs = all_xs[~np.isnan(all_xs)]
            valid_pres = all_pres[~np.isnan(all_pres)]
            self._x_range = (
                (valid_xs.min() - x_margin, valid_xs.max() + x_margin)
                if valid_xs.size else (0, 1)
            )
            self._y_range = (
                (valid_pres.min() - y_margin, valid_pres.max() + y_margin)
                if valid_pres.size else (0, 1)
            )
            self._pw.setXRange(*self._x_range, padding=0)
            self._pw.setYRange(*self._y_range, padding=0)
            self._pw.getPlotItem().enableAutoRange(enable=False)

            # Lasso hit-tests against every overlaid profile simultaneously
            self._lasso = LassoItem(
                self._pw.getPlotItem(),
                self._profile_xs(self._profiles[0]),
                self._profiles[0]["pres_data"],
            )
            self._lasso.set_point_sets(
                [(self._profile_xs(p), p["pres_data"]) for p in self._profiles]
            )

        # Wire up selection signals — PlotDataItem (CTD) exposes clicks via its
        # internal ScatterPlotItem; ScatterPlotItem (thermograph) exposes them directly.
        if self._mode == "ctd":
            for i, prof in enumerate(self._profiles):
                prof["scatter"].scatter.sigClicked.connect(
                    lambda _plot, points, pi=i: self._on_points_clicked(
                        _plot, points, profile_idx=pi
                    )
                )
        else:
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
        lbl_mode.setStyleSheet("color: green;")
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
        elif mode == "ctd":
            if len(self._profiles) > 1:
                file_lines = "<br>".join(
                    f"&nbsp;&nbsp;• {p['cast_label']} ({p['symbol']}): "
                    f"{Path(str(p['current_file'])).name}"
                    for p in self._profiles
                )
                info_html = (
                    f"<b>Station:</b> {station}<br>"
                    f"<b>Event:</b> {event_num}<br>"
                    f"<b>Instrument:</b> {instrument}<br>"
                    f"<b>Profiles ({len(self._profiles)}):</b><br>{file_lines}"
                )
            else:
                info_html = (
                    f"<b>Station:</b> {station}<br>"
                    f"<b>Event:</b> {event_num}<br>"
                    f"<b>Instrument:</b> {instrument}<br>"
                    f"<b>Y-axis:</b> {self._profiles[0]['pres_col']}"
                )
        lbl_info = QLabel(info_html)
        lbl_info.setStyleSheet("color: navy;")
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
                lbl.setStyleSheet("font-weight: bold; color: navy;")
                self._axis_combo = QComboBox()
                self._axis_combo.addItem("Temperature")
                for name in extra_params:
                    self._axis_combo.addItem(name)
                self._axis_combo.currentTextChanged.connect(self._switch_axis)
                row.addWidget(lbl)
                row.addWidget(self._axis_combo)
                row.addStretch()
                right_panel.addLayout(row)

        elif mode == "ctd":

            row = QHBoxLayout()
            lbl = QLabel("<b>X-axis variable:</b>")
            lbl.setStyleSheet("color: navy;")
            self._axis_combo = QComboBox()
            self._axis_combo.setStyleSheet("font-weight: bold;")
            for name in self._common_params:
                self._axis_combo.addItem(name)
            self._axis_combo.setCurrentText(self._x_col)
            self._axis_combo.currentTextChanged.connect(self._switch_axis)
            row.addWidget(lbl)
            row.addWidget(self._axis_combo)
            row.addStretch()
            right_panel.addLayout(row)

        right_panel.addSpacing(12)

        # ── Per-profile visibility toggles (multi-profile CTD overlay only) ──
        self._profile_checkboxes: list[QCheckBox] = []
        if mode == "ctd" and len(self._profiles) > 1:

            grp_vis = QGroupBox(f"Profiles Overlaid ({len(self._profiles)}):")
            grp_vis.setStyleSheet("QGroupBox { font-weight: bold; color: navy; }")
            vis_layout = QVBoxLayout(grp_vis)
            for i, prof in enumerate(self._profiles):
                cb = QCheckBox(
                    f"{prof['cast_label']}  [{prof['symbol']}]  — "
                    f"{Path(str(prof['current_file'])).name}"
                )
                cb.setChecked(True)
                cb.stateChanged.connect(
                    lambda cb_state, pi=i: self._toggle_profile_visibility(pi, cb_state)
                )
                vis_layout.addWidget(cb)
                self._profile_checkboxes.append(cb)
            right_panel.addWidget(grp_vis)

        right_panel.addSpacing(12)

        # ── Flag radio buttons ─────────────────────────────────────────────
        grp = QGroupBox("Assign Quality Codes for Selected Points:")
        grp.setStyleSheet("QGroupBox { font-weight: bold; color: navy; }")
        grp_layout = QVBoxLayout(grp)
        self._flag_group = QButtonGroup(self)
        for k, label in FLAG_LABELS.items():
            rb = QRadioButton(f"{k}: {label}")
            rb.setStyleSheet(
                f"color: {FLAG_COLORS[k]}; font-weight: bold; "
                f"font-family: serif;"
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
                f"background-color: {color}; "
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
    def _compute_margins(xs: np.ndarray, ys: np.ndarray):
        """Compute 5% plot-range margins for a pair of coordinate arrays.

        Args:
            xs: X-coordinates (NaNs are ignored).
            ys: Y-coordinates (NaNs are ignored).

        Returns:
            An ``(x_margin, y_margin)`` tuple, each defaulting to
            ``0.5`` if the corresponding array has fewer than 2 finite
            values or a zero range.
        """
        xs_mask = ~np.isnan(xs)
        xs = xs[xs_mask]
        ys_mask = ~np.isnan(ys)
        ys = ys[ys_mask]
        xm = (xs.max() - xs.min()) * 0.05 if xs.size > 1 else 1.0
        ym = (ys.max() - ys.min()) * 0.05 if ys.size > 1 else 1.0
        return xm or 0.5, ym or 0.5

    def _current_active_col(self) -> str:
        """Return the name of the column currently plotted on the selectable axis.

        Returns:
            ``self._y_col`` in thermograph mode, or ``self._x_col`` in
            CTD mode.
        """
        if self._mode == "thermograph":
            return getattr(self, "_y_col", "Temperature")
        else:
            return getattr(self, "_x_col", "Temperature")

    def _current_xs(self) -> np.ndarray:
        """X-values for the current scatter (thermograph: timestamps; CTD: param).

        Returns:
            ``self._xnums`` in thermograph mode, or the current
            X-axis column's values (falling back to the DataFrame's
            first column) in CTD mode.
        """
        if self._mode == "thermograph":
            return self._xnums
        col = self._x_col        
        return (
            self._df[col].to_numpy() if col in self._df.columns
            else self._df.iloc[:, 0].to_numpy()
        )

    def _current_ys(self) -> np.ndarray:
        """Y-values for the current scatter (thermograph: param; CTD: pressure).

        Returns:
            The current Y-axis column's values (falling back to
            ``"Temperature"``) in thermograph mode, or
            ``self._pres_data`` in CTD mode.
        """
        if self._mode == "thermograph":
            col = getattr(self, "_y_col", "Temperature")
            return (
                self._df[col].to_numpy() if col in self._df.columns
                else self._df["Temperature"].to_numpy()
            )
        return self._pres_data

    def _profile_xs(self, prof: dict) -> np.ndarray:
        """X-values (current axis param) for one CTD profile in self._profiles.

        Args:
            prof: One profile dict from ``self._profiles``.

        Returns:
            The current X-axis column's values from ``prof["df"]``, or
            an all-NaN array of matching length if the column is
            absent.
        """
        col = self._x_col
        df = prof["df"]
        return (
            df[col].to_numpy() if col in df.columns
            else np.full(len(prof["pres_data"]) if "pres_data" in prof
                         else len(df), np.nan)
        )

    # =======================================================================
    # Interaction mode management
    # =======================================================================
    def _set_button_active(self, active_btn):
        """Highlight the active interaction-mode button.

        Args:
            active_btn: The lasso/zoom-box/pan button to draw with a
                highlighted border; the others are drawn plain.
        """
        nav = {
            self._btn_lasso:    "#ffcc66",
            self._btn_zoom_box: "#9999ff",
            self._btn_pan:      "#00ffcc",
        }
        for btn, color in nav.items():
            style = (
                f"background-color: {color}; font-weight: bold; "
                f"padding: 6px; border: 3px solid #222222;"
                if btn is active_btn else
                f"background-color: {color}; font-weight: bold; padding: 6px;"
            )
            btn.setStyleSheet(style)

    def _click_lasso(self):
        """Switch to lasso selection mode."""
        self._lasso.resume()
        self._vb.setMouseMode(pg.ViewBox.PanMode)
        self._vb.setMouseEnabled(x=False, y=False)
        self._set_button_active(self._btn_lasso)
        logger.info("Lasso mode activated.")

    def _click_zoom_box(self):
        """Switch to rectangular zoom-box mode."""
        self._lasso.pause()
        self._vb.setMouseEnabled(x=True, y=True)
        self._vb.setMouseMode(pg.ViewBox.RectMode)
        self._set_button_active(self._btn_zoom_box)
        logger.info("Zoom Box mode activated.")

    def _click_pan(self):
        """Switch to pan mode."""
        self._lasso.pause()
        self._vb.setMouseEnabled(x=True, y=True)
        self._vb.setMouseMode(pg.ViewBox.PanMode)
        self._set_button_active(self._btn_pan)
        logger.info("Pan mode activated.")

    # =======================================================================
    # Axis switching
    # =======================================================================
    def _switch_axis(self, col_name: str):
        """Handle Y-axis switch (thermograph) or X-axis switch (CTD).

        Updates the active flag column and scatter plot(s) to reflect
        the newly selected parameter, recolors points by their
        existing flags, and rescales the corresponding axis.

        Args:
            col_name: Name of the parameter column to switch to. In
                CTD mode, ignored if not one of ``self._common_params``.
        """
        if self._mode == "thermograph":

            self._flag_col = f"qualityflag_{col_name}"
            self._state["active_display"] = col_name
            self._df["qualityflag"] = self._df[self._flag_col].copy()
            brushes = [
                pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                for f in self._df[self._flag_col]
            ]

            self._y_col = col_name
            ys = self._current_ys()
            self._scatter.setData(
                x=self._xnums, y=ys, brush=brushes, pen=pg.mkPen(None), size=8,
            )
            self._lasso.set_point_sets((self._xnums, ys))
            valid = ys[~np.isnan(ys.astype(float))]
            if valid.size:
                y_margin = (valid.max() - valid.min()) * 0.05 or 1.0
                self._y_range = (valid.min() - y_margin, valid.max() + y_margin)
                self._pw.setYRange(*self._y_range, padding=0)
            self._pw.setLabel("left", col_name)

        elif self._mode == "ctd":

            if col_name not in self._common_params:
                return
            self._x_col = col_name
            self._flag_col = f"qualityflag_{col_name}"
            self._state["active_display"] = col_name

            for prof in self._profiles:
                prof["df"]["qualityflag"] = prof["df"][self._flag_col].copy()
                xs = self._profile_xs(prof)
                brushes = [
                    pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                    for f in prof["df"][self._flag_col]
                ]
                prof["scatter"].setData(
                    x=xs, y=prof["pres_data"],
                    symbol=prof["symbol"], symbolSize=8,
                    symbolBrush=brushes, symbolPen=pg.mkPen(None),
                    pen=pg.mkPen("k" if len(self._profiles) == 1 else "#888888", width=1),
                    connect="finite", name=prof["cast_label"],
                )

            self._lasso.set_point_sets(
                [(self._profile_xs(p), p["pres_data"]) for p in self._profiles]
            )
            all_xs = np.concatenate([self._profile_xs(p) for p in self._profiles])
            valid_xs = all_xs[~np.isnan(all_xs)]
            if valid_xs.size:
                x_margin, _ = self._compute_margins(all_xs, np.concatenate(
                    [p["pres_data"] for p in self._profiles]
                ))
                self._x_range = (valid_xs.min() - x_margin, valid_xs.max() + x_margin)
                self._pw.setXRange(*self._x_range, padding=0)
            self._pw.setLabel("bottom", col_name)

        logger.info(f"Axis switched to: {col_name} (flag col: {self._flag_col})")

    # =======================================================================
    # Flag assignment
    # =======================================================================
    def _on_flag_selected(self, flag_id: int):
        """Store the newly selected QC flag as the "current" flag to apply.

        Args:
            flag_id: QC flag code selected via the radio buttons.
        """
        self._state["current_flag"] = flag_id
        logger.info(f"Current flag set to {flag_id}")

    def _apply_flags_to_points(self, indices: np.ndarray):
        """Apply the current flag to points at the given indices and recolor them.

        Args:
            indices: Row indices, into ``self._df``, of the points to
                flag.
        """
        flag = self._state["current_flag"]
        self._df.iloc[indices, self._df.columns.get_loc(self._flag_col)] = flag
        self._df["qualityflag"] = self._df[self._flag_col].copy()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]

        if self._mode == "thermograph":
            self._scatter.setData(
                x=self._xnums,
                y=self._current_ys(),
                brush=brushes,
                pen=pg.mkPen(None),
                size=8,
            )
        elif self._mode == "ctd":
            self._scatter.setData(
                x=self._current_xs(),
                y=self._pres_data,
                symbolBrush=brushes,
                symbolPen=pg.mkPen(None),
                symbolSize=8,
                pen=pg.mkPen("k", width=1),
            )
        # if self._mode == "ctd":
        #     self._scatter.scatter.setBrush(brushes)
        # else:
        #     self._scatter.setBrush(brushes)
        self._state["scatter"] = self._scatter

    def _apply_flags_to_profile(self, profile_idx: int, indices: np.ndarray):
        """CTD-only: apply the current flag to one overlaid profile's points.

        Args:
            profile_idx: Index into ``self._profiles`` of the profile
                to flag.
            indices: Row indices, into that profile's DataFrame, of
                the points to flag.
        """
        flag = self._state["current_flag"]
        prof = self._profiles[profile_idx]
        df = prof["df"]
        df.iloc[indices, df.columns.get_loc(self._flag_col)] = flag
        df["qualityflag"] = df[self._flag_col].copy()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in df[self._flag_col]
        ]
        prof["scatter"].setData(
            x=self._profile_xs(prof), y=prof["pres_data"],
            symbol=prof["symbol"], symbolSize=8,
            symbolBrush=brushes, symbolPen=pg.mkPen(None),
            pen=pg.mkPen("k" if len(self._profiles) == 1 else "#888888", width=1),
            connect="finite", name=prof["cast_label"],
        )

    def _record_selection(self, profile_idx: int, indices: np.ndarray):
        """CTD-only: track a selection group against a specific profile for undo/export.

        Args:
            profile_idx: Index into ``self._profiles`` of the profile
                the selection belongs to.
            indices: Row indices, into that profile's DataFrame, that
                were selected.
        """
        prof = self._profiles[profile_idx]
        groups = self._state.setdefault("selection_groups", {})
        groups.setdefault(profile_idx, []).append(pd.DataFrame({
            self._x_col: self._profile_xs(prof)[indices],
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    # =======================================================================
    # Selection events
    # =======================================================================
    def _on_lasso_select(self, selections):
        """Apply the current flag to points selected by the lasso.

        Args:
            selections: One index array per overlaid point set (as
                emitted by :attr:`LassoItem.sigSelected`). In CTD
                mode, index ``i`` corresponds to ``self._profiles[i]``;
                otherwise only the first array is used.
        """
        if self._mode == "ctd":
            for i, indices in enumerate(selections):
                if indices.size == 0:
                    continue
                logger.info(
                    f"Lasso: {len(indices)} point(s) selected on "
                    f"{self._profiles[i]['cast_label']} — "
                    f"flag {self._state['current_flag']} on {self._x_col}"
                )
                self._apply_flags_to_profile(i, indices)
                self._record_selection(i, indices)
            return

        indices = selections[0] if selections else np.array([], dtype=int)
        if indices.size == 0:
            return
        active = self._current_active_col()
        logger.info(
            f"Lasso: {len(indices)} point(s) selected — "
            f"flag {self._state['current_flag']} on {active}"
        )
        self._apply_flags_to_points(indices)
        self._state["selection_groups"].append(pd.DataFrame({
            active: self._current_ys()[indices],
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    def _on_points_clicked(self, _plot, points, profile_idx: int = 0):
        """Apply the current flag to individually clicked scatter points.

        Args:
            _plot: The plot item that was clicked (unused).
            points: The clicked ``SpotItem`` points.
            profile_idx: Index into ``self._profiles`` of the profile
                clicked. CTD mode only.
        """
        indices = np.array([p.index() for p in points], dtype=int)
        if indices.size == 0:
            return

        if self._mode == "ctd":
            logger.info(
                f"Click: {len(indices)} point(s) selected on "
                f"{self._profiles[profile_idx]['cast_label']} — "
                f"flag {self._state['current_flag']} on {self._x_col}"
            )
            self._apply_flags_to_profile(profile_idx, indices)
            self._record_selection(profile_idx, indices)
            return

        active = self._current_active_col()
        logger.info(
            f"Click: {len(indices)} point(s) selected — "
            f"flag {self._state['current_flag']} on {active}"
        )
        self._apply_flags_to_points(indices)
        self._state["selection_groups"].append(pd.DataFrame({
            active: self._current_ys()[indices],
            "idx": indices,
            "Flag": self._state["current_flag"],
        }))

    # =======================================================================
    # Button slots
    # =======================================================================
    def _click_reset_view(self):
        """Redraw the scatter(s) with current flag colors and reset the axis ranges."""
        if self._mode == "thermograph":
            brushes = [
                pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                for f in self._df[self._flag_col]
            ]
            self._scatter.setData(
                x=self._xnums,
                y=self._current_ys(),
                brush=brushes,
                pen=pg.mkPen(None),
                size=8,
            )
        elif self._mode == "ctd":
            for prof in self._profiles:
                brushes = [
                    pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                    for f in prof["df"][self._flag_col]
                ]
                prof["scatter"].setData(
                    x=self._profile_xs(prof), y=prof["pres_data"],
                    symbol=prof["symbol"], symbolSize=8,
                    symbolBrush=brushes, symbolPen=pg.mkPen(None),
                    pen=pg.mkPen("k" if len(self._profiles) == 1 else "#888888", width=1),
                    connect="finite", name=prof["cast_label"],
                )

        self._pw.setXRange(*self._x_range, padding=0)
        self._pw.setYRange(*self._y_range, padding=0)

    def _click_deselect_all(self):
        """Restore all quality flags to their pre-session snapshot values."""
        logger.info("Undo All Selections — restoring original flags.")

        if self._mode == "ctd":
            self._state["selection_groups"] = {}
            for prof in self._profiles:
                for fc, snap in prof["qflag_snapshots"].items():
                    prof["df"][fc] = snap.copy()
                prof["df"]["qualityflag"] = prof["df"][self._flag_col].copy()
                brushes = [
                    pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                    for f in prof["df"][self._flag_col]
                ]
                prof["scatter"].scatter.setBrush(brushes)
            self._lasso.set_point_sets(
                [(self._profile_xs(p), p["pres_data"]) for p in self._profiles]
            )
            return

        self._state["selection_groups"].clear()
        for fc, snap in self._qflag_snapshots.items():
            self._df[fc] = snap.copy()
        self._df["qualityflag"] = self._df[self._flag_col].copy()
        brushes = [
            pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
            for f in self._df[self._flag_col]
        ]
        self._scatter.setBrush(brushes)
        self._lasso.set_point_sets((self._xnums, self._current_ys()))
        self._state["scatter"] = self._scatter

    def _click_continue(self):
        """Mark the QC session as applied and close the window."""
        self._state["applied"] = True
        logger.info("Continue clicked.")
        self.close()

    def _click_exit(self):
        """Mark the QC session as user-exited and close the window."""
        global exit_requested
        self._state["user_exited"] = True
        self._state["exit_requested"] = True
        exit_requested = True
        logger.info("Exit clicked — exit_requested set True.")
        self.close()

    def _toggle_profile_visibility(self, profile_idx: int, cb_state):
        """CTD-only: show/hide one overlaid profile without affecting its flags.

        Args:
            profile_idx: Index into ``self._profiles`` of the profile
                to show or hide.
            cb_state: Checkbox state; truthy shows the profile,
                falsy hides it.
        """
        visible = bool(cb_state)
        prof = self._profiles[profile_idx]
        prof["visible"] = bool(visible)
        prof["scatter"].setVisible(bool(visible))
        logger.info(
            f"{prof['cast_label']} {'shown' if visible else 'hidden'} in overlay."
        )

    def _export_dataframe(self, current_file):
        """Export the QC'd DataFrame(s) to CSV.

        In CTD mode with more than one overlaid profile, prompts for a
        folder and exports one CSV per profile; otherwise prompts for
        a single save path and exports one CSV. Each export adds a
        ``SEQ_INDEX`` column from the DataFrame's row index.

        Args:
            current_file: Path or identifier used to derive the
                default export filename (single-profile case).
        """
        self._state["applied"] = True

        if self._mode == "ctd" and len(self._profiles) > 1:
            directory = QFileDialog.getExistingDirectory(
                self, "Select Folder to Export QC'd Profiles"
            )
            if not directory:
                return
            exported = []
            try:
                for prof in self._profiles:
                    stem = Path(str(prof["current_file"])).stem
                    out_path = Path(directory) / f"{stem}_QC_Export.csv"
                    df_export = prof["df"].copy()
                    df_export.reset_index(inplace=True)
                    df_export.rename(columns={"index": "SEQ_INDEX"}, inplace=True)
                    df_export.to_csv(out_path, index=False)
                    exported.append(str(out_path))
                logger.info(f"DataFrames exported to {directory}")
                QMessageBox.information(
                    self, "Export Successful",
                    "✅ Exported:\n" + "\n".join(exported),
                )
            except Exception as exc:
                logger.error(f"Failed to export DataFrames: {exc}")
                QMessageBox.critical(
                    self, "Export Failed", f"❌ Failed to export DataFrames:\n{exc}",
                )
            return

        df_to_export = self._profiles[0]["df"] if self._mode == "ctd" else self._df
        stem = Path(str(current_file)).stem
        export_path, _ = QFileDialog.getSaveFileName(
            self, "Export DataFrame to CSV",
            f"{stem}_QC_Export.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not export_path:
            return
        try:
            df_export = df_to_export.copy()
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
        """Emit :attr:`closed` before handling the standard close event.

        Args:
            ev: The Qt close event.
        """
        self.closed.emit()
        super().closeEvent(ev)


# ===========================================================================
# Shared: Input selection dialog
# ===========================================================================
class InputDialog(QMainWindow):
    """Unified input dialog.

    ``mode``         : ``"thermograph"`` or ``"ctd"``
    ``review_mode``  : True → Review QC, False → Initial QC

    Attributes:
        line_edit_text: QC operator/reviewer name.
        input_data_folder: Path to the selected input ODF folder.
        output_data_folder: Path to the selected output folder.
        wildcard_string: File-matching wildcard entered by the user.
        metadata_file: Path to the selected metadata file (thermograph
            mode only).
        generate_batch: Batch name entered by the user (thermograph
            mode only).
        result: ``"accept"`` or ``"reject"`` after the dialog closes.
    """

    def __init__(self, mode: str, review_mode: bool):
        """Build the dialog's widgets and layout.

        Args:
            mode: ``"thermograph"`` or ``"ctd"``.
            review_mode: ``True`` for reviewing previously QC'd files,
                ``False`` for initial QC.
        """
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
        """Prompt for and store the ODF input folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select ODF input folder")
        if folder:
            self.input_data_folder = folder
            self._input_path.setText(folder)

    def _choose_output(self):
        """Prompt for and store the QC output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select QC output folder")
        if folder:
            self.output_data_folder = folder
            self._output_path.setText(folder)

    def _choose_metadata(self):
        """Prompt for and store the metadata file (thermograph mode)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select metadata file", "",
            "Excel / CSV Files (*.xlsx *.xls *.csv);;All Files (*)",
        )
        if path:
            self.metadata_file = path
            self._meta_path.setText(path)

    # ── Accept / reject ───────────────────────────────────────────────────
    def _on_accept(self):
        """Validate required fields, optionally persist the name, and close.

        Requires the operator/reviewer name, input folder, and output
        folder to be set; otherwise shows a warning dialog and returns
        without closing. On success, sets :attr:`result` to
        ``"accept"``.
        """
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
        """Set :attr:`result` to ``"reject"`` and close the window."""
        self.result = "reject"
        self.close()

    # ── Persistent name storage ───────────────────────────────────────────
    def _save_name(self):
        """Persist the operator/reviewer name to :attr:`_meta_store` as JSON."""
        try:
            self._meta_store.write_text(
                json.dumps({"remember": True, "name": self.line_edit_text}), encoding="utf-8"
            )
        except Exception:
            pass

    def _clear_saved(self):
        """Delete the persisted name file, if one exists."""
        try:
            if self._meta_store.exists():
                self._meta_store.unlink()
        except Exception:
            pass

    def _load_saved(self):
        """Load and apply a previously persisted operator/reviewer name, if any."""
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

    Attributes:
        radio_opt: Toggle for enabling QC-reviewer mode.
        radio_initial: Toggle for initial-QC mode (checked by default).
        btn_start: Button that starts the visual QC process.
        btn_exit: Button that exits the program.
        qtext_handler: Logging handler that appends formatted records
            to the window's log text area.
    """

    def __init__(self):
        """Build the window's widgets and layout."""
        super().__init__()
        self.setWindowTitle("Datashop ODF QC Toolbox")
        self.resize(900, 550)

        import logging

        from PySide6.QtWidgets import QTextEdit

        layout = QVBoxLayout(self)

        # ── Data-type selector ────────────────────────────────────────────
        dtype_box = QGroupBox("Data Type")
        dtype_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        dtype_layout = QHBoxLayout(dtype_box)
        self._rb_thermograph = QRadioButton("Thermograph / MTR (time-series)")
        self._rb_ctd = QRadioButton("CTD (profile)")
        self._rb_thermograph.setChecked(True)
        dtype_layout.addWidget(self._rb_thermograph)
        dtype_layout.addWidget(self._rb_ctd)
        layout.addWidget(dtype_box)

        # ── QC mode selector ──────────────────────────────────────────────
        mode_box = QGroupBox("QC Mode")
        mode_box.setStyleSheet("QGroupBox { font-weight: bold; }")
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
        self._log_edit.setStyleSheet("font-family: Courier; ")
        layout.addWidget(self._log_edit)

        # ── Control buttons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶  Start Visual QC Process")
        self.btn_start.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-weight: bold; padding: 8px;"
        )
        self.btn_exit = QPushButton("✖  Exit Program")
        self.btn_exit.setStyleSheet(
            "background-color: salmon; font-weight: bold; padding: 8px;"
        )
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_exit)
        layout.addLayout(btn_row)

        # ── Qt logging handler that appends to _log_edit ──────────────────
        class _QtHandler(logging.Handler):
            """A logging.Handler that appends formatted records to a QTextEdit."""

            def __init__(self, widget):
                """Initialize the handler.

                Args:
                    widget: ``QTextEdit`` that formatted log records
                        are appended to.
                """
                super().__init__()
                self._w = widget

            def emit(self, record):
                """Format a log record and append it to the text widget.

                Args:
                    record: Log record to format and display. Any
                        exception raised while formatting or appending
                        is silently ignored.
                """
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
        """str: ``"thermograph"`` or ``"ctd"``, per the selected radio button."""
        return "thermograph" if self._rb_thermograph.isChecked() else "ctd"


# ===========================================================================
# Shared: prepare_output_folder
# ===========================================================================
def prepare_output_folder(
    in_folder_path: str, out_folder_path: str, qc_operator: str
) -> str:
    """Create the appropriate QC output folder for initial or review mode.

    If ``in_folder_path`` is a ``"Step_1_Create_ODF"`` folder (initial
    QC), creates (or clears and recreates) a ``Step_2_Assign_QFlag``
    folder under ``out_folder_path``. Otherwise (review QC), creates a
    new timestamped ``Step_3_Review_QFlag_<operator>_<timestamp>``
    folder under ``out_folder_path``.

    Args:
        in_folder_path: Path to the input folder. Only used to check
            whether it is a ``"Step_1_Create_ODF"`` folder.
        out_folder_path: Parent path under which the output folder is
            created.
        qc_operator: Name of the QC operator/reviewer, used in the
            review-mode folder name.

    Returns:
        The resolved path to the created output folder.
    """
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
    """Parse separate date/time strings into a combined datetime string.

    Tries several common date formats and several time formats;
    missing/blank time defaults to ``"12:00"``.

    Args:
        date_str: Date string to parse. Returns ``pd.NaT`` if missing
            or blank.
        time_str: Time string to parse. Defaults to ``"12:00"`` if
            missing, blank, or unparseable.

    Returns:
        A ``"YYYY-MM-DD HH:MM:SS"`` string, or ``pd.NaT`` if
        ``date_str`` is missing/blank or does not match any supported
        format.
    """
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
    """Parse a datetime string and convert it to UTC.

    Args:
        dt_str: Datetime string to parse. Any trailing
            ``"/<3-letter-code>"`` timezone abbreviation is stripped
            before parsing.
        tz_mode: If ``"local"`` (case-insensitive), a naive parsed
            datetime is localized to ``Canada/Atlantic`` before
            converting to UTC; otherwise a naive datetime is treated
            as already UTC.

    Returns:
        The datetime converted to UTC, or ``pd.NaT`` if ``dt_str`` is
        missing, blank, or unparseable.
    """
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
    """Check that a BIO metadata DataFrame has the required columns.

    Args:
        meta: Metadata DataFrame to validate.

    Returns:
        ``False`` if ``meta`` is ``None``/empty, lacks both ``"ID"``
        and ``"gauge"`` columns, lacks ``"deploy"``/``"recover"``
        columns, or lacks any recognized time-zone column name;
        ``True`` otherwise. A warning is logged for each failing
        check.
    """
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

# Replace all ODF null values in the dataframe with np.nan
def _null_to_na(df: pd.DataFrame) -> pd.DataFrame:
    """Replace ODF's numeric null sentinel with NaN.

    Args:
        df: DataFrame to convert.

    Returns:
        A copy of ``df`` with all ``-99.0`` values replaced by
        ``np.nan``.
    """
    return df.replace(-99.0, np.nan)
    

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
    """Run the interactive visual QC loop over a batch of thermograph ODF files.

    For each ODF file matching ``wildcard`` in ``in_folder_path``,
    reads the thermograph data, builds a parameter map of numeric
    columns, derives the deploy/recover QC time window (from metadata
    when available, otherwise from the event header), opens a
    :class:`QCWindow` for interactive flagging, applies the resulting
    flags to the full (including out-of-window) data, updates the ODF
    object's history and quality header, and writes the result to
    ``out_folder_path`` (via :func:`prepare_output_folder`) as both a
    new ODF file and a CSV file. Runs until all files are processed or
    the user exits.

    Args:
        in_folder_path: Path to the folder containing the input ODF
            files.
        wildcard: Glob pattern used to select which files in
            ``in_folder_path`` to process, e.g. ``"*.ODF"``.
        out_folder_path: Parent path under which the output folder is
            created (see :func:`prepare_output_folder`).
        qc_operator: Name of the QC operator/reviewer, recorded in the
            ODF history and used in the review-mode output folder
            name.
        metadata_file_path: Path to an optional metadata file used to
            derive per-cast deploy/recover times and time-zone
            information (DFO BIO / FSRS institutions).
        review_mode: If ``True``, run in review-QC mode (existing
            flags are reviewed and folder naming differs); if
            ``False``, run in initial-QC mode.
        batch_name: Human-readable label for the batch, shown in the
            QC window title.

    Returns:
        A dict with a ``"finished"`` key, ``True`` if every file in
        the batch was processed without an early exit, ``False``
        otherwise (including if the input directory could not be
        entered or no matching files were found).
    """
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

        # Deal with nulls and nans
        orig_df = _null_to_na(orig_df)
        # for col in orig_df.columns:
            # Create mask for finite values (not nan, not inf)
            # finite_mask = np.isfinite(orig_df[col])
            # Apply mask
            # orig_df[col] = orig_df[col][finite_mask]

        orig_df_stored = orig_df.copy()
        orig_df = pd.DataFrame(orig_df).reset_index(drop=True)

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
                """Return the candidate dict with the highest value of ``key``.

                Args:
                    candidates: List of dicts to search.
                    key: Dict key to compare candidates by.

                Returns:
                    The candidate with the maximum ``key`` value, or
                    ``None`` if ``candidates`` is empty.
                """
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

        colors_initial = [FLAG_COLORS.get(int(f), "#8A8787") for f in df["qualityflag"]]

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
                if qc_mode_code_ == 0:
                    orig_df[flag_col] = 1
                orig_df.loc[before_qc_mask, flag_col] = 4
                orig_df.loc[after_qc_mask, flag_col] = 4
                if len(combined_indices) > 0:
                    orig_df.iloc[combined_indices,
                                    orig_df.columns.get_loc(flag_col)] = \
                        df.iloc[combined_indices][df_flag_col].to_numpy()

            # Propagate pressure/depth flags to all other parameters.
            # Where the pressure or depth flag is higher than a parameter's own
            # flag, raise the parameter flag to match.
            pres_display = next(
                (d for d in ("Pressure", "Depth") if d in param_map), None
            )
            if pres_display is not None:
                _pres_flag_col = param_map[pres_display][1]
                pres_flags = orig_df[_pres_flag_col].to_numpy().astype(int)
                for display, (_data_col, flag_col) in param_map.items():
                    if display == pres_display:
                        continue
                    param_flags = orig_df[flag_col].to_numpy().astype(int)
                    elevated = pres_flags > param_flags
                    if elevated.any():
                        orig_df.loc[elevated, flag_col] = pres_flags[elevated]
                        logger.info(
                            f"  [{display} / {flag_col}] {elevated.sum()} row(s) "
                            f"elevated to match {pres_display} flag."
                        )
            else:
                logger.debug("No Pressure or Depth parameter found; skipping flag propagation.")

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
class _FilenameMismatchError(Exception):
    """Raised by _load_ctd_profile when the ODF's generated file spec doesn't
    match the file it was read from — a hard stop, matching legacy behaviour."""


def _cast_label_from_filename(ctd_file_name: str) -> str:
    """Infer a human-readable cast label from an ODF filename suffix.

    ODF CTD filenames typically end in ``_DN`` (down-cast) or ``_UP``
    (up-cast), e.g. ``CTD_BCD2024669_001_01_DN.ODF``. Falls back to the
    bare filename stem when no recognised suffix is present.

    Args:
        ctd_file_name: Name of the ODF file to infer a label from.

    Returns:
        ``"Downcast"``, ``"Upcast"``, or the filename stem.
    """
    stem = Path(ctd_file_name).stem
    upper = stem.upper()
    if upper.endswith("_DN"):
        return "Downcast"
    if upper.endswith("_UP"):
        return "Upcast"
    return stem


def _load_ctd_profile(ctd_file: Path, in_folder_path: str, qc_mode_user: int) -> dict | None:
    """Read one ODF file and prepare everything QCWindow needs to plot it.

    Builds a parameter map of plottable numeric columns (creating any
    missing quality-flag columns), determines the QC mode (initial vs.
    review) by checking for pre-existing flags against the requested
    mode, and warns the user if the two are mismatched.

    Args:
        ctd_file: Path to the ODF file to read, relative to
            ``in_folder_path``.
        in_folder_path: Path to the folder containing ``ctd_file``.
        qc_mode_user: Requested QC mode: ``0`` for initial QC, ``1``
            for review QC.

    Returns:
        A dict of everything :class:`QCWindow` needs to plot and QC
        this profile (``ctd``, ``df``, ``orig_df``, ``pres_col``,
        ``param_map``, QC-mode info, etc.), or ``None`` if the file
        should be skipped (unreadable, no pressure column, or no
        plottable parameters).

    Raises:
        _FilenameMismatchError: If the ODF's generated file spec
            doesn't match the file it was read from — a hard stop,
            matching legacy behaviour.
    """
    ctd_file_name = ctd_file.name
    logger.info(f"Reading file: {ctd_file}")
    full_path = str(pathlib.Path(in_folder_path, ctd_file))
    try:
        ctd = OdfHeader()
        ctd.read_odf(full_path)
    except Exception as e:
        logger.exception(f"Failed to read ODF {full_path}: {e}")
        return None

    orig_df = ctd.data.data_frame
    orig_df = _null_to_na(orig_df)
    orig_df_stored = orig_df.copy()
    orig_df = pd.DataFrame(orig_df).reset_index(drop=True)

    # Filename verification
    file_name = f"{ctd.generate_file_spec()}.ODF"
    if file_name != ctd_file_name:
        logger.warning(f"Filename mismatch: '{file_name}' vs '{ctd_file_name}'")
        raise _FilenameMismatchError(ctd_file_name)
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
        return None
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
        elif col.startswith("CNTR"):
            display = "Scan Count"
        elif col.startswith("SNCNTR"):
            display = "Count of averaged records in bin"
        else:
            display = col
        param_map[display] = (col, flag_col)

    if not param_map:
        logger.warning(f"No plottable parameters in {ctd_file_name}. Skipping.")
        return None

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

    return {
        "ctd": ctd,
        "df": df,
        "orig_df": orig_df,
        "orig_df_stored": orig_df_stored,
        "pres_col": pres_col,
        "param_map": param_map,
        "colors_initial": colors_initial,
        "current_file": ctd_file,
        "ctd_file_name": ctd_file_name,
        "cast_label": _cast_label_from_filename(ctd_file_name),
        "station": station,
        "event_num": event_num,
        "organization": organization,
        "instrument": instrument,
        "qc_mode_": qc_mode_,
        "qc_mode_code_": qc_mode_code_,
        "block_next_": block_next_,
        "x_col_default": x_col_default,
    }


def _group_ctd_profiles(profiles: list[dict]) -> list[list[dict]]:
    """Group loaded CTD profiles by (station, event) so that associated
    casts — typically a down-cast and an up-cast of the same event — are
    QC'd together in one overlaid window. Downcasts are ordered before
    upcasts within a group; original discovery order is otherwise preserved.

    Args:
        profiles: Profile dicts as returned by :func:`_load_ctd_profile`.

    Returns:
        A list of groups, each a list of profile dicts sharing the
        same station and event number, in original discovery order.
    """
    groups: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for p in profiles:
        key = (p["station"], str(p["event_num"]))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)

    _rank = {"Downcast": 0, "Upcast": 1}
    for key in order:
        groups[key].sort(key=lambda p: _rank.get(p["cast_label"], 0.5))
    return [groups[key] for key in order]


def qc_ctd_data(
    in_folder_path: str,
    wildcard: str,
    out_folder_path: str,
    qc_operator: str,
    review_mode: bool,
) -> dict:
    """Run the interactive visual QC loop over a batch of CTD ODF files.

    Loads every ODF file matching ``wildcard`` in ``in_folder_path``
    (via :func:`_load_ctd_profile`), groups associated casts (e.g. a
    down-cast and up-cast of the same station/event) together via
    :func:`_group_ctd_profiles`, then for each group opens a single
    overlaid :class:`QCWindow` for interactive flagging. After each
    window closes, applies the resulting flags to each profile in the
    group, updates its ODF object's history and quality header, and
    writes the result to ``out_folder_path`` (via
    :func:`prepare_output_folder`) as both a new ODF file and a CSV
    file. Runs until every group is processed or the user exits.

    Args:
        in_folder_path: Path to the folder containing the input ODF
            files.
        wildcard: Glob pattern used to select which files in
            ``in_folder_path`` to process, e.g. ``"*.ODF"``.
        out_folder_path: Parent path under which the output folder is
            created (see :func:`prepare_output_folder`).
        qc_operator: Name of the QC operator/reviewer, recorded in the
            ODF history and used in the review-mode output folder
            name.
        review_mode: If ``True``, run in review-QC mode (existing
            flags are reviewed); if ``False``, run in initial-QC mode.

    Returns:
        A dict with a ``"finished"`` key, ``True`` if every group was
        processed without an early exit, ``False`` otherwise
        (including if the input directory could not be entered, no
        matching files were found, or a filename/file-spec mismatch
        was encountered).
    """
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

    # ── Pass 1: load every file, then group associated casts together ──────
    loaded_profiles: list[dict] = []
    for ctd_file in ctd_files:
        try:
            profile = _load_ctd_profile(ctd_file, in_folder_path, qc_mode_user)
        except _FilenameMismatchError:
            batch_result["finished"] = False
            return batch_result
        if profile is not None:
            loaded_profiles.append(profile)

    groups = _group_ctd_profiles(loaded_profiles)
    logger.info(
        f"Grouped {len(loaded_profiles)} file(s) into {len(groups)} QC window(s) "
        f"(associated casts, e.g. down/up, are overlaid together)."
    )

    state: dict = {}
    group_idx = 0

    # ── Pass 2: QC each group (1 or more overlaid profiles) interactively ──
    for group_idx, group in enumerate(groups, start=1):
        if exit_requested:
            logger.warning("Exit requested — stopping QC loop.")
            break

        file_names = ", ".join(p["ctd_file_name"] for p in group)
        logger.info(
            f"QC group {group_idx}/{len(groups)}: {len(group)} profile(s) — {file_names}"
        )

        primary = group[0]
        # Represent the group's combined QC mode / block-next state as the
        # most restrictive across its profiles, since they're QC'd together.
        qc_mode_ = primary["qc_mode_"]
        qc_mode_code_ = max(p["qc_mode_code_"] for p in group)
        block_next_ = max(p["block_next_"] for p in group)
        instrument = " / ".join(dict.fromkeys(p["instrument"] for p in group))

        state.clear()
        state.update({
            "selection_groups": {},
            "applied": False,
            "user_exited": False,
            "exit_requested": False,
            "current_flag": 4,
            "param_map": primary["param_map"],
            "active_display": primary["x_col_default"],
        })

        qc_win = QCWindow(
            mode="ctd",
            df=None,
            state=state,
            x_col_default=primary["x_col_default"],
            station=primary["station"],
            event_num=str(primary["event_num"]),
            ctd_profiles=group,
            instrument=instrument,
            organization=primary["organization"],
            qc_mode_=qc_mode_,
            qc_mode_code_=qc_mode_code_,
            block_next_=block_next_,
            idx=group_idx,
            file_list=groups,
            current_file=primary["current_file"],
            param_map=primary["param_map"],
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
            "  - When multiple casts are overlaid (e.g. down/up), each is "
            "flagged independently — use the profile checkboxes to hide one.\n"
            "  - Click 'Continue Next >>' to save and move to the next group.\n"
            "  - Click 'Exit' to stop immediately."
        )

        while qc_win.isVisible() and not state["exit_requested"]:
            if app_inst:
                app_inst.processEvents()
            time.sleep(0.05)

        if state["exit_requested"]:
            exit_requested = True

        # Write back flags and save each profile in the group.
        for profile_idx, profile in enumerate(group):
            ctd = profile["ctd"]
            ctd_file = profile["current_file"]
            ctd_file_name = profile["ctd_file_name"]
            orig_df = profile["orig_df"]
            orig_df_stored = profile["orig_df_stored"]
            df = profile["df"]
            param_map = profile["param_map"]
            qc_mode_code_p = profile["qc_mode_code_"]
            event_num = profile["event_num"]

            if state["applied"]:
                if len(orig_df) != len(df):
                    logger.error(
                        f"Size mismatch: orig_df {len(orig_df)} vs df {len(df)} rows "
                        f"for {ctd_file_name}. Skipping write-back."
                    )
                else:
                    idx_lists = state["selection_groups"].get(profile_idx, [])
                    combined_indices = (
                        np.unique(np.concatenate(
                            [g["idx"].to_numpy() for g in idx_lists]
                        )).astype(int)
                        if idx_lists else np.array([], dtype=int)
                    )
                    logger.info(
                        f"{len(combined_indices)} unique point(s) flagged across all "
                        f"x-axis variables for {ctd_file_name}."
                    )
                    for display, (_data_col, flag_col) in param_map.items():
                        df_fc = f"qualityflag_{display}"
                        if qc_mode_code_p == 0:
                            orig_df[flag_col] = 1
                        if len(combined_indices) > 0:
                            orig_df.iloc[combined_indices,
                                            orig_df.columns.get_loc(flag_col)] = \
                                df.iloc[combined_indices][df_fc].to_numpy()

            # Log flag changes
            orig_df_after = orig_df.copy()
            total_changed = 0
            for display, (data_col, flag_col) in param_map.items():
                if flag_col not in orig_df_stored.columns:
                    continue
                after = orig_df_after[flag_col].to_numpy().astype(int)
                before = orig_df_stored[flag_col].to_numpy().astype(int)
                mask = before != after
                n = mask.sum()
                total_changed += n
                if n > 0:
                    logger.info(f"  [{display} / {data_col} / {flag_col}] {n} flag(s) changed:")
                    for (b, a), cnt in Counter(
                        zip(before[mask], after[mask], strict=True)
                    ).items():
                        logger.info(f"    Flag {b} → {a}: {cnt}")
                else:
                    logger.info(f"  [{display} / {data_col} / {flag_col}] No changes.")
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
                    if qc_mode_code_p == 0 else
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
                logger.info(f"Writing [{group_idx}/{len(groups)}]: {out_file}")
                ctd.write_odf(str(out_file), version=2.0)
                logger.info(f"Saved [{group_idx}/{len(groups)}]: {out_file}")
            except Exception as e:
                logger.exception(f"Failed writing QC ODF for {ctd_file}: {e}")

    # End loop
    if not exit_requested and group_idx == len(groups):
        logger.info(
            f"CTD QC complete — all {len(groups)} group(s) "
            f"({len(loaded_profiles)} file(s)) processed."
        )
        batch_result["finished"] = True
    elif exit_requested:
        logger.info(f"CTD QC interrupted after {group_idx}/{len(groups)} group(s).")
    return batch_result


# ===========================================================================
# Input selection wrapper (shared)
# ===========================================================================
def main_select_inputs(mode: str, review_mode: bool):
    """Open the input dialog and return collected values.

    Instantiates a Qt application if none exists, shows an
    :class:`InputDialog` for ``mode``, and blocks (processing events)
    until it closes.

    Args:
        mode: ``"thermograph"`` or ``"ctd"``.
        review_mode: ``True`` for reviewing previously QC'd files,
            ``False`` for initial QC.

    Returns:
        For ``mode="thermograph"``: a 6-tuple of ``(input_path,
        output_path, operator, metadata_file_path, batch_name,
        wildcard)``. For ``mode="ctd"``: a 4-tuple of ``(input_path,
        output_path, operator, wildcard)``. All elements are ``None``
        if the dialog was not accepted.
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
    """Run :func:`qc_thermograph_data` and log the outcome.

    Args:
        input_path: Path to the folder containing the input ODF files.
        output_path: Parent path under which the output folder is
            created.
        qc_operator: Name of the QC operator/reviewer.
        metadata_file_path: Path to an optional metadata file.
        review_mode: ``True`` for review QC, ``False`` for initial QC.
        batch_name: Human-readable label for the batch.
        wildcard: Glob pattern used to select which files to process.

    Returns:
        The dict returned by :func:`qc_thermograph_data`.
    """
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
    """Run :func:`qc_ctd_data` and log the outcome.

    Args:
        input_path: Path to the folder containing the input ODF files.
        output_path: Parent path under which the output folder is
            created.
        qc_operator: Name of the QC operator/reviewer.
        review_mode: ``True`` for review QC, ``False`` for initial QC.
        wildcard: Glob pattern used to select which files to process.

    Returns:
        The dict returned by :func:`qc_ctd_data`.
    """
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
    """Handle the log window's "Start" button: collect inputs and run QC.

    Reads the selected data type and review-mode from ``log_ui``,
    prompts for the remaining inputs via :func:`main_select_inputs`,
    and dispatches to :func:`run_qc_thermograph_data` or
    :func:`run_qc_ctd_data`. Logs and returns early if any required
    input is missing.

    Args:
        log_ui: Log window to read the data-type/review-mode selection
            from and log progress to.
    """
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
    """Signal the running QC loop to stop and quit the application.

    Args:
        app_inst: The running ``QApplication`` instance to quit.
    """
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
