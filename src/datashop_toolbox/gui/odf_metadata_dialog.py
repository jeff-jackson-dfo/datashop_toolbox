# odf_header_dialog.py
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from .odf_metadata_form import OdfMetadataForm


class OdfMetadataDialog(QDialog):
    """Modal dialog that wraps :class:`OdfMetadataForm` for editing ODF metadata.

    Attributes:
        form: The embedded :class:`OdfMetadataForm` widget.
    """

    def __init__(self, parent=None):
        """Build the dialog and wire up the embedded form's signals.

        Args:
            parent: Optional parent widget.
        """
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

        self._odf = None

        # Bridge form signals to dialog result
        self.form.submitted.connect(self._on_submitted)
        self.form.cancelled.connect(self.reject)

        # Sizing (tune as desired)
        self.setMinimumSize(800, 500)
        self.resize(1100, 800)

    def _on_submitted(self, odf):
        """Store the submitted ODF object and accept the dialog.

        Args:
            odf: The ODF object produced by the embedded form.
        """
        # Write/export using the form method (or your own)
        self._odf = odf
        self.accept()

    def odf(self):
        """Return the ODF object captured on OK (or None if cancelled)."""
        return self._odf

def main():
    app = QApplication(sys.argv)
    dlg = OdfMetadataDialog()
    if dlg.exec():
        print("Dialog accepted")
    else:
        print("Dialog cancelled")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
