# odf_header_dialog.py
import sys

from odf_metadata_form import OdfMetadataForm
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog


class OdfMetadataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ODF Metadata Editor (Dialog)")

        # ✅ Enable minimize & maximize buttons
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )

        self.form = OdfMetadataForm(self)

        self.form.setMinimumHeight(1200)  # Viewport ~800px; pick any value > viewport

        # --- Debug: confirm the buttons exist and are visible/layouted
        btn_ok = getattr(self.form.ui, "ok_push_button", None)
        btn_cancel = getattr(self.form.ui, "cancel_push_button", None)
        for name, w in (("OK", btn_ok), ("Cancel", btn_cancel)):
            if w is None:
                print(f"{name} button object not found on form.ui")
            else:
                print(
                    f"{name}: visible={w.isVisible()} hidden={w.isHidden()} "
                    f"enabled={w.isEnabled()} geometry={w.geometry()} "
                    f"in_layout={w.parentWidget().__class__.__name__ if w.parentWidget() else 'None'}"
                )

        self._odf = None

        # Bridge form signals to dialog result
        self.form.submitted.connect(self._on_submitted)
        self.form.cancelled.connect(self.reject)

        # Sizing (tune as desired)
        self.setMinimumSize(800, 500)
        self.resize(1100, 800)

    def _on_submitted(self, odf):
        # Write/export using the form method (or your own)
        self._odf = odf
        self.accept()

    def odf(self):
        """Return the ODF object captured on OK (or None if cancelled)."""
        return self._odf


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = OdfMetadataDialog()
    if dlg.exec():
        print("Dialog accepted")
    else:
        print("Dialog cancelled")
    sys.exit(app.exec())
