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
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from datashop_toolbox import select_metadata_file_and_data_folder
from datashop_toolbox.log_window import LogWindowThermographQC, SafeConsoleFilter
from datashop_toolbox.thermograph import ThermographHeader

# --- create logs folder in project root ---
log_dir = Path.cwd() / "logs"
log_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"datashop_MTR_QC_log_{timestamp}.txt"

ATLANTIC_TZ = pytz.timezone("Canada/Atlantic")
UTC = pytz.UTC
exit_requested = False
# global mtr_logger
mtr_logger = logging.getLogger("thermograph_qc_logger")
mtr_logger.setLevel(logging.INFO)
mtr_logger.propagate = False
# Guard handler addition so re-imports / reloads don't duplicate output
if not mtr_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.addFilter(SafeConsoleFilter())
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    mtr_logger.addHandler(console_handler)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    mtr_logger.addHandler(file_handler)
    mtr_logger.info("Logger file initialized.")

FLAG_LABELS = {
    0: "No QC",
    1: "Correct",
    2: "Inconsistent",
    3: "Doubtful",
    4: "Erroneous",
    5: "Modified",
}


FLAG_COLORS = {
    0: "#808080",
    1: "#02590F",
    2: "#B59410",
    3: "#8B008B",
    4: "#FF0000",
    5: "#00008B",
}


def parse_datetime(date_str, time_str):
    date_formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%b-%d-%y",
        "%B-%d-%y",
        "%d-%b-%y",  # <-- handles 13-Jul-12
        "%d-%B-%y",
    ]
    time_formats = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]
    if pd.isna(date_str) or date_str.strip() == "":
        return pd.NaT

    # Handle missing time
    if pd.isna(time_str) or time_str.strip() == "":
        time_str = "12:00"  # default time

    # Try each date format
    dt_date = None
    for d_fmt in date_formats:
        try:
            dt_date = datetime.strptime(date_str, d_fmt).date()
            break
        except ValueError:
            continue
    if dt_date is None:
        return pd.NaT

    # Try each time format
    dt_time = None
    for t_fmt in time_formats:
        try:
            dt_time = datetime.strptime(time_str, t_fmt).time()
            break
        except ValueError:
            continue
    if dt_time is None:
        dt_time = datetime.strptime("12:00", "%H:%M").time()  # fallback

    # Combine date and time, then format as string
    return f"{dt_date.strftime('%Y-%m-%d')} {dt_time.strftime('%H:%M:%S')}"


def parse_to_utc(dt_str, tz_mode):
    """
    dt_str : string like '13:49 ADT Jul 11/14'
    tz_mode: 'local' or 'UTC'
    """
    if pd.isna(dt_str) or str(dt_str).strip() == "":
        return pd.NaT

    # Remove duplicate timezone tokens like "/ADT"
    dt_str = re.sub(r"/[A-Z]{3}$", "", str(dt_str)).strip()

    try:
        dt = pd.to_datetime(dt_str, errors="coerce")
    except Exception:
        return pd.NaT

    if pd.isna(dt):
        return pd.NaT

    if tz_mode.lower() == "local":
        # Local Atlantic time → UTC
        if dt.tzinfo is None:
            dt = ATLANTIC_TZ.localize(dt)
        return dt.astimezone(UTC)

    else:  # UTC
        if dt.tzinfo is None:
            return UTC.localize(dt)
        return dt.astimezone(UTC)


def validate_bio_metadata(meta: pd.DataFrame) -> bool:
    if meta is None or meta.empty:
        return False

    cols = set(meta.columns)

    # ---- ID or gauge must exist ----
    if not ({"ID", "gauge"} & cols):
        mtr_logger.warning("Metadata invalid: neither 'ID' nor 'gauge' column found.")
        return False

    # ---- deploy & recover must exist ----
    required_time_cols = {"deploy", "recover"}
    if not required_time_cols.issubset(cols):
        mtr_logger.warning(
            "Metadata invalid: 'deploy' and/or 'recover' column missing."
        )
        return False

    # ---- any acceptable timezone column must exist ----
    tz_candidates = {
        "instrument time zone",
        "Instrument Time Zone",
        "time zone",
        "Time zone",
        "Time Zone",
        "timezone",
        "TimeZone",
    }

    if not (tz_candidates & cols):
        mtr_logger.warning("Metadata invalid: no recognized time-zone column found.")
        return False

    return True


def run_qc_thermograph_data(
        input_path: str,
        output_path: str,
        qc_operator: str,
        metadata_file_path: str,
        review_mode: bool,
        batch_name: str,
        wildcard: str
    ) -> dict:
    
    mtr_logger.info(f"Starting QC Thermograph Data task by {qc_operator} on {input_path}")
    task_completion = qc_thermograph_data(
        input_path,
        wildcard,
        output_path,
        qc_operator,
        metadata_file_path,
        review_mode,
        batch_name,
    )
    print(task_completion)
    if task_completion["finished"]:
        mtr_logger.info("QC Thermograph Data task completed successfully.")
        mtr_logger.info("Finished batch successfully (returned to GUI).")
        mtr_logger.info("Please Start QC for new batch.")
    else:
        print("QC Thermograph Data task did not complete.")
        mtr_logger.warning("QC Thermograph Data task did not complete.......")
        mtr_logger.warning("Please check the logs for more details.")
    return task_completion


def prepare_output_folder(
    in_folder_path: str, out_folder_path: str, qc_operator: str
) -> str:
    base_name_input = "Step_1_Create_ODF"
    in_folder_path = str(Path(in_folder_path).resolve())

    base_name_output = "Step_2_Assign_QFlag"
    out_folder_path = str(Path(out_folder_path).resolve())
    out_odf_path = Path(out_folder_path) / base_name_output
    out_odf_path = Path(out_odf_path).resolve()

    if base_name_input.lower() in in_folder_path.lower():
        if (not Path.exists(out_odf_path)) and (out_odf_path != in_folder_path):
            mtr_logger.info(
                "Initial QC Mode: No existing output folder found. Creating new folder, name : Step_2_Assign_QFlag"
            )
            out_odf_path.mkdir(parents=True, exist_ok=False)
            mtr_logger.info(f"Created output folder: {out_odf_path}")
        else:
            mtr_logger.info(
                "Initial QC Mode: Overwriting existing output folder, name : Step_2_Assign_QFlag"
            )
            try:
                shutil.rmtree(out_odf_path)
                out_odf_path.mkdir(parents=True, exist_ok=False)
                mtr_logger.warning(f"Overwriting existing folder: {out_odf_path}")
            except Exception as e:
                print(e)
                out_odf_path.mkdir(parents=True, exist_ok=True)
    else:
        mtr_logger.info(
            "Review QC Mode: Creating new reviewed output folder, name: Step_3_Review_QFlag_with timestamp."
        )
        now_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"Step_3_Review_QFlag_{qc_operator.strip().title()}_{now_timestamp}"
        out_odf_path = Path(f"{out_folder_path}/{new_name}")
        out_odf_path.mkdir(parents=True, exist_ok=False)
        mtr_logger.info(f"Created new reviewed output folder: {out_odf_path}")

    return str(out_odf_path)


