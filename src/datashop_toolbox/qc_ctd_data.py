"""
qc_ctd_data.py

Entry point for CTD quality control using the PyQtGraph QCWindow.

CTD QC DOES NOT use metadata files.
Only ODF input/output folders, wildcard, and QC operator are required.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QApplication, QMessageBox

from datashop_toolbox.gui.qc_window import QCWindow
from datashop_toolbox.log_window import LogWindowCTDQC, SafeConsoleFilter
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.select_metadata_file_and_data_folder import SubWindowOne

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

log_dir = Path.cwd() / "logs"
log_dir.mkdir(exist_ok=True)

log_file = log_dir / "datashop_CTD_QC.log"

ctd_logger = logging.getLogger("CTD_qc_logger")
ctd_logger.setLevel(logging.INFO)
ctd_logger.propagate = False

if not ctd_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.addFilter(SafeConsoleFilter())
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    ctd_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    ctd_logger.addHandler(file_handler)

ctd_logger.info("CTD QC logger initialized.")

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_ctd_casts(
    input_dir: Path,
    wildcard: str,
) -> tuple[dict[str, pd.DataFrame], dict[str, OdfHeader]]:
    """
    Load CTD ODF files into cast DataFrames and per-cast OdfHeaders.
    """
    casts: dict[str, pd.DataFrame] = {}
    odf_headers: dict[str, OdfHeader] = {}

    odf_files = sorted(input_dir.glob(wildcard))
    if not odf_files:
        raise FileNotFoundError(f"No files match pattern: {wildcard}")

    for odf_file in odf_files:
        ctd_logger.info(f"Loading ODF: {odf_file.name}")

        header = OdfHeader.from_file(odf_file)
        df = header.to_dataframe()

        # Normalize pressure column
        if "PRES" not in df.columns:
            for alt in ("PRESSURE", "DEPTH"):
                if alt in df.columns:
                    df = df.rename(columns={alt: "PRES"})
                    break

        cast_id = odf_file.stem
        casts[cast_id] = df
        odf_headers[cast_id] = header

    return casts, odf_headers

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

    log_window = LogWindowCTDQC()
    log_window.show()

    try:
        # NOTE: Metadata file selection is ignored for CTD QC
        selector = SubWindowOne(review_mode=False)
        selector.show()
        app.exec()

        if selector.result != "accept":
            ctd_logger.info("User cancelled CTD QC input selection.")
            return

        input_dir = Path(selector.input_data_folder)
        output_dir = Path(selector.output_data_folder)
        wildcard = selector.wildcard_string or "*.ODF"
        qc_operator = selector.line_edit_text
        batch_name = selector.generate_batch

        casts, odf_headers = load_ctd_casts(input_dir, wildcard)

        ctd_logger.info(f"Loaded {len(casts)} CTD casts.")

        qc_window = QCWindow(
            casts=casts,
            odf_headers=odf_headers,
            qc_operator=qc_operator,
            batch_name=batch_name,
            output_dir=output_dir,
            logger=ctd_logger,
        )

        qc_window.show()
        app.exec()

    except Exception as exc:
        ctd_logger.exception("Fatal error during CTD QC.")
        QMessageBox.critical(
            None,
            "CTD QC Error",
            f"An error occurred:\n\n{exc}",
        )

if __name__ == "__main__":
    main()
