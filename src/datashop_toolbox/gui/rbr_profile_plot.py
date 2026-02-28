# ========= Profile Plot Dialog — One-at-a-time, Prev/Next only =========
import sys

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .ui_rsk_plot_dialog import Ui_plot_dialog


class PlotDialog(QDialog):
    """
    Dialog that displays RSK profile figures one at a time with Next/Prev navigation
    and keyboard left/right support. No jump wheel/spinbox; no up/down arrows.
    """

    def __init__(self, fig_handles: list | None = None, parent=None, title: str = "RSK Profiles"):
        super().__init__(parent)
        self.ui = Ui_plot_dialog()
        self.ui.setupUi(self)

        # Window flags & initial size
        self.setWindowFlag(Qt.WindowTitleHint, True)
        self.setWindowFlag(Qt.WindowSystemMenuHint, True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.resize(1600, 800)
        self.setWindowTitle(title)

        # Data
        self.fig_handles: list = fig_handles if fig_handles else []
        self.current_profile_index: int = 0
        self.saved_profiles = set()

        # Replace the QGraphicsView with a real container for toolbar + canvas
        parent_layout = self.ui.verticalLayout_2
        parent_layout.removeWidget(self.ui.profile_graphics_view)
        self.ui.profile_graphics_view.deleteLater()

        self.plotContainer = QWidget(self)
        self.plotLayout = QVBoxLayout(self.plotContainer)
        self.plotLayout.setContentsMargins(0, 0, 0, 0)
        self.plotLayout.setSpacing(2)
        self.plotContainer.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        parent_layout.insertWidget(0, self.plotContainer)

        # Placeholders
        self.canvas: FigureCanvas | None = None
        self.toolbar: NavigationToolbar | None = None
        self._prev_action: QAction | None = None
        self._next_action: QAction | None = None

        # Wire footer buttons
        self.ui.dialog_button_box.accepted.connect(self.on_accept)
        self.ui.dialog_button_box.rejected.connect(self.on_reject)
        self.ui.save_profile_check_box.stateChanged.connect(self.on_save_checkbox_changed)

        # Show first figure if any
        if self.fig_handles:
            self.display_current_profile()

    # ---------- Toolbar helpers ----------
    def _add_navigation_actions(self):
        """Add only Prev/Next actions (no jump, no up/down arrows)."""
        style = self.style()
        prev_icon = style.standardIcon(QStyle.SP_ArrowBack)
        next_icon = style.standardIcon(QStyle.SP_ArrowForward)

        self._prev_action = QAction(prev_icon, "Previous profile (←)", self)
        self._prev_action.setShortcut("Left")
        self._prev_action.triggered.connect(self.on_prev_profile)

        self._next_action = QAction(next_icon, "Next profile (→)", self)
        self._next_action.setShortcut("Right")
        self._next_action.triggered.connect(self.on_next_profile)

        self.toolbar.addAction(self._prev_action)
        self.toolbar.addAction(self._next_action)
        self.toolbar.addSeparator()

        self._update_nav_enabled()

    def _update_nav_enabled(self):
        total = len(self.fig_handles)
        at_first = self.current_profile_index <= 0
        at_last = self.current_profile_index >= (total - 1)
        if self._prev_action:
            self._prev_action.setEnabled(not at_first)
        if self._next_action:
            self._next_action.setEnabled(not at_last)

    # ---------- Display one profile ----------
    def _clear_plot_area(self):
        while self.plotLayout.count():
            item = self.plotLayout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.canvas = None
        self.toolbar = None
        self._prev_action = None
        self._next_action = None

    def display_current_profile(self):
        """Display the current profile figure in the dialog."""
        if not self.fig_handles or self.current_profile_index >= len(self.fig_handles):
            return

        profile = self.fig_handles[self.current_profile_index]
        figure = profile[0] if isinstance(profile, tuple) else profile

        # Clear previous widgets
        self._clear_plot_area()

        # Create canvas and toolbar for this figure
        self.canvas = FigureCanvas(figure)
        self.canvas.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))

        # Add Prev/Next actions
        self._add_navigation_actions()

        # Add to layout
        self.plotLayout.addWidget(self.toolbar)
        self.plotLayout.addWidget(self.canvas)

        # Draw
        self.canvas.draw()

        # Update checkbox state and title
        self.ui.save_profile_check_box.setChecked(self.current_profile_index in self.saved_profiles)
        total = len(self.fig_handles)
        self.setWindowTitle(f"RSK Profiles — Profile {self.current_profile_index + 1} of {total}")

        # Keyboard: left/right arrows to navigate
        self._connect_key_navigation(figure)

    def _connect_key_navigation(self, figure):
        def on_key(event):
            if event.key == "left":
                self.on_prev_profile()
            elif event.key == "right":
                self.on_next_profile()

        figure.canvas.mpl_connect("key_press_event", on_key)

    # ---------- Handlers ----------
    def on_prev_profile(self):
        if self.current_profile_index > 0:
            self.current_profile_index -= 1
            self.display_current_profile()

    def on_next_profile(self):
        if self.current_profile_index < len(self.fig_handles) - 1:
            self.current_profile_index += 1
            self.display_current_profile()

    def on_save_checkbox_changed(self, state):
        if state == Qt.CheckState.Checked.value:
            self.saved_profiles.add(self.current_profile_index)
        else:
            self.saved_profiles.discard(self.current_profile_index)

    def on_accept(self):
        self.accept()

    def on_reject(self):
        self.reject()

    # ---------- API ----------
    def get_saved_profiles(self):
        return sorted(list(self.saved_profiles))


# ----------------------- Local test harness -----------------------
def _create_sample_profiles(num_profiles=5):
    import numpy as np

    profiles = []
    for i in range(num_profiles):
        x = np.linspace(0, 2 * np.pi, 500)
        y1 = np.sin(x + i * 0.5)
        y2 = np.cos(x + i * 0.5)
        fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
        ax.plot(x, y1, label=f"sin(x+{i * 0.5:.1f})", linewidth=2)
        ax.plot(x, y2, label=f"cos(x+{i * 0.5:.1f})", linewidth=2)
        ax.set_title(f"RSK Profile {i + 1}")
        ax.set_xlabel("x")
        ax.set_ylabel("Amplitude")
        ax.grid(True, alpha=0.3)
        ax.legend()
        profiles.append(fig)
    return profiles


def main():
    """Quick manual test: run this file directly."""
    app = QApplication.instance() or QApplication(sys.argv)
    profiles = _create_sample_profiles(6)
    dlg = PlotDialog(profiles, title="RSK Profiles — Test")
    dlg.exec()
    print("Saved profile indices:", dlg.get_saved_profiles())
    app.exit()


if __name__ == "__main__":
    main()