def qc_thermograph_data(
    in_folder_path: str,
    wildcard: str,
    out_folder_path: str,
    qc_operator: str,
    metadata_file_path: str,
    review_mode: bool,
    batch_name: str
) -> dict:
    """
    Processes ODF files in `in_folder_path` matching `wildcard`, writes to out_folder_path/Step_2_Quality_Flagging.
    Uses global `exit_requested` to allow user interruption.
    Returns {"finished": bool}
    """

    global exit_requested
    exit_requested = False
    batch_result_container = {"finished": False}
    if review_mode:
        qc_mode_user = 1  # Review QC Mode
    else:
        qc_mode_user = 0  # Initial QC Mode

    cwd = Path.cwd()

    try:
        os.chdir(in_folder_path)
        mtr_logger.info(f"Changed working dir to the input directory: {in_folder_path}")
    except Exception as e:
        mtr_logger.exception(f"Cannot change directory: {e}")
        return batch_result_container

    print(f"wildcard = {wildcard}")
    mtr_files = list(Path.cwd().glob(wildcard))
    print(f"mtr_files = {mtr_files}")

    if not mtr_files:
        mtr_logger.warning("No ODF files found in selected folder.")
        os.chdir(cwd)
        return batch_result_container

    # Prepare output folder
    out_odf_path = prepare_output_folder(in_folder_path, out_folder_path, qc_operator)
    mtr_logger.info("Created a output data folder name, Step_2_Quality_Flagging ")
    mtr_logger.info(f"Path for Step_2_Quality_Flagging: {out_odf_path}")

    os.chdir(cwd)

    # Declared outside the loop so inner functions defined each iteration
    # close over stable (non-loop) names — required to satisfy ruff B023.
    state: dict = {}

    for idx, mtr_file in enumerate(mtr_files, start=1):
        if exit_requested:
            mtr_logger.warning("Exit requested — stopping QC loop.")
            break
        mtr_file_name = mtr_file.name
        mtr_logger.info(f"Reading file {idx} of {len(mtr_files)}: {mtr_file}")
        mtr_logger.info("Please wait...reading ODF file for QC visualization...")

        full_path = str(pathlib.Path(in_folder_path, mtr_file))

        try:
            mtr = ThermographHeader()
            mtr.read_odf(full_path)
        except Exception as e:
            mtr_logger.exception(f"Failed to read ODF {full_path}: {e}")
            continue

        # Extract data frame
        orig_df = mtr.data.data_frame
        orig_df_stored = orig_df.copy()
        orig_df = orig_df.copy()
        orig_df.reset_index(drop=True, inplace=True)
        orig_df = pd.DataFrame(orig_df)

        temp = orig_df["TE90_01"].to_numpy()
        sytm = orig_df["SYTM_01"].str.lower().str.strip("'")

        # ── Discover all parameter→flag column pairs dynamically ──────────
        # Convention: quality flag column name = "Q" + param_col
        # e.g.  TE90_01 → QTE90_01,  DEPH_01 → QDEPH_01,  PRES_01 → QPRES_01
        # We always include TE90_01/QTE90_01 as the primary (Temperature) pair.
        _time_cols = {c for c in orig_df.columns if c.upper().startswith("SYTM")}

        # Build mapping: display_name → (data_col, flag_col)
        param_map = {}  # e.g. {"Temperature": ("TE90_01", "QTE90_01"), "DEPH_01": ("DEPH_01", "QDEPH_01")}
        for col in orig_df.columns:
            if col in _time_cols:
                continue
            # Skip columns that are themselves flag columns (start with Q + digit pattern)
            if col.upper().startswith("Q") and col[1:] in orig_df.columns:
                continue
            # Check column is numeric
            try:
                arr = pd.to_numeric(orig_df[col], errors="coerce")
                if not arr.notna().any():
                    continue
            except Exception:
                continue
            # Derive expected flag column name
            flag_col = "Q" + col
            if flag_col not in orig_df.columns:
                # Create it initialised to 0
                orig_df[flag_col] = np.zeros(len(orig_df), dtype=int)
                mtr_logger.info(f"Created missing flag column {flag_col} for parameter {col}")
            if col == "TE90_01":
                display = "Temperature" 
            elif col == 'PRES_01':
                display = 'Pressure'
            elif col == 'DEPH_01':
                display = 'Depth'
            param_map[display] = (col, flag_col)

        # Primary temperature pair (always first)
        _primary_data_col, _primary_flag_col = param_map.get("Temperature", ("TE90_01", "QTE90_01"))
        qflag = orig_df[_primary_flag_col].to_numpy().astype(int)

        try:
            dt = pd.to_datetime(sytm, format="%d-%b-%Y %H:%M:%S.%f")
        except Exception as e:
            print(e)
            dt = pd.to_datetime(sytm, infer_datetime_format=True, errors="coerce")

        # Build df: one column per parameter value, one qualityflag_* per parameter
        df = pd.DataFrame({"Temperature": temp}, index=dt)
        for display, (data_col, flag_col) in param_map.items():
            if display == "Temperature":
                df["qualityflag_Temperature"] = orig_df[flag_col].to_numpy().astype(int)
            else:
                if display == "Pressure":
                    orig_df[data_col] = (orig_df[data_col] - 101.325) * 0.1
                df[display] = pd.to_numeric(orig_df[data_col], errors="coerce").to_numpy()
                df[f"qualityflag_{display}"] = orig_df[flag_col].to_numpy().astype(int)

        # Extra params for the combo box (everything except Temperature)
        extra_params = {d: (dc, fc) for d, (dc, fc) in param_map.items() if d != "Temperature"}

        # Backwards-compat alias: "qualityflag" always points to the active param's flags.
        # We keep a single "qualityflag" column in df that is a view of the active param.
        # On init that is Temperature.
        df["qualityflag"] = df["qualityflag_Temperature"].copy()

        state["df"] = df  # expose to closures via state to avoid B023
        state["param_map"] = param_map
        state["active_display"] = "Temperature"

        # Extract metadata from ODF headers
        file_name = mtr._file_specification
        file_name = f"{file_name}.ODF"
        if file_name != mtr_file_name:
            mtr_logger.warning(
                f"Filename mismatch: Header '{file_name}' vs Actual '{mtr_file_name}'"
            )
            batch_result_container["finished"] = False
            return batch_result_container
        else:
            mtr_logger.info(f"Filename verified: {mtr_file_name}")

        organization = mtr.cruise_header.organization
        start_datetime = mtr.event_header.start_date_time
        end_datetime = mtr.event_header.end_date_time
        event_num = mtr.event_header.event_number
        if event_num in (None, "", "NA", "NaN"):
            event_num = None
            mtr_logger.warning(f"Event number is invalid for {mtr_file}.")
        if event_num is None:
            # Matches _011_ in filename
            match = re.search(r"_(\d{1,4})_", file_name)
            if match:
                event_num = match.group(1)
                mtr_logger.info(f"Event number extracted from filename: {event_num}")
            else:
                mtr_logger.warning(
                    f"Could not determine event number from header or filename: {file_name}"
                )
        gauge_serial_number = mtr.instrument_header.serial_number
        instrument = mtr.instrument_header.instrument_type
        list_organization = ["DFO BIO", "FSRS"]

        if organization not in list_organization:
            mtr_logger.warning(
                f"Organization '{organization}' not recognized for {mtr_file}."
            )
            break

        # Add metadata from metadata file if provided
        meta = None
        if organization == list_organization[1]:  # FSRS
            if not metadata_file_path or not Path(metadata_file_path).is_file():
                QMessageBox.critical(
                    None,
                    "Missing Metadata File",
                    "❌ FSRS processing requires a valid metadata file.\n\n"
                    "Please select a valid metadata file before continuing.",
                )
                mtr_logger.error(
                    "FSRS selected but metadata_file_path is missing or invalid."
                )
                batch_result_container["finished"] = False
                return batch_result_container

            try:
                meta = mtr.read_metadata(metadata_file_path, organization)
                meta["date"] = meta["date"].astype(str)
                meta["time"] = meta["time"].astype(str)
                meta["time"] = meta["time"].where(
                    meta["time"].notna() & (meta["time"] != ""), "12:00"
                )
                meta["datetime"] = meta.apply(
                    lambda row: parse_datetime(row["date"], row["time"]), axis=1
                )
                mtr_logger.info(
                    f"Metadata successfully loaded for FSRS: {metadata_file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    None,
                    "Metadata Read Error",
                    f"❌ Failed to read metadata file:\n\n{metadata_file_path}\n\n{e}",
                )
                mtr_logger.exception(
                    f"Failed to read metadata from {metadata_file_path}"
                )
                batch_result_container["finished"] = False
                return batch_result_container

        if organization == list_organization[0]:  # DFO BIO
            if metadata_file_path and Path(metadata_file_path).is_file():
                try:
                    meta_tmp = mtr.read_metadata(metadata_file_path, organization)
                    if not validate_bio_metadata(meta_tmp):
                        meta = None
                        mtr_logger.warning(
                            "Metadata file loaded but failed validation; "
                            "proceeding without metadata."
                        )
                    else:
                        meta = meta_tmp
                        tz_col = next(
                            c
                            for c in meta.columns
                            if c.lower().replace(" ", "")
                            in {"instrumenttimezone", "timezone"}
                        )

                        meta["deploy_utc"] = meta.apply(
                            lambda r, _tz=tz_col: parse_to_utc(r["deploy"], r[_tz]), axis=1
                        )

                        meta["recover_utc"] = meta.apply(
                            lambda r, _tz=tz_col: parse_to_utc(r["recover"], r[_tz]), axis=1
                        )
                        mtr_logger.info(
                            f"Metadata loaded and validated (DFO BIO): {metadata_file_path}"
                        )
                except Exception as e:
                    mtr_logger.warning(
                        f"Metadata file provided but could not be read: {metadata_file_path}. "
                        f"Proceeding without metadata. Error: {e}"
                    )
                    meta = None
            else:
                meta = None
                mtr_logger.info(
                    "No metadata file provided; proceeding without metadata assuming organization is DFO BIO."
                )

        # Determine QC start/end from metadata if available
        start_datetime_qc = start_datetime
        end_datetime_qc = end_datetime

        if organization == list_organization[1]:  # FSRS
            meta_subset = meta[meta["gauge"] == int(gauge_serial_number)]
            if not meta_subset.empty:
                if (
                    "datetime" in meta_subset.columns
                    and not meta_subset["datetime"].isna().all()
                ):
                    meta_subset = meta_subset.copy()
                    meta_subset["datetime"] = pd.to_datetime(
                        meta_subset["datetime"], errors="coerce"
                    )
                    meta_subset = meta_subset.dropna(subset=["datetime", "soak_days"])
                    if not meta_subset.empty:
                        idx_start = meta_subset["datetime"].idxmin()
                        start_dt = meta_subset.loc[idx_start, "datetime"]
                        start_soak = meta_subset.loc[idx_start, "soak_days"]
                        start_datetime_qc = start_dt - pd.to_timedelta(
                            start_soak, unit="D"
                        )

                        idx_end = meta_subset["datetime"].idxmax()
                        end_dt = meta_subset.loc[idx_end, "datetime"]
                        # end_soak = meta_subset.loc[idx_end, "soak_days"]
                        end_datetime_qc = (
                            end_dt  # + pd.to_timedelta(end_soak, unit="D")
                        )

                    else:
                        start_datetime_qc = start_datetime
                        end_datetime_qc = end_datetime

                # ---- Case 2: only date column exists ----
                elif (
                    "date" in meta_subset.columns
                    and not meta_subset["date"].isna().all()
                ):
                    meta_subset = meta_subset.copy()
                    meta_subset["date"] = pd.to_datetime(
                        meta_subset["date"], errors="coerce"
                    )
                    meta_subset = meta_subset.dropna(subset=["date", "soak_days"])
                    if not meta_subset.empty:
                        idx_start = meta_subset["date"].idxmin()
                        start_dt = meta_subset.loc[idx_start, "date"]
                        start_soak = meta_subset.loc[idx_start, "soak_days"]
                        start_datetime_qc = start_dt - pd.to_timedelta(
                            start_soak, unit="D"
                        )

                        idx_end = meta_subset["date"].idxmax()
                        end_dt = meta_subset.loc[idx_end, "date"]
                        # end_soak = meta_subset.loc[idx_end, "soak_days"]
                        end_datetime_qc = (
                            end_dt  # + pd.to_timedelta(end_soak, unit="D")
                        )

                    else:
                        start_datetime_qc = start_datetime
                        end_datetime_qc = end_datetime

            else:
                # Empty metadata subset → fallback
                start_datetime_qc = start_datetime
                end_datetime_qc = end_datetime

        if organization == list_organization[0]:  # DFO BIO
            dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.0
            temp_rate = df["Temperature"].diff() / dt_minutes
            temp_rate = temp_rate.replace([np.inf, -np.inf], np.nan)
            temp_diff = df["Temperature"].diff()
            df["temp_rate"] = temp_rate
            df["temp_diff"] = temp_diff

            drop_threshold = -0.2  # °C per sample minute (deployment)
            rise_threshold = 0.2  # °C per sample minute (recovery)
            temp_jump_mag = 2.0  # °C jump per sample interval

            deployment_rate_idx = df.index[temp_rate < drop_threshold]
            deployment_jump_idx = df.index[temp_diff <= -temp_jump_mag]

            deployment_candidates_rate = [
                {
                    "time": t,
                    "type": "rate",
                    "severity": abs(temp_rate.loc[t]),  # °C/min
                    "temp_drop": (
                        abs(temp_diff.loc[t]) if not pd.isna(temp_diff.loc[t]) else 0.0
                    ),
                }
                for t in deployment_rate_idx
            ]

            deployment_candidates_jump = [
                {
                    "time": t,
                    "type": "jump",
                    "severity": abs(temp_diff.loc[t]),  # °C
                    "temp_drop": abs(temp_diff.loc[t]),
                }
                for t in deployment_jump_idx
            ]

            # --- Pick strongest from each ---
            best_rate = max(
                deployment_candidates_rate, key=lambda x: x["severity"], default=None
            )

            best_jump = max(
                deployment_candidates_jump, key=lambda x: x["severity"], default=None
            )

            # --- Decision logic ---
            if best_rate and best_jump:
                # Case 1: same timestamp → strongest evidence
                if best_rate["time"] == best_jump["time"]:
                    start_in_water = best_rate["time"]

                else:
                    # Case 2: different timestamps → choose bigger temperature drop
                    if best_jump["temp_drop"] > best_rate["temp_drop"]:
                        start_in_water = best_jump["time"]
                    elif best_jump["temp_drop"] < best_rate["temp_drop"]:
                        start_in_water = best_rate["time"]
                    else:
                        # Tie-breaker: earlier event
                        start_in_water = min(best_rate["time"], best_jump["time"])

            elif best_rate:
                start_in_water = best_rate["time"]

            elif best_jump:
                start_in_water = best_jump["time"]

            else:
                # Fallback: no signal detected
                start_in_water = df.index[0]

            recovery_rate_idx = df.index[df["temp_rate"] > rise_threshold]
            recovery_jump_idx = df.index[df["temp_diff"] >= temp_jump_mag]

            recovery_candidates_rate = [
                {
                    "time": t,
                    "type": "rate",
                    "severity": abs(df.loc[t, "temp_rate"]),  # °C/min
                    "temp_rise": (
                        abs(df.loc[t, "temp_diff"])
                        if pd.notna(df.loc[t, "temp_diff"])
                        else 0.0
                    ),
                }
                for t in recovery_rate_idx
            ]

            recovery_candidates_jump = [
                {
                    "time": t,
                    "type": "jump",
                    "severity": abs(df.loc[t, "temp_diff"]),  # °C
                    "temp_rise": abs(df.loc[t, "temp_diff"]),
                }
                for t in recovery_jump_idx
            ]

            # --- Pick strongest from each ---
            best_rate = max(
                recovery_candidates_rate, key=lambda x: x["severity"], default=None
            )

            best_jump = max(
                recovery_candidates_jump, key=lambda x: x["severity"], default=None
            )

            # --- Decision logic ---
            if best_rate and best_jump:
                # Case 1: same timestamp → strongest evidence
                if best_rate["time"] == best_jump["time"]:
                    end_in_water = best_rate["time"]

                else:
                    # Case 2: choose larger temperature rise
                    if best_jump["temp_rise"] > best_rate["temp_rise"]:
                        end_in_water = best_jump["time"]
                    elif best_jump["temp_rise"] < best_rate["temp_rise"]:
                        end_in_water = best_rate["time"]
                    else:
                        # Tie-breaker: later event (recovery happens at end)
                        end_in_water = max(best_rate["time"], best_jump["time"])

            elif best_rate:
                end_in_water = best_rate["time"]

            elif best_jump:
                end_in_water = best_jump["time"]

            else:
                # Fallback: no recovery detected
                end_in_water = df.index[-1]

            if end_in_water <= start_in_water:
                start_in_water = df.index[0]
                end_in_water = df.index[-1]

            if meta is None:
                start_datetime_qc = pd.to_datetime(start_in_water)
                end_datetime_qc = pd.to_datetime(end_in_water)
            else:
                meta = meta.copy()
                if "ID" in meta.columns:
                    meta_subset = meta[meta["ID"] == int(gauge_serial_number)]
                    if len(meta_subset) > 1:
                        try:
                            event_num_int = int(event_num)
                        except (TypeError, ValueError):
                            event_num_int = None
                        if (
                            event_num_int is not None
                            and event_num_int in meta_subset.index
                        ):
                            meta_subset = meta_subset.loc[[event_num_int]]
                        else:
                            mtr_logger.warning(
                                f"Multiple metadata entries found for gauge {gauge_serial_number} "
                                "but event number is missing or invalid; using all entries for this gauge."
                            )
                            meta_subset = meta_subset

                else:
                    meta_subset = pd.DataFrame()

                if meta_subset.empty:
                    mtr_logger.warning(
                        f"No metadata found for gauge {gauge_serial_number}; "
                        "falling back to in-water times."
                    )
                    start_datetime_qc = pd.to_datetime(start_in_water, errors="coerce")
                    end_datetime_qc = pd.to_datetime(end_in_water, errors="coerce")
                else:
                    tolerance_start_t = timedelta(minutes=60)
                    tolerance_end_t = timedelta(minutes=60)
                    meta_subset = meta_subset.copy()
                    if (
                        "deploy_utc" in meta_subset.columns
                        and not meta_subset["deploy_utc"].isna().all()
                    ):
                        meta_subset["deploy_utc"] = pd.to_datetime(
                            meta_subset["deploy_utc"], errors="coerce"
                        )
                        start_in_meta = meta_subset["deploy_utc"].min()
                        if start_in_meta.tzinfo is not None:
                            start_in_meta = start_in_meta.tz_convert("UTC").tz_localize(
                                None
                            )

                        start_datetime = pd.to_datetime(start_datetime, errors="coerce")
                        if (start_in_meta - start_datetime) > tolerance_start_t:
                            start_datetime_qc = start_in_water
                        else:
                            start_datetime_qc = start_in_meta
                    else:
                        mtr_logger.warning(
                            "deploy_utc missing or empty in metadata; using in-water start."
                        )
                        start_datetime_qc = pd.to_datetime(
                            start_in_water, errors="coerce"
                        )

                    if (
                        "recover_utc" in meta_subset.columns
                        and not meta_subset["recover_utc"].isna().all()
                    ):
                        meta_subset["recover_utc"] = pd.to_datetime(
                            meta_subset["recover_utc"], errors="coerce"
                        )
                        end_in_meta = meta_subset["recover_utc"].max()
                        if end_in_meta.tzinfo is not None:
                            end_in_meta = end_in_meta.tz_convert("UTC").tz_localize(
                                None
                            )
                        end_datetime = pd.to_datetime(end_datetime, errors="coerce")
                        if (end_datetime - end_in_meta) > tolerance_end_t:
                            end_datetime_qc = end_in_water
                        else:
                            end_datetime_qc = end_in_meta
                    else:
                        mtr_logger.warning(
                            "recover_utc missing or empty in metadata; using in-water end."
                        )
                        end_datetime_qc = pd.to_datetime(end_in_water, errors="coerce")

        mtr_logger.info(
            f"Determined QC window for {mtr_file}: {start_datetime_qc} to {end_datetime_qc}"
        )
        qc_start_ts = pd.to_datetime(start_datetime_qc).timestamp()
        qc_end_ts = pd.to_datetime(end_datetime_qc).timestamp()

        # Determine QC Mode based on existing flags and user selection
        # Check the primary (Temperature) flag column for previous QC
        has_previous_qc = np.any(df["qualityflag_Temperature"] != 0)
        if (not has_previous_qc) and (qc_mode_user == 0):
            qc_mode_ = " QC Mode - Initial\n(No Previous QC Flags)"
            qc_mode_code_ = 0
            block_next_ = 0
        elif (not has_previous_qc) and (qc_mode_user == 1):
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            mtr_logger.warning(
                "QC Mode Mismatch: Review QC Mode selected but no previous QC flags found."
            )
            QMessageBox.warning(
                None,
                "QC Mode Mismatch",
                "⚠️ Invalid QC Mode Selection\n\n"
                "You selected *Review QC Mode*, but no previous QC flags "
                "were found in this file.\n\n"
                "Please run *Initial QC Mode* first before reviewing QC.\n\n"
                "This file will not proceed.",
            )

        elif (has_previous_qc) and (qc_mode_user == 1):
            qc_mode_ = " QC Mode - Review\n(With Previous QC Flags)"
            qc_mode_code_ = 1
            block_next_ = 0
        else:
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            mtr_logger.warning(
                "QC Mode Mismatch: Review QC Mode selected but no previous QC flags found."
            )
            QMessageBox.warning(
                None,
                "QC Mode Mismatch",
                "⚠️ Invalid QC Mode Selection\n\n"
                "You selected *Review QC Mode*, but no previous QC flags "
                "were found in this file.\n\n"
                "Please run *Initial QC Mode* first before reviewing QC.\n\n"
                "This file will not proceed.",
            )

        mtr_logger.info(f"QC Mode for this file {mtr_file}: {qc_mode_}")

        xnums = np.array([pd.Timestamp(t).timestamp() for t in df.index])
        before_qc_mask = df.index < start_datetime_qc
        after_qc_mask = df.index > end_datetime_qc
        if qc_mode_code_ == 0:
            # Apply initial flags to every parameter's flag column
            _all_flag_cols = [f"qualityflag_{d}" for d in param_map]
            for _fc in _all_flag_cols:
                df.loc[df.index < start_datetime_qc, _fc] = 4
                df.loc[df.index > end_datetime_qc, _fc] = 4
                _in_water = (df.index >= start_datetime_qc) & (df.index <= end_datetime_qc)
                df.loc[_in_water & ~df[_fc].isin([4]), _fc] = 1
            # Sync the active alias
            df["qualityflag"] = df["qualityflag_Temperature"].copy()
        else:
            df["qualityflag"] = df["qualityflag_Temperature"].copy()
        colors_initial = [FLAG_COLORS.get(int(f), "#808080") for f in df["qualityflag"]]

        # Reset per-iteration state in-place — keeps the same object reference
        # that the inner functions already close over (ruff B023 safe).
        state.clear()
        state.update({
            "selection_groups": [],
            "applied": False,
            "user_exited": False,
            "current_flag": 4,
            "param_map": param_map,       # display→(data_col, flag_col)
            "active_display": "Temperature",
        })

        # ── Build pyqtgraph QC window ──────────────────────────────────────────
        class LassoItem(pg.GraphicsObject):
            """Overlay that collects a freehand lasso polygon while the user
            holds the left mouse button, then fires ``sigSelected(indices)``."""

            sigSelected = pg.QtCore.Signal(object)  # emits ndarray of int indices

            def __init__(self, plot_item, xs, ys):
                super().__init__()
                self._plot = plot_item
                self._vb = plot_item.getViewBox()
                self._xs = xs   # unix timestamps (data coords)
                self._ys = ys   # temperatures (data coords)
                self._verts_data = []   # lasso path in data coordinates
                self._drawing = False
                self._pen = QPen(QColor("red"), 0)   # width=0 → cosmetic (1px regardless of zoom)
                self._pen.setStyle(Qt.DashLine)
                plot_item.addItem(self)

            # required by GraphicsObject — return the full view rect so we
            # are always asked to paint and never culled by the scene.
            def boundingRect(self):
                return self._vb.viewRect()

            def paint(self, p, *args):
                if len(self._verts_data) < 2:
                    return
                p.setPen(self._pen)
                path = QPainterPath()
                path.moveTo(QPointF(self._verts_data[0][0], self._verts_data[0][1]))
                for x, y in self._verts_data[1:]:
                    path.lineTo(QPointF(x, y))
                p.drawPath(path)

            def _screen_to_data(self, pos):
                """Convert a mouse event position (view-box pixels) to data coordinates."""
                pt = self._vb.mapSceneToView(pos)
                return pt.x(), pt.y()

            def mousePressEvent(self, ev):
                if ev.button() == Qt.LeftButton:
                    self._verts_data = [self._screen_to_data(ev.scenePos())]
                    self._drawing = True
                    self.update()
                    ev.accept()
                else:
                    ev.ignore()

            def mouseMoveEvent(self, ev):
                if self._drawing:
                    self._verts_data.append(self._screen_to_data(ev.scenePos()))
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
                # Clear the drawn lasso
                self._verts_data = []
                self.update()
                if selected:
                    self.sigSelected.emit(np.array(selected, dtype=int))

        class QCWindow(QWidget):
            """Main interactive QC window built on pyqtgraph."""

            closed = pg.QtCore.Signal()

            def __init__(self, _xnums, _df, _qflag, _colors_initial,
                         _qc_start_ts, _qc_end_ts,
                         _start_datetime_qc, _end_datetime_qc,
                         _instrument, _batch_name, _qc_mode_, _qc_mode_code_,
                         _block_next_, _idx, _mtr_files, _mtr_file,
                         _organization, _state, _extra_params):
                super().__init__()
                self._xnums = _xnums
                self._df = _df
                self._qflag = _qflag
                self._state = _state
                self._mtr_file = _mtr_file
                self._block_next_ = _block_next_
                # _extra_params: {display_name: (data_col, flag_col)} for non-Temperature params
                self._extra_params = _extra_params
                self._param_map = _state.get("param_map", {"Temperature": ("TE90_01", "QTE90_01")})
                self._y_col = "Temperature"
                self._flag_col = "qualityflag_Temperature"  # active per-param flag column

                self.setWindowTitle(
                    f"[{_idx}/{len(_mtr_files)}] {_organization} "
                    f"Time Series QC — {_mtr_file}"
                )
                self.resize(1400, 700)

                # ── top-level layout ──────────────────────────────────────
                root = QHBoxLayout(self)

                # ── left panel: plot ────────────────────────────────────────────
                pg.setConfigOption("background", "w")
                pg.setConfigOption("foreground", "k")
                self._pw = pg.PlotWidget()
                self._pw.setLabel("bottom", "Date / Time")
                self._pw.setLabel("left", "Temperature")
                self._pw.showGrid(x=True, y=True, alpha=0.3)
                self._pw.setTitle(
                    f"[{_idx}/{len(_mtr_files)}] {_organization} "
                    f"Time Series Data — {_mtr_file}"
                )

                # Enable mouse pan (right_panel-drag or middle-drag) and wheel zoom
                self._pw.setMouseEnabled(x=True, y=True)
                self._pw.getPlotItem().setMenuEnabled(True)

                # Set to RectMode for left-click drag zooming
                self._pw.getViewBox().setMouseMode(pg.ViewBox.RectMode) 

                # Date-time axis
                axis = pg.DateAxisItem(orientation="bottom")
                self._pw.setAxisItems({"bottom": axis})

                # QC window shading — excluded from auto-range so it doesn't
                # stretch the view to cover the entire epoch range.
                lr = pg.LinearRegionItem(
                    [_qc_start_ts, _qc_end_ts],
                    brush=pg.mkBrush(QColor(173, 216, 230, 60)),
                    movable=False,
                )
                lr.setZValue(-10)
                self._pw.addItem(lr)

                # Vertical deployment / recovery lines — also excluded from auto-range
                vline_start = pg.InfiniteLine(
                    pos=_qc_start_ts, angle=90,
                    pen=pg.mkPen("b", width=2, style=Qt.DashLine),
                    label="Deployment: Start",
                    labelOpts={"color": "purple", "rotateAxis": (1, 0)},
                )
                vline_end = pg.InfiniteLine(
                    pos=_qc_end_ts, angle=90,
                    pen=pg.mkPen("b", width=2, style=Qt.DashLine),
                    label="Recovered: End",
                    labelOpts={"color": "purple", "rotateAxis": (1, 0)},
                )
                self._pw.addItem(vline_start)
                self._pw.addItem(vline_end)

                # Scatter plot
                brushes = [pg.mkBrush(QColor(c)) for c in _colors_initial]
                self._scatter = pg.ScatterPlotItem(
                    x=_xnums,
                    y=_df["Temperature"].to_numpy(),
                    size=8,
                    brush=brushes,
                    pen=pg.mkPen(None),
                )
                self._pw.addItem(self._scatter)
                self._state["scatter"] = self._scatter

                # Fit view tightly to the scatter data, ignoring infinite lines / regions.
                # Add a small margin so points aren't clipped at the edges.
                x_margin = (_xnums.max() - _xnums.min()) * 0.03 or 86400  # fallback 1 day
                temps = _df["Temperature"].to_numpy()
                y_margin = (temps.max() - temps.min()) * 0.05 or 1.0
                self._pw.setXRange(_xnums.min() - x_margin, _xnums.max() + x_margin, padding=0)
                self._pw.setYRange(temps.min() - y_margin, temps.max() + y_margin, padding=0)
                # Disable auto-range so InfiniteLine / LinearRegionItem don't re-expand the view
                self._pw.getPlotItem().enableAutoRange(enable=False)

                # Click-to-select
                self._scatter.sigClicked.connect(self._on_points_clicked)

                # Lasso
                self._lasso = LassoItem(
                    self._pw.getPlotItem(),
                    _xnums,
                    _df["Temperature"].to_numpy(),
                )
                self._lasso.sigSelected.connect(self._on_lasso_select)

                # ── left panel: time series plot ─────────────────────────────
                left_panel = QVBoxLayout()
                root.addLayout(left_panel, stretch=5)
                left_panel.addWidget(self._pw)

                # ── right panel: info and controls ───────────────────────────
                right_panel = QVBoxLayout()
                root.addLayout(right_panel, stretch=1)

                # QC Mode label
                mode_color = "green" if _qc_mode_code_ == 0 else "green"
                mode_lbl = QLabel(f"<b>QC Mode:</b><br>{_qc_mode_}")
                mode_lbl.setStyleSheet(f"color: {mode_color}; font-size: 16px;")
                mode_lbl.setWordWrap(True)
                right_panel.addWidget(mode_lbl)

                # Info block
                info_text = (
                    f"<b>Deployed:</b> {_start_datetime_qc}<br>"
                    f"<b>Recovered:</b> {_end_datetime_qc}<br>"
                    f"<b>Instrument:</b> {_instrument}<br>"
                    f"<b>Batch:</b> {_batch_name}"
                )
                info_lbl = QLabel(info_text)
                info_lbl.setStyleSheet("color: navy; font-size: 16px;")
                info_lbl.setWordWrap(True)
                right_panel.addWidget(info_lbl)

                right_panel.addSpacing(12)

                # Y-axis variable selector (only shown when extra params exist)
                if _extra_params:
                    y_sel_row = QHBoxLayout()
                    y_lbl = QLabel("<b>Y-axis variable:</b>")
                    y_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: navy;")
                    self._y_combo = QComboBox()
                    self._y_combo.setStyleSheet("font-size: 16px;")
                    self._y_combo.addItem("Temperature")
                    for display_name in _extra_params:
                        self._y_combo.addItem(display_name)
                    self._y_combo.currentTextChanged.connect(self._switch_y_axis)
                    y_sel_row.addWidget(y_lbl)
                    y_sel_row.addWidget(self._y_combo)
                    y_sel_row.addStretch()
                    right_panel.addLayout(y_sel_row)

                right_panel.addSpacing(12)

                # Radio buttons for flag selection
                flag_box = QGroupBox("Assign Quality Codes for Selected Points:")
                flag_box.setStyleSheet(
                    "QGroupBox { font-weight: bold; color: navy; font-size: 16px; }"
                )
                flag_layout = QVBoxLayout(flag_box)
                self._flag_group = QButtonGroup(self)
                for k, label in FLAG_LABELS.items():
                    rb = QRadioButton(f"{k}: {label}")
                    color = FLAG_COLORS[k]
                    rb.setStyleSheet(
                        f"color: {color}; font-weight: bold; font-family: serif; font-size: 16px;"
                    )
                    rb.setProperty("flag_value", k)
                    self._flag_group.addButton(rb, k)
                    flag_layout.addWidget(rb)
                    if k == _state["current_flag"]:
                        rb.setChecked(True)
                self._flag_group.idClicked.connect(self._on_flag_selected)
                right_panel.addWidget(flag_box)

                right_panel.addStretch()

                # Store data ranges for Reset View
                self._x_range = (_xnums.min() - x_margin, _xnums.max() + x_margin)
                self._y_range = (temps.min() - y_margin, temps.max() + y_margin)

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

                right_panel.addWidget(self._btn_exit)

                # Snapshot all per-param flag columns at init for undo
                self._qflag_snapshots = {
                    f"qualityflag_{d}": self._df[f"qualityflag_{d}"].to_numpy().copy()
                    for d in self._param_map
                }

                for b in (self._btn_reset, self._btn_undo, self._btn_export,
                        self._btn_continue, self._btn_exit):
                    right_panel.addWidget(b)

                self._btn_reset.clicked.connect(self._click_reset_view)
                self._btn_undo.clicked.connect(self._click_deselect_all)
                self._btn_export.clicked.connect(lambda: self._export_dataframe(self._mtr_file))
                self._btn_continue.clicked.connect(self._click_continue)
                self._btn_exit.clicked.connect(self._click_exit)

            # ── slots ─────────────────────────────────────────────────────

            def _click_reset_view(self):
                self._pw.setXRange(*self._x_range, padding=0)
                self._pw.setYRange(*self._y_range, padding=0)

            def _switch_y_axis(self, col_name):
                """Replot using a different y-axis column and switch the active flag column."""
                self._y_col = col_name
                self._flag_col = f"qualityflag_{col_name}"
                self._state["active_display"] = col_name

                # Sync the qualityflag alias to the newly active param's flags
                self._df["qualityflag"] = self._df[self._flag_col].copy()

                ys = self._current_ys()
                brushes = [
                    pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                    for f in self._df[self._flag_col]
                ]
                self._scatter.setData(
                    x=self._xnums,
                    y=ys,
                    brush=brushes,
                    pen=pg.mkPen(None),
                    size=8,
                )
                self._lasso._ys = ys

                # Refit y range
                valid = ys[~np.isnan(ys.astype(float))]
                if valid.size:
                    y_margin = (valid.max() - valid.min()) * 0.05 or 1.0
                    self._y_range = (valid.min() - y_margin, valid.max() + y_margin)
                    self._pw.setYRange(*self._y_range, padding=0)
                self._pw.setLabel("left", col_name)
                mtr_logger.info(f"Y-axis switched to: {col_name} (flag col: {self._flag_col})")

            def _current_ys(self):
                """Return the y-values for whichever column is currently displayed."""
                if self._y_col == "Temperature":
                    return self._df["Temperature"].to_numpy()
                return self._df[self._y_col].to_numpy() if self._y_col in self._df.columns \
                    else self._df["Temperature"].to_numpy()

            def _on_flag_selected(self, flag_id):
                self._state["current_flag"] = flag_id
                mtr_logger.info(f"Current flag set to {flag_id}")

            def _apply_flags_to_points(self, indices):
                flag = self._state["current_flag"]
                # Write to the active per-param flag column
                self._df.iloc[indices, self._df.columns.get_loc(self._flag_col)] = flag
                # Keep alias in sync
                self._df["qualityflag"] = self._df[self._flag_col].copy()
                brushes = [
                    pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                    for f in self._df[self._flag_col]
                ]
                self._scatter.setBrush(brushes)
                self._state["scatter"] = self._scatter

            def _on_lasso_select(self, indices):
                if indices.size == 0:
                    return
                mtr_logger.info(
                    f"Selected {len(indices)} point(s) via LASSO using "
                    f"current flag: {self._state['current_flag']} on {self._y_col}"
                )
                self._apply_flags_to_points(indices)
                sel_dt = self._df.index[indices]
                sel_vals = self._current_ys()[indices]
                self._state["selection_groups"].append(pd.DataFrame({
                    "DateTime": sel_dt,
                    self._y_col: sel_vals,
                    "idx": indices,
                    "Flag": self._state["current_flag"],
                }))

            def _on_points_clicked(self, _plot, points):
                indices = np.array([p.index() for p in points], dtype=int)
                if indices.size == 0:
                    return
                mtr_logger.info(
                    f"Selected {len(indices)} point(s) via click using "
                    f"current flag: {self._state['current_flag']} on {self._y_col}"
                )
                self._apply_flags_to_points(indices)
                sel_dt = self._df.index[indices]
                sel_vals = self._current_ys()[indices]
                self._state["selection_groups"].append(pd.DataFrame({
                    "DateTime": sel_dt,
                    self._y_col: sel_vals,
                    "idx": indices,
                    "Flag": self._state["current_flag"],
                }))

            def _click_deselect_all(self):
                self._state["selection_groups"].clear()
                mtr_logger.info("Figure: Undo Selection clicked (all selections cleared).")
                # Restore every per-param flag column from the initial snapshot
                for fc, snap in self._qflag_snapshots.items():
                    self._df[fc] = snap.copy()
                # Sync the alias to the currently active param
                self._df["qualityflag"] = self._df[self._flag_col].copy()
                brushes = [
                    pg.mkBrush(QColor(FLAG_COLORS[int(f)]))
                    for f in self._df[self._flag_col]
                ]
                self._scatter.setBrush(brushes)
                self._lasso._ys = self._current_ys()
                self._state["scatter"] = self._scatter
                logging.getLogger("qc_tool").info(
                    "Undo All Selections: restored original flags/colors."
                )

            def _click_continue(self):
                self._state["applied"] = True
                mtr_logger.info("Figure: Continue clicked.")
                self.close()

            def _click_exit(self):
                global exit_requested
                self._state["user_exited"] = True
                exit_requested = True
                mtr_logger.info("Figure: Exit clicked (exit_requested set True).")
                self.close()

            def _export_dataframe(self, _mtr_file):
                self._state["applied"] = True
                export_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Export DataFrame to CSV",
                    f"{Path(Path.name(_mtr_file)).stem}_QC_Export.csv",
                    "CSV Files (*.csv);;All Files (*)",
                )
                if export_path:
                    try:
                        df_export = self._df.copy()
                        df_export.reset_index(inplace=True)
                        df_export.rename(columns={"index": "SEQ_INDEX"}, inplace=True)
                        df_export.to_csv(export_path, index=False)
                        mtr_logger.info(f"DataFrame exported successfully to {export_path}")
                        QMessageBox.information(
                            self,
                            "Export Successful",
                            f"✅ DataFrame exported successfully to:\n{export_path}",
                        )
                    except Exception as e:
                        mtr_logger.error(f"Failed to export DataFrame: {e}")
                        QMessageBox.critical(
                            self, "Export Failed", f"❌ Failed to export DataFrame:\n{e}"
                        )

            def closeEvent(self, ev):
                self.closed.emit()
                super().closeEvent(ev)

        # ── Instantiate and show the window ───────────────────────────────
        qc_win = QCWindow(
            xnums, df, qflag, colors_initial,
            qc_start_ts, qc_end_ts,
            start_datetime_qc, end_datetime_qc,
            instrument, batch_name, qc_mode_, qc_mode_code_,
            block_next_, idx, mtr_files, mtr_file,
            organization, state, extra_params,
        )

        if block_next_ == 1:
            try:
                Path.rmdir(out_odf_path)
            except Exception:
                pass

        qc_win.show()

        # Flush pending paint/resize events so the window actually renders
        # before the busy-wait loop begins.
        app = QApplication.instance()
        if app:
            app.processEvents()
            app.processEvents()  # second pass ensures deferred layouts are resolved

        mtr_logger.info(
            "QC Point Selection Tips:\n"
            "- Use the Lasso tool (click and drag) to select multiple data points.\n"
            "- Single points can also be selected using a mouse click.\n"
            "- Choose the desired quality flag using the radio buttons BEFORE selecting points.\n"
            "- Only select points that appear problematic or questionable.\n"
            "- Focus primarily on flags:\n"
            "    2: Inconsistent\n"
            "    3: Doubtful\n"
            "    4: Erroneous\n"
            "    5: Modified\n"
            "- Points not selected will automatically be assigned flag 1 (Correct) when you click 'Continue Next >>'.\n"
            "- Use 'Undo All Selections' to clear all current selections and start over.\n"
            "- Click 'Continue Next >>' to apply flags and proceed to the next file.\n"
            "- Click 'Exit' to stop the QC process immediately."
        )

        # Wait until the window is closed, processing Qt events so the main GUI stays responsive
        app = QApplication.instance()
        while qc_win.isVisible() and not exit_requested:
            if app:
                app.processEvents()
            time.sleep(0.05)

        # After closing the plot and collecting all selection groups
        if state["applied"]:
            if len(orig_df) != len(df):
                raise ValueError(
                    f"Size mismatch: orig_df has {len(orig_df)} rows, but df has {len(df)} rows."
                )

            if state["selection_groups"]:
                combined_indices = np.unique(
                    np.concatenate([g["idx"].to_numpy() for g in state["selection_groups"]])
                ).astype(int)
            else:
                combined_indices = np.array([], dtype=int)

            mtr_logger.info(
                f"Total of {len(combined_indices)} unique points selected for flagging."
            )

            # Write back flags for every parameter dynamically
            for display, (_data_col, flag_col) in param_map.items():
                df_flag_col = f"qualityflag_{display}"

                if len(combined_indices) == 0:
                    if qc_mode_code_ == 0:
                        orig_df[flag_col] = 1
                        orig_df.loc[before_qc_mask, flag_col] = 4
                        orig_df.loc[after_qc_mask, flag_col] = 4
                    # Review mode + no selections → no change for this param
                else:
                    if qc_mode_code_ == 0:
                        orig_df[flag_col] = 1
                        orig_df.loc[before_qc_mask, flag_col] = 4
                        orig_df.loc[after_qc_mask, flag_col] = 4
                        orig_df.iloc[
                            combined_indices, orig_df.columns.get_loc(flag_col)
                        ] = df.iloc[combined_indices][df_flag_col].to_numpy()
                    elif qc_mode_code_ == 1:
                        orig_df.loc[before_qc_mask, flag_col] = 4
                        orig_df.loc[after_qc_mask, flag_col] = 4
                        orig_df.iloc[
                            combined_indices, orig_df.columns.get_loc(flag_col)
                        ] = df.iloc[combined_indices][df_flag_col].to_numpy()

            if len(combined_indices) == 0 and qc_mode_code_ == 0:
                mtr_logger.info("No points were selected; applied default flags with QC window.")
            elif len(combined_indices) == 0 and qc_mode_code_ == 1:
                mtr_logger.info("No points were selected; no changes made.")
            elif qc_mode_code_ == 0:
                mtr_logger.info(
                    f"Applied {len(combined_indices)} user-selected QC flags with window enforcement."
                )
            else:
                mtr_logger.info("Review QC: updated selected points and enforced QC window.")

        # Log flag changes for all parameters
        orig_df_after_qc = orig_df.copy()
        total_changed = 0
        for display, (_data_col, flag_col) in param_map.items():
            if flag_col not in orig_df_stored.columns:
                continue
            after_flags = orig_df_after_qc[flag_col].to_numpy().astype(int)
            before_flags = orig_df_stored[flag_col].to_numpy().astype(int)
            changed_mask = before_flags != after_flags
            n_changed = changed_mask.sum()
            total_changed += n_changed
            if n_changed > 0:
                mtr_logger.info(f"  [{display} / {flag_col}] {n_changed} flag(s) changed:")
                transitions = Counter(zip(before_flags[changed_mask], after_flags[changed_mask], strict=True))
                for (before, after), count in transitions.items():
                    mtr_logger.info(f"    Flag {before} → {after}: {count}")
            else:
                mtr_logger.info(f"  [{display} / {flag_col}] No changes.")

        if total_changed == 0:
            mtr_logger.info(f"No quality flag changes were made for {mtr_file}")
        else:
            mtr_logger.info(f"Total QC flags changed across all parameters for {mtr_file}: {total_changed}")

        try:
            mtr.data.data_frame = orig_df
            mtr.add_history()
            if qc_mode_code_ == 0:
                mtr.add_to_history(
                    f"APPLIED QUALITY CODE FLAGGING AND PERFORMED INITIAL VISUAL QC BY {qc_operator.upper()}"
                )
            elif qc_mode_code_ == 1:
                mtr.add_to_history(
                    f"REVIEWED AND UPDATED QUALITY CODE FLAGGING BY {qc_operator.upper()}"
                )
            mtr.update_odf()
            file_spec = mtr.generate_file_spec()
            event_num = getattr(mtr.event_header, "event_number", None)

            if "__" in file_spec or event_num is None:
                # Extract a 0 to 4-digit number between underscores in the filename
                fname = file_name  # remove .ODF
                match = re.search(r"_(\d{1,4})_", fname)
                if match:
                    event_num = match.group(1).zfill(
                        3
                    )  # pad with leading zeros if needed
                    # Insert event number into file_spec if missing
                    file_spec_parts = file_spec.split("__")
                    if len(file_spec_parts) == 2:
                        file_spec = (
                            f"{file_spec_parts[0]}_{event_num}_{file_spec_parts[1]}"
                        )
                    else:
                        # fallback: just append event_num if double underscore not found
                        file_spec = f"{file_spec.replace('.ODF', '')}_{event_num}.ODF"
                else:
                    raise ValueError(
                        f"Could not determine event number from filename: {mtr_file}"
                    )

            mtr.file_specification = file_spec
            mtr_logger.info(f"Writing file {idx} of {len(mtr_files)}: {mtr_file}")
            mtr_logger.info("Please wait...writing QC ODF file...")
            out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
            mtr.write_odf(str(out_file), version=2.0)
            mtr_logger.info(f"QC completed for [{idx}/{len(mtr_files)}]: {mtr_file}")
            mtr_logger.info(f"Saved [{idx}/{len(mtr_files)}]: {out_file}")
        except Exception as e:
            mtr_logger.exception(f"Failed writing QC ODF for {mtr_file}: {e}")

    # Completed loop
    if not exit_requested and (idx == len(mtr_files)):
        mtr_logger.info(f"QC process completed for all {len(mtr_files)} files.")
        batch_result_container["finished"] = True
    elif exit_requested:
        mtr_logger.info(
            f"QC process was interrupted before completion ({idx} of {len(mtr_files)} files)"
        )
        batch_result_container["finished"] = False
    else:
        # fallback
        batch_result_container["finished"] = False

    return batch_result_container


