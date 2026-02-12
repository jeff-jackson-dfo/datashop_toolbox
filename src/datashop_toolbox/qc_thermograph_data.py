import logging
import os
import pathlib
import re
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timedelta

import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz
from matplotlib.patches import Rectangle
from matplotlib.path import Path
from matplotlib.widgets import Button, CheckButtons, RadioButtons
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from datashop_toolbox import select_metadata_file_and_data_folder
from datashop_toolbox.log_window import LogWindowThermographQC, SafeConsoleFilter
from datashop_toolbox.thermograph import ThermographHeader

ATLANTIC_TZ = pytz.timezone("Canada/Atlantic")
UTC = pytz.UTC
exit_requested = False
global logger
logger = logging.getLogger("thermograph_qc_logger")
logger.setLevel(logging.INFO)
logger.propagate = False
console_handler = logging.StreamHandler()
console_handler.addFilter(SafeConsoleFilter())
console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(console_handler)
file_handler = logging.FileHandler("datashop_MTR_QC_log.txt", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)
logger.info("Logger file initialized.")

FLAG_LABELS = {
    0: "Not been QC'd",
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
        logger.warning("Metadata invalid: neither 'ID' nor 'gauge' column found.")
        return False

    # ---- deploy & recover must exist ----
    required_time_cols = {"deploy", "recover"}
    if not required_time_cols.issubset(cols):
        logger.warning("Metadata invalid: 'deploy' and/or 'recover' column missing.")
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
        logger.warning("Metadata invalid: no recognized time-zone column found.")
        return False

    return True


def run_qc_thermograph_data(
    input_path, output_path, qc_operator, metadata_file_path, review_mode: bool, batch_name
) -> dict:
    logger.info(f"Starting QC Thermograph Data task by {qc_operator} on {input_path}")
    wildcard = "*.ODF"
    task_completion = qc_thermograph_data(
        input_path, wildcard, output_path, qc_operator, metadata_file_path, review_mode, batch_name
    )
    print(task_completion)
    if task_completion["finished"]:
        logger.info("QC Thermograph Data task completed successfully.")
        logger.info("Finished batch successfully (returned to GUI).")
        logger.info("Please Start QC for new batch.")
    else:
        print("QC Thermograph Data task did not complete.")
        logger.warning("QC Thermograph Data task did not complete.......")
        logger.warning("Please check the logs for more details.")
    return task_completion


def prepare_output_folder(in_folder_path: str, out_folder_path: str, qc_operator: str) -> str:
    base_name_input = "Step_1_Create_ODF"
    in_folder_path = Path(in_folder_path).resolve()

    base_name_output = "Step_2_Assign_QFlag"
    out_folder_path = Path(out_folder_path).resolve()
    out_odf_path = Path(out_folder_path / base_name_output)
    out_odf_path = Path(out_odf_path).resolve()

    if base_name_input.lower() in in_folder_path.lower():
        if (not Path.exists(out_odf_path)) and (out_odf_path != in_folder_path):
            logger.info(
                "Initial QC Mode: No existing output folder found. Creating new folder, name : Step_2_Assign_QFlag"
            )
            Path.mkdir(out_odf_path, parent=True)
            logger.info(f"Created output folder: {out_odf_path}")
        else:
            logger.info(
                "Initial QC Mode: Overwriting existing output folder, name : Step_2_Assign_QFlag"
            )
            shutil.rmtree(out_odf_path)
            Path.mkdir(out_odf_path, parent=True)
            logger.warning(f"Overwriting existing folder: {out_odf_path}")
    else:
        logger.info(
            "Review QC Mode: Creating new reviewed output folder, name: Step_3_Review_QFlag_with timestamp."
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"Step_3_Review_QFlag_{qc_operator.strip().title()}_{timestamp}"
        out_odf_path = Path(out_folder_path / new_name)
        Path.mkdir(out_odf_path, parent=True)
        logger.info(f"Created new reviewed output folder: {out_odf_path}")

    return out_odf_path


def qc_thermograph_data(
    in_folder_path: str,
    wildcard: str,
    out_folder_path: str,
    qc_operator: str,
    metadata_file_path: str,
    review_mode: bool,
    batch_name: str,
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
        logger.info(f"Changed working dir to the input directory: {in_folder_path}")
    except Exception as e:
        logger.exception(f"Cannot change directory: {e}")
        return batch_result_container

    mtr_files = Path.glob(wildcard)
    if not mtr_files:
        logger.warning("No ODF files found in selected folder.")
        os.chdir(cwd)
        return batch_result_container

    # Prepare output folder
    out_odf_path = prepare_output_folder(in_folder_path, out_folder_path, qc_operator)
    logger.info("Created a output data folder name, Step_2_Quality_Flagging ")
    logger.info(f"Path for Step_2_Quality_Flagging: {out_odf_path}")

    os.chdir(cwd)

    for idx, mtr_file in enumerate(mtr_files, start=1):
        if exit_requested:
            logger.warning("Exit requested — stopping QC loop.")
            break

        logger.info(f"Reading file {idx} of {len(mtr_files)}: {mtr_file}")
        logger.info("Please wait...reading ODF file for QC visualization...")

        full_path = str(pathlib.Path(in_folder_path, mtr_file))

        try:
            mtr = ThermographHeader()
            mtr.read_odf(full_path)
        except Exception as e:
            logger.exception(f"Failed to read ODF {full_path}: {e}")
            continue

        # Extract data frame
        orig_df = mtr.data.data_frame
        orig_df_stored = orig_df.copy()
        orig_df = orig_df.copy()
        orig_df.reset_index(drop=True, inplace=True)
        orig_df = pd.DataFrame(orig_df)

        temp = orig_df["TE90_01"].to_numpy()
        sytm = orig_df["SYTM_01"].str.lower().str.strip("'")

        if "QTE90_01" in orig_df.columns:
            qflag = orig_df["QTE90_01"].to_numpy().astype(int)
        else:
            orig_df["QTE90_01"] = np.zeros(len(orig_df), dtype=int)
            qflag = orig_df["QTE90_01"].to_numpy().astype(int)

        try:
            dt = pd.to_datetime(sytm, format="%d-%b-%Y %H:%M:%S.%f")
        except Exception:
            dt = pd.to_datetime(sytm, infer_datetime_format=True, errors="coerce")

        # Create a DataFrame with Temperature as the variable and DateTime as the index.
        df = pd.DataFrame({"Temperature": temp, "qualityflag": qflag}, index=dt)
        number_of_rows = len(df)

        # Extract metadata from ODF headers
        file_name = mtr._file_specification
        file_name = f"{file_name}.ODF"
        if file_name != mtr_file:
            logger.warning(f"Filename mismatch: Header '{file_name}' vs Actual '{mtr_file}'")
            batch_result_container["finished"] = False
            return batch_result_container
        else:
            logger.info(f"Filename verified: {mtr_file}")

        organization = mtr.cruise_header.organization
        start_datetime = mtr.event_header.start_date_time
        end_datetime = mtr.event_header.end_date_time
        event_num = mtr.event_header.event_number
        if event_num in (None, "", "NA", "NaN"):
            event_num = None
            logger.warning(f"Event number is invalid for {mtr_file}.")
        if event_num is None:
            # Matches _011_ in filename
            match = re.search(r"_(\d{1,4})_", file_name)
            if match:
                event_num = match.group(1)
                logger.info(f"Event number extracted from filename: {event_num}")
            else:
                logger.warning(
                    f"Could not determine event number from header or filename: {file_name}"
                )
        gauge_serial_number = mtr.instrument_header.serial_number
        instrument = mtr.instrument_header.instrument_type
        list_organization = ["DFO BIO", "FSRS"]

        if organization not in list_organization:
            logger.warning(f"Organization '{organization}' not recognized for {mtr_file}.")
            break

        # Add metadata from metadata file if provided
        meta = None
        if organization == list_organization[1]:  # FSRS
            if not metadata_file_path or not Path.is_file(metadata_file_path):
                QMessageBox.critical(
                    None,
                    "Missing Metadata File",
                    "❌ FSRS processing requires a valid metadata file.\n\n"
                    "Please select a valid metadata file before continuing.",
                )
                logger.error("FSRS selected but metadata_file_path is missing or invalid.")
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
                logger.info(f"Metadata successfully loaded for FSRS: {metadata_file_path}")
            except Exception as e:
                QMessageBox.critical(
                    None,
                    "Metadata Read Error",
                    f"❌ Failed to read metadata file:\n\n{metadata_file_path}\n\n{e}",
                )
                logger.exception(f"Failed to read metadata from {metadata_file_path}")
                batch_result_container["finished"] = False
                return batch_result_container

        if organization == list_organization[0]:  # DFO BIO
            if metadata_file_path and Path.is_file(metadata_file_path):
                try:
                    meta_tmp = mtr.read_metadata(metadata_file_path, organization)
                    if not validate_bio_metadata(meta_tmp):
                        meta = None
                        logger.warning(
                            "Metadata file loaded but failed validation; "
                            "proceeding without metadata."
                        )
                    else:
                        meta = meta_tmp
                        tz_col = next(
                            c
                            for c in meta.columns
                            if c.lower().replace(" ", "") in {"instrumenttimezone", "timezone"}
                        )

                        meta["deploy_utc"] = meta.apply(
                            lambda r: parse_to_utc(r["deploy"], r[tz_col]), axis=1
                        )

                        meta["recover_utc"] = meta.apply(
                            lambda r: parse_to_utc(r["recover"], r[tz_col]), axis=1
                        )
                        logger.info(
                            f"Metadata loaded and validated (DFO BIO): {metadata_file_path}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Metadata file provided but could not be read: {metadata_file_path}. "
                        f"Proceeding without metadata. Error: {e}"
                    )
                    meta = None
            else:
                meta = None
                logger.info(
                    "No metadata file provided; proceeding without metadata assuming organization is DFO BIO."
                )

        # Determine QC start/end from metadata if available
        start_datetime_qc = start_datetime
        end_datetime_qc = end_datetime

        if organization == list_organization[1]:  # FSRS
            meta_subset = meta[meta["gauge"] == int(gauge_serial_number)]
            if not meta_subset.empty:
                if "datetime" in meta_subset.columns and not meta_subset["datetime"].isna().all():
                    meta_subset = meta_subset.copy()
                    meta_subset["datetime"] = pd.to_datetime(
                        meta_subset["datetime"], errors="coerce"
                    )
                    meta_subset = meta_subset.dropna(subset=["datetime", "soak_days"])
                    if not meta_subset.empty:
                        idx_start = meta_subset["datetime"].idxmin()
                        start_dt = meta_subset.loc[idx_start, "datetime"]
                        start_soak = meta_subset.loc[idx_start, "soak_days"]
                        start_datetime_qc = start_dt - pd.to_timedelta(start_soak, unit="D")

                        idx_end = meta_subset["datetime"].idxmax()
                        end_dt = meta_subset.loc[idx_end, "datetime"]
                        # end_soak = meta_subset.loc[idx_end, "soak_days"]
                        end_datetime_qc = end_dt  # + pd.to_timedelta(end_soak, unit="D")

                    else:
                        start_datetime_qc = start_datetime
                        end_datetime_qc = end_datetime

                # ---- Case 2: only date column exists ----
                elif "date" in meta_subset.columns and not meta_subset["date"].isna().all():
                    meta_subset = meta_subset.copy()
                    meta_subset["date"] = pd.to_datetime(meta_subset["date"], errors="coerce")
                    meta_subset = meta_subset.dropna(subset=["date", "soak_days"])
                    if not meta_subset.empty:
                        idx_start = meta_subset["date"].idxmin()
                        start_dt = meta_subset.loc[idx_start, "date"]
                        start_soak = meta_subset.loc[idx_start, "soak_days"]
                        start_datetime_qc = start_dt - pd.to_timedelta(start_soak, unit="D")

                        idx_end = meta_subset["date"].idxmax()
                        end_dt = meta_subset.loc[idx_end, "date"]
                        # end_soak = meta_subset.loc[idx_end, "soak_days"]
                        end_datetime_qc = end_dt  # + pd.to_timedelta(end_soak, unit="D")

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
                    "temp_drop": abs(temp_diff.loc[t]) if not pd.isna(temp_diff.loc[t]) else 0.0,
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
            best_rate = max(deployment_candidates_rate, key=lambda x: x["severity"], default=None)

            best_jump = max(deployment_candidates_jump, key=lambda x: x["severity"], default=None)

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
                    "temp_rise": abs(df.loc[t, "temp_diff"]) if pd.notna(df.loc[t, "temp_diff"]) else 0.0,
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
            best_rate = max(recovery_candidates_rate, key=lambda x: x["severity"], default=None)

            best_jump = max(recovery_candidates_jump, key=lambda x: x["severity"], default=None)

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
                        if event_num_int is not None and event_num_int in meta_subset.index:
                            meta_subset = meta_subset.loc[[event_num_int]]
                        else:
                            logger.warning(
                                f"Multiple metadata entries found for gauge {gauge_serial_number} "
                                "but event number is missing or invalid; using all entries for this gauge."
                            )
                            meta_subset = meta_subset

                else:
                    meta_subset = pd.DataFrame()

                if meta_subset.empty:
                    logger.warning(
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
                            start_in_meta = start_in_meta.tz_convert("UTC").tz_localize(None)

                        start_datetime = pd.to_datetime(start_datetime, errors="coerce")
                        if (start_in_meta - start_datetime) > tolerance_start_t:
                            start_datetime_qc = start_in_water
                        else:
                            start_datetime_qc = start_in_meta
                    else:
                        logger.warning(
                            "deploy_utc missing or empty in metadata; using in-water start."
                        )
                        start_datetime_qc = pd.to_datetime(start_in_water, errors="coerce")

                    if (
                        "recover_utc" in meta_subset.columns
                        and not meta_subset["recover_utc"].isna().all()
                    ):
                        meta_subset["recover_utc"] = pd.to_datetime(
                            meta_subset["recover_utc"], errors="coerce"
                        )
                        end_in_meta = meta_subset["recover_utc"].max()
                        if end_in_meta.tzinfo is not None:
                            end_in_meta = end_in_meta.tz_convert("UTC").tz_localize(None)
                        end_datetime = pd.to_datetime(end_datetime, errors="coerce")
                        if (end_datetime - end_in_meta) > tolerance_end_t:
                            end_datetime_qc = end_in_water
                        else:
                            end_datetime_qc = end_in_meta
                    else:
                        logger.warning(
                            "recover_utc missing or empty in metadata; using in-water end."
                        )
                        end_datetime_qc = pd.to_datetime(end_in_water, errors="coerce")

        logger.info(
            f"Determined QC window for {mtr_file}: {start_datetime_qc} to {end_datetime_qc}"
        )
        qc_start_num = mdates.date2num(pd.to_datetime(start_datetime_qc))
        qc_end_num = mdates.date2num(pd.to_datetime(end_datetime_qc))

        # Determine QC Mode based on existing flags and user selection
        has_previous_qc = np.any(df["qualityflag"] != 0)
        if (not has_previous_qc) and (qc_mode_user == 0):
            qc_mode_ = " QC Mode - Initial\n(No Previous QC Flags)"
            qc_mode_code_ = 0
            block_next_ = 0
        elif (not has_previous_qc) and (qc_mode_user == 1):
            qc_mode_ = " QC Mode - Invalid\n(Mode Selection Mismatch)"
            qc_mode_code_ = 1
            block_next_ = 1
            logger.warning(
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
            logger.warning(
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

        logger.info(f"QC Mode for this file {mtr_file}: {qc_mode_}")

        # Convert datetime to numeric for lasso selection
        xnums = mdates.date2num(df.index.to_pydatetime())
        xy = np.column_stack([mdates.date2num(df.index.to_pydatetime()), df["Temperature"]])
        before_qc_mask = df.index < start_datetime_qc
        after_qc_mask = df.index > end_datetime_qc
        if qc_mode_code_ == 0:
            df.loc[df.index < start_datetime_qc, "qualityflag"] = 4
            df.loc[df.index > end_datetime_qc, "qualityflag"] = 4
            in_water_mask = (df.index >= start_datetime_qc) & (df.index <= end_datetime_qc)
            df.loc[in_water_mask & ~df["qualityflag"].isin([4]), "qualityflag"] = 1
        colors_initial = [FLAG_COLORS.get(int(f), "#808080") for f in df["qualityflag"]]

        # Store multiple selection groups
        selection_groups = []
        applied = False
        user_exited = False
        current_flag = 4
        figsize = (14, 7)

        plt.style.use("ggplot")
        fig = plt.figure(figsize=figsize)
        ax = fig.add_axes([0.065, 0.15, 0.72, 0.8])

        qc_mode_ax = fig.add_axes([0.78, 0.78, 0.1, 0.35])
        qc_mode_ax.set_axis_off()
        qc_mode_ax.set_title(
            "QC Mode:",
            fontsize=15,
            pad=0,
            fontweight="heavy",
            color="navy",
            family="arial",
            loc="right",
        )
        qc_mode = CheckButtons(
            qc_mode_ax,
            labels=[qc_mode_],
            actives=[False],
        )
        for label in qc_mode.labels:
            label.set_fontsize(15)
            label.set_fontweight("bold")
            if qc_mode_code_ == 0:
                label.set_color("green")
            else:
                label.set_color("orange")
            label.set_family("arial")

        info_ax = fig.add_axes([0.79, 0.85, 0.1, 0.35])  # [left, bottom, width, height]
        info_ax.set_axis_off()  # hide the axes

        info_text = (
            f"\u2022 Deployed: {start_datetime_qc}\n"
            f"\u2022 Recovered: {end_datetime_qc}\n"
            f"\u2022 Recording Instrument: {instrument}\n"
            f"\u2022 Batch: {batch_name}\n"
        )

        info_ax.text(
            0,
            0,
            info_text,  # x=0 left, y=0 top
            fontsize=12,
            fontweight="bold",
            family="arial",
            color="navy",
            va="top",
            ha="left",
            wrap=True,
        )

        radio_ax = fig.add_axes([0.80, 0.20, 0.2, 0.35])
        radio_ax.set_axis_off()
        radio_ax.set_title(
            "Assign Quality Codes for\nSelected Points:",
            fontsize=12,
            pad=0,
            fontweight="heavy",
            color="navy",
            family="serif",
            loc="left",
        )

        ax_exit = fig.add_axes([0.004, 0.01, 0.05, 0.07])
        ax_deselect_all = fig.add_axes([0.06, 0.01, 0.14, 0.07])
        ax_export_df = fig.add_axes([0.21, 0.01, 0.13, 0.07])
        ax_continue = fig.add_axes([0.86, 0.01, 0.13, 0.07])

        scatter = ax.scatter(xnums, df["Temperature"], s=10, c=colors_initial, picker=5, zorder=1)
        ax.set_title(f"[{idx}/{len(mtr_files)}] {organization} Time Series Data- {mtr_file}")
        ax.set_xlabel("Date Time")
        ax.set_ylabel("Temperature")
        ax.grid(True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

        ax.axvspan(qc_start_num, qc_end_num, color="lightblue", alpha=0.25, label="QC Window")

        ax.axvline(
            qc_start_num, color="blue", linestyle="--", linewidth=2, label="Deployment: Start"
        )

        ax.axvline(qc_end_num, color="blue", linestyle="--", linewidth=2, label="Recovered: End")

        ymin, ymax = ax.get_ylim()

        ax.text(
            qc_start_num,
            ymax - 0.6,
            "Deployment: Start",
            color="purple",
            fontsize=8,
            verticalalignment="top",
            horizontalalignment="right",
            rotation=90,
            bbox=dict(facecolor="purple", alpha=0.3, edgecolor="none", pad=2),
        )

        ax.text(
            qc_end_num,
            ymax - 0.6,
            "Recovered: End",
            color="purple",
            fontsize=8,
            verticalalignment="top",
            horizontalalignment="right",
            rotation=90,
            bbox=dict(facecolor="purple", alpha=0.3, edgecolor="none", pad=2),
        )

        btn_deselect_all = Button(ax_deselect_all, "Undo All Selections")
        btn_deselect_all.color = "lightblue"
        btn_deselect_all.hovercolor = "yellow"
        btn_deselect_all.label.set_fontsize(10)

        btn_exit = Button(ax_exit, "Exit")
        btn_exit.color = "salmon"
        btn_exit.hovercolor = "red"
        btn_exit.label.set_fontsize(10)

        btn_continue = Button(ax_continue, "Continue Next >>")
        btn_continue.color = "lightgreen"
        btn_continue.hovercolor = "limegreen"
        btn_continue.label.set_fontsize(10)

        btn_export_df = Button(ax_export_df, "Export DataFrame")
        btn_export_df.color = "lightgrey"
        btn_export_df.hovercolor = "ghostwhite"
        btn_export_df.label.set_fontsize(10)

        radio_labels = [f"{k}: {FLAG_LABELS[k]}" for k in FLAG_LABELS]
        radio = RadioButtons(
            radio_ax, radio_labels, active=list(FLAG_LABELS.keys()).index(current_flag)
        )

        for i, text in enumerate(radio.labels):
            flag = list(FLAG_LABELS.keys())[i]
            text.set_color(FLAG_COLORS[flag])
            x, y = text.get_position()
            # Small color square beside text
            rect = Rectangle(
                (0.01, y - 0.017), 0.07, 0.05, color=FLAG_COLORS[flag], transform=radio_ax.transAxes
            )
            radio_ax.add_patch(rect)
            text.set_family("serif")
            text.set_fontsize(10)
            text.set_weight("bold")
            text.set_linespacing(1)

        def set_current_flag_from_label(label):
            nonlocal current_flag
            current_flag = int(label.split(":")[0])
            logger.info(f"Current flag set to {current_flag}")

        def click_continue(event):
            nonlocal applied
            applied = True
            logger.info("Figure: Continue clicked.")
            plt.close(fig)  # close figure and continue

        def click_exit(event):
            nonlocal user_exited
            global exit_requested
            user_exited = True
            exit_requested = True
            logger.info("Figure: Exit clicked (exit_requested set True).")
            plt.close(fig)  # close figure and stop

        def onselect(verts):
            path = Path(verts)
            selected_indices = np.nonzero(path.contains_points(xy))[0].astype(int)
            if selected_indices.size == 0:
                return
            logger.info(
                f"Selected {len(selected_indices)} point(s) via LASSO using current flag: {current_flag}"
            )
            df.iloc[selected_indices, df.columns.get_loc("qualityflag")] = current_flag
            try:
                facecolors = scatter.get_facecolors()
                new_rgba = np.array(mcolors.to_rgba(FLAG_COLORS[current_flag]))
                facecolors[selected_indices] = new_rgba
                scatter.set_facecolors(facecolors)
            except Exception:
                colors = [FLAG_COLORS[int(f)] for f in df["qualityflag"]]
                scatter.set_color(colors)

            selected_dt = df.index[selected_indices]
            selected_temp = df["Temperature"].iloc[selected_indices].to_numpy()
            # Store selected points
            selected_df = pd.DataFrame(
                {
                    "DateTime": selected_dt,
                    "Temperature": selected_temp,
                    "idx": selected_indices,
                    "Flag": current_flag,
                }
            )
            selection_groups.append(selected_df)
            fig.canvas.draw_idle()

        def click_deselect_all(event):
            nonlocal selection_groups, df, scatter
            selection_groups.clear()
            logger.info("Figure: Undo Selection clicked (all selections cleared).")
            df["qualityflag"] = qflag.copy()
            try:
                facecolors = scatter.get_facecolors()
                if facecolors.shape[0] != number_of_rows:
                    colors = np.array(
                        [mcolors.to_rgba(FLAG_COLORS[int(f)]) for f in df["qualityflag"]]
                    )
                    ax.cla()
                    scatter = ax.scatter(
                        xnums, df["Temperature"], s=12, c=colors, picker=5, zorder=2
                    )
                    ax.set_title(f"[{idx}/{len(mtr_files)}] Time Series Data- {mtr_file}")
                    ax.set_xlabel("Date Time")
                    ax.set_ylabel("Temperature")
                    ax.grid(True)
                else:
                    new_rgba = np.array(
                        [mcolors.to_rgba(FLAG_COLORS[int(f)]) for f in df["qualityflag"]]
                    )
                    facecolors[:, :] = new_rgba
                    scatter.set_facecolors(facecolors)
            except Exception:
                colors = [FLAG_COLORS[int(f)] for f in df["qualityflag"]]
                scatter.set_color(colors)
            fig.canvas.draw_idle()
            logging.getLogger("qc_tool").info(
                "Undo All Selections: restored original flags/colors."
            )

        def on_pick(event):
            # click-to-select: event.ind are positional indices
            if event.artist != scatter:
                return
            inds = np.unique(event.ind).astype(int)
            if inds.size == 0:
                return
            logger.info(
                f"Selected {len(inds)} point(s) via LASSO using current flag: {current_flag}"
            )
            # apply current flag to df (positional)
            df.iloc[inds, df.columns.get_loc("qualityflag")] = current_flag
            # update only those facecolors
            try:
                facecolors = scatter.get_facecolors()
                new_rgba = np.array(mcolors.to_rgba(FLAG_COLORS[current_flag]))
                facecolors[inds] = new_rgba
                scatter.set_facecolors(facecolors)
            except Exception:
                colors = [FLAG_COLORS[int(f)] for f in df["qualityflag"]]
                scatter.set_color(colors)
            # record selection group
            sel_dt = df.index[inds]
            sel_temp = df["Temperature"].iloc[inds].to_numpy()
            sel_df = pd.DataFrame(
                {"DateTime": sel_dt, "Temperature": sel_temp, "idx": inds, "Flag": current_flag}
            )
            selection_groups.append(sel_df)
            fig.canvas.draw_idle()

        def export_dataframe(event):
            nonlocal applied
            applied = True
            export_path, _ = QFileDialog.getSaveFileName(
                None,
                "Export DataFrame to CSV",
                f"{Path(Path.name(mtr_file)).stem}_QC_Export.csv",
                "CSV Files (*.csv);;All Files (*)",
            )
            if export_path:
                try:
                    df_export = df.copy()
                    df_export.reset_index(inplace=True)
                    df_export.rename(columns={"index": "SEQ_INDEX"}, inplace=True)
                    df_export.to_csv(export_path, index=False)
                    logger.info(f"DataFrame exported successfully to {export_path}")
                    QMessageBox.information(
                        None,
                        "Export Successful",
                        f"✅ DataFrame exported successfully to:\n{export_path}",
                    )
                except Exception as e:
                    logger.error(f"Failed to export DataFrame: {e}")
                    QMessageBox.critical(
                        None, "Export Failed", f"❌ Failed to export DataFrame:\n{e}"
                    )

        # Connect radio button event
        radio.on_clicked(set_current_flag_from_label)

        # Blocking next if mode mismatch
        if block_next_ == 1:
            btn_continue.disconnect_events()
            Path.rmdir(out_odf_path)

        # Bind button events
        btn_continue.on_clicked(click_continue)
        btn_exit.on_clicked(click_exit)
        btn_deselect_all.on_clicked(click_deselect_all)
        btn_export_df.on_clicked(export_dataframe)

        # Initialize Lasso Selector
        # lasso = LassoSelector(ax, onselect)
        # cid = fig.canvas.mpl_connect("pick_event", on_pick)

        ## Plt show non-blocking
        plt.show(block=False)
        logger.info(
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

        # Wait until the figure is closed, processing Qt events so the main GUI remains responsive
        app = QApplication.instance()
        while plt.fignum_exists(fig.number) and not exit_requested:
            if app:
                app.processEvents()
            time.sleep(0.001)

        # After closing the plot and collecting all selection groups
        if applied:
            if len(orig_df) != len(df):
                raise ValueError(
                    f"Size mismatch: orig_df has {len(orig_df)} rows, but df has {len(df)} rows."
                )

            if selection_groups:
                combined_indices = np.unique(
                    np.concatenate([g["idx"].to_numpy() for g in selection_groups])
                ).astype(int)
            else:
                combined_indices = np.array([], dtype=int)

            logger.info(f"Total of {len(combined_indices)} unique points selected for flagging.")

            if len(combined_indices) == 0:
                if qc_mode_code_ == 0:
                    # Initial QC Mode: no points selected → all flag = 1
                    orig_df["QTE90_01"] = 1
                    orig_df.loc[before_qc_mask, "QTE90_01"] = 4
                    orig_df.loc[after_qc_mask, "QTE90_01"] = 4
                    logger.info("No points were selected for this file.")
                    logger.info("Initial QC: applied default flags with QC window boundaries.")
                elif qc_mode_code_ == 1:
                    # Review-QC Mode: no points selected → no changes made
                    logger.info("No points were selected for this file; no changes made.")
                    pass

            if len(combined_indices) > 0:
                if qc_mode_code_ == 0:
                    orig_df["QTE90_01"] = 1
                    orig_df.loc[before_qc_mask, "QTE90_01"] = 4
                    orig_df.loc[after_qc_mask, "QTE90_01"] = 4
                    orig_df.iloc[combined_indices, orig_df.columns.get_loc("QTE90_01")] = df.iloc[
                        combined_indices
                    ]["qualityflag"].to_numpy()
                    logger.info(
                        f"Applied {len(combined_indices)} user-selected QC flags with window enforcement."
                    )
                elif qc_mode_code_ == 1:
                    orig_df.loc[before_qc_mask, "QTE90_01"] = 4
                    orig_df.loc[after_qc_mask, "QTE90_01"] = 4
                    orig_df.iloc[combined_indices, orig_df.columns.get_loc("QTE90_01")] = df.iloc[
                        combined_indices
                    ]["qualityflag"].to_numpy()
                    logger.info("Review QC: updated selected points and enforced QC window.")

        orig_df_after_qc = orig_df.copy()
        after_qc_flags = orig_df_after_qc["QTE90_01"].to_numpy().astype(int)
        before_qc_flags = orig_df_stored["QTE90_01"].to_numpy().astype(int)
        changed_mask = before_qc_flags != after_qc_flags
        changed_rows = orig_df_stored.loc[changed_mask, ["SYTM_01", "TE90_01", "QTE90_01"]]
        transitions = Counter(zip(before_qc_flags, after_qc_flags))
        for (before, after), count in transitions.items():
            if before != after:
                logger.info(f"Flag Code: {before} to Flag Code: {after}: {count}")
        if changed_rows.empty:
            logger.info(f"No quality flag changes were made for {mtr_file}")
        else:
            logger.info(f"Total QC flags changed for {mtr_file}: {len(changed_rows)}")

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
                # Extract 0–4 digit number between underscores in the filename
                fname = file_name  # remove .ODF
                match = re.search(r"_(\d{1,4})_", fname)
                if match:
                    event_num = match.group(1).zfill(3)  # pad with leading zeros if needed
                    # Insert event number into file_spec if missing
                    file_spec_parts = file_spec.split("__")
                    if len(file_spec_parts) == 2:
                        file_spec = f"{file_spec_parts[0]}_{event_num}_{file_spec_parts[1]}"
                    else:
                        # fallback: just append event_num if double underscore not found
                        file_spec = f"{file_spec.replace('.ODF', '')}_{event_num}.ODF"
                else:
                    raise ValueError(f"Could not determine event number from filename: {mtr_file}")

            mtr.file_specification = file_spec
            logger.info(f"Writing file {idx} of {len(mtr_files)}: {mtr_file}")
            logger.info("Please wait...writing QC ODF file...")
            out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
            mtr.write_odf(str(out_file), version=2.0)
            logger.info(f"QC completed for [{idx}/{len(mtr_files)}]: {mtr_file}")
            logger.info(f"Saved [{idx}/{len(mtr_files)}]: {out_file}")
        except Exception as e:
            logger.exception(f"Failed writing QC ODF for {mtr_file}: {e}")

    # Completed loop
    if not exit_requested and (idx == len(mtr_files)):
        logger.info(f"QC process completed for all {len(mtr_files)} files.")
        batch_result_container["finished"] = True
    elif exit_requested:
        logger.info(
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

    select_inputs = select_metadata_file_and_data_folder.SubWindowOne(review_mode=review_mode)
    select_inputs.show()

    result_container = {
        "finished": False,
        "input": None,
        "output": None,
        "operator": None,
        "metadata": None,
        "batch": None,
    }

    def on_accept():
        operator = select_inputs.line_edit_text.strip()
        metadata_file_path = select_inputs.metadata_file
        input_path = select_inputs.input_data_folder
        output_path = select_inputs.output_data_folder
        batch_name = select_inputs.generate_batch

        if not operator or not input_path or not output_path:
            print("❌ Missing required fields.")
            return

        result_container["operator"] = operator
        result_container["metadata"] = metadata_file_path
        result_container["input"] = input_path
        result_container["output"] = output_path
        result_container["finished"] = True
        result_container["batch"] = batch_name
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
        )
    else:
        return None, None, None, None, None


def exit_program(app):
    """
    Clean exit.
    """
    global exit_requested
    exit_requested = True
    logger.info("Exit Program clicked — setting exit_requested and quitting.")
    # Allow logger to flush
    handlers = logger.handlers[:]
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
    logger.info("Start QC button clicked.")

    review_mode = log_ui.radio_opt.isChecked()
    if review_mode:
        logger.info("Review QC Mode selected.")
    else:
        logger.info("Initial QC Mode selected.")

    input_path, output_path, operator, metadata_file_path, batch_name = main_select_inputs(
        review_mode
    )
    if not input_path or not output_path or not operator:
        logger.info("QC start aborted: missing input, output, or operator.")
        return
    logger.info(
        "QC Inputs Selected:\n"
        f"  • QC Operator : {operator.strip().title()}\n"
        f"  • Input Path  : {input_path}\n"
        f"  • Output Path : {output_path}\n"
        f"  • Metadata    : {metadata_file_path}\n"
        f"  • BatchName    : {batch_name}\n"
    )
    run_qc_thermograph_data(
        input_path, output_path, operator, metadata_file_path, review_mode, batch_name
    )


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    log_window = LogWindowThermographQC()
    log_window.show()
    logger.addHandler(log_window.qtext_handler)
    logger.info("Log window initialized.")
    log_window.radio_opt.toggled.connect(
        lambda checked: logger.info(f"Radio button is {'checked' if checked else 'unchecked'}")
    )

    # Connect buttons
    # log_window.btn_start.clicked.connect(lambda: start_qc_process(log_window))
    log_window.btn_start.clicked.connect(
        lambda: start_qc_process(log_window, log_window.radio_opt.isChecked())
    )
    log_window.btn_exit.clicked.connect(lambda: exit_program(app))
    logger.info("Application started. Use Start QC to begin.")

    # Start the Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
