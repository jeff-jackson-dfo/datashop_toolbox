"""
UI subpackage for datashop_toolbox.

IMPORTANT DESIGN NOTES
----------------------
- This package must remain safe to import without triggering
  heavy workflows or third-party side effects.
- Application entry points (main windows, plotting workflows)
  are imported explicitly where needed, NOT here.
"""

# ---- Lightweight dialogs (SAFE) ----
from .odf_metadata_dialog import OdfMetadataDialog
from .odf_metadata_form import OdfMetadataForm
from .qc_window import Ui_QCWindow as QCWindow

# ---- Qt Designer generated UI classes (SAFE) ----
from .ui_odf_metadata_form import Ui_odf_metadata_form
from .ui_rbr_to_odf import Ui_main_window
from .ui_rsk_plot_dialog import Ui_plot_dialog
from .ui_thermograph_main_window import Ui_thermograph_main_window

# ---- Public GUI API ----
__all__ = [
    # Dialogs
    "OdfMetadataDialog",
    "OdfMetadataForm",

    # Qt UI classes
    "Ui_main_window",
    "Ui_odf_metadata_form",
    "Ui_plot_dialog",
    "Ui_thermograph_main_window",
]