def main_select_inputs(review_mode: bool):
    app = QApplication.instance()
    must_quit_app = app is None
    if must_quit_app:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    select_inputs = select_metadata_file_and_data_folder.SubWindowOne(
        review_mode=review_mode
    )
    select_inputs.show()

    result_container = {
        "finished": False,
        "input": None,
        "output": None,
        "operator": None,
        "metadata": None,
        "batch": None,
        "wildcard": None
    }

    def on_accept():
        operator = select_inputs.line_edit_text.strip()
        metadata_file_path = select_inputs.metadata_file
        input_path = select_inputs.input_data_folder
        output_path = select_inputs.output_data_folder
        batch_name = select_inputs.generate_batch
        wildcard = select_inputs.wildcard_string

        if not operator or not input_path or not output_path:
            print("❌ Missing required fields.")
            return

        result_container["operator"] = operator
        result_container["metadata"] = metadata_file_path
        result_container["input"] = input_path
        result_container["output"] = output_path
        result_container["finished"] = True
        result_container["batch"] = batch_name
        result_container["wildcard"] = wildcard
        select_inputs.close()

    def on_reject():
        print("❌ QC cancelled by user.")
        result_container["finished"] = False
        select_inputs.close()

    select_inputs.buttonBox.accepted.connect(on_accept)
    select_inputs.buttonBox.rejected.connect(on_reject)

    while select_inputs.isVisible():
        app.processEvents()
        time.sleep(0.05)

    if must_quit_app:
        pass

    if result_container["finished"]:
        return (
            result_container["input"],
            result_container["output"],
            result_container["operator"],
            result_container["metadata"],
            result_container["batch"],
            result_container["wildcard"]
        )
    else:
        return None, None, None, None, None


def exit_program(app):
    """
    Clean exit.
    """
    global exit_requested
    global mtr_logger
    exit_requested = True
    mtr_logger.info("Exit Program clicked — setting exit_requested and quitting.")
    # Allow mtr_logger to flush
    handlers = mtr_logger.handlers[:]
    for h in handlers:
        try:
            h.flush()
        except Exception:
            pass
    app.quit()


def start_qc_process(log_ui: LogWindowThermographQC, review_mode: bool):
    """
    Called when Start QC button is clicked.
    It opens the metadata/input selection dialog, and if accepted, runs the QC workflow.
    """
    global exit_requested
    exit_requested = False
    mtr_logger.info("Start QC button clicked.")

    review_mode = log_ui.radio_opt.isChecked()
    if review_mode:
        mtr_logger.info("Review QC Mode selected.")
    else:
        mtr_logger.info("Initial QC Mode selected.")

    input_path, output_path, operator, metadata_file_path, batch_name, wildcard = (
        main_select_inputs(review_mode)
    )
    if not input_path or not output_path or not operator:
        mtr_logger.info("QC start aborted: missing input, output, or operator.")
        return
    mtr_logger.info(
        "QC Inputs Selected:\n"
        f"  • QC Operator : {operator.strip().title()}\n"
        f"  • Input Path  : {input_path}\n"
        f"  • Output Path : {output_path}\n"
        f"  • Metadata    : {metadata_file_path}\n"
        f"  • BatchName   : {batch_name}\n"
        f"  • Wildcard    : {wildcard}\n"
    )
    run_qc_thermograph_data(input_path, output_path, operator, metadata_file_path, review_mode, batch_name, wildcard)


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    log_window = LogWindowThermographQC()
    log_window.show()
    if log_window.qtext_handler not in mtr_logger.handlers:
        mtr_logger.addHandler(log_window.qtext_handler)
    mtr_logger.info("Log window initialized.")
    log_window.radio_opt.toggled.connect(
        lambda checked: mtr_logger.info(
            f"The 'Enable As QC Reviewer Mode' radio button is {'checked' if checked else 'unchecked'}"
        )
    )

    # Connect buttons
    # log_window.btn_start.clicked.connect(lambda: start_qc_process(log_window))
    log_window.btn_start.clicked.connect(
        lambda: start_qc_process(log_window, log_window.radio_opt.isChecked())
    )
    log_window.btn_exit.clicked.connect(lambda: exit_program(app))
    mtr_logger.info("Application started. Use Start QC to begin.")

    # Start the Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
