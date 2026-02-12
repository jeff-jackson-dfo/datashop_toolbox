import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QApplication

from datashop_toolbox import select_metadata_file_and_data_folder
from datashop_toolbox.thermograph import ThermographHeader


def regional_meta_bioregions():
    base_dir = Path(Path(__file__).resolve()).parent

    bioregions_file_path = Path(base_dir / "map" / "All_Federal_Marine_bioregions.geojson").resolve()
    try:
        with Path.open(bioregions_file_path) as f:
            bioregions = json.load(f)["features"]
    except FileNotFoundError:
        print(f"Error: The file '{bioregions_file_path}' was not found.")
    except json.JSONDecodeError:
        print(
            f"Error: Could not decode JSON from the file '{bioregions_file_path}'. Check file format."
        )

    return bioregions


def regional_meta_temp_climatology():
    base_dir = Path(Path(__file__).resolve()).parent

    temp_climatology_path = Path(base_dir / "map" / "temp_climatology.txt")
    try:
        with Path.open(temp_climatology_path) as file:
            temp_climatology = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{temp_climatology_path}' was not found.")
    except json.JSONDecodeError:
        print(
            f"Error: Could not decode JSON from the file '{temp_climatology_path}'. Check file format."
        )
    return temp_climatology


def point_in_polygon(lon, lat, polygon):
    inside = False
    n = len(polygon)

    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        if (y1 > lat) != (y2 > lat):
            xinters = (lat - y1) * (x2 - x1) / (y2 - y1 + 1e-12) + x1
            if lon < xinters:
                inside = not inside

    return inside


def get_bioregion(lat, lon):
    bioregions = regional_meta_bioregions()
    for feature in bioregions:
        geom = feature["geometry"]
        name = feature["properties"].get("NAME_E")

        if geom["type"] == "Polygon":
            rings = geom["coordinates"]
            if point_in_polygon(lon, lat, rings[0]):
                return name

        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                if point_in_polygon(lon, lat, poly[0]):
                    return name

    return None


def get_surface_temp_profile(lat, lon):
    temp_climatology = regional_meta_temp_climatology()
    region = get_bioregion(lat, lon)

    if region is None:
        temps = temp_climatology.get("DFO-Special Region")
        return {
            "Latitude": lat,
            "Longitude": lon,
            "Bioregion": "DFO-Special Region",
            "SurfaceTemperatureProfile": temps,
        }

    temps = temp_climatology.get(region)

    return {
        "Latitude": lat,
        "Longitude": lon,
        "Bioregion": region,
        "SurfaceTemperatureProfile": temps,
    }


def get_season(dt):
    """Return climatological season name for a datetime"""
    month = dt.month
    if month in (12, 1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Spring"
    elif month in (6, 7, 8):
        return "Summer"
    else:
        return "Fall"


def prepare_output_folder(in_folder_path: str, out_folder_path: str, qc_operator: str) -> str:
    base_name_input = "Step_1_Create_ODF"
    in_folder_path = Path(in_folder_path).resolve()

    base_name_output = "Step_2_Assign_QFlag"
    out_folder_path = Path(out_folder_path).resolve()
    out_odf_path = Path(out_folder_path / base_name_output)
    out_odf_path = Path(out_odf_path).resolve()

    if base_name_input.lower() in in_folder_path.lower():
        if (not Path.exists(out_odf_path)) and (out_odf_path != in_folder_path):
            print(
                "Initial QC Mode: No existing output folder found. Creating new folder, name : Step_2_Assign_QFlag"
            )
            Path.mkdir(out_odf_path, parents=True)
            print(f"Created output folder: {out_odf_path}")
        else:
            print("Initial QC Mode: Overwriting existing output folder, name : Step_2_Assign_QFlag")
            shutil.rmtree(out_odf_path)
            Path.mkdir(out_odf_path, parents=True)
            print(f"Overwriting existing folder: {out_odf_path}")

    return out_odf_path


def qc_ai_thermograph_data(
    in_folder_path: str, wildcard: str, out_folder_path: str, qc_operator: str
):

    cwd = Path.cwd()

    try:
        os.chdir(in_folder_path)
        print(f"Changed working dir to the input directory: {in_folder_path}")
    except Exception as e:
        print(f"Cannot change directory: {e}")

    mtr_files = Path.glob(wildcard)
    if not mtr_files:
        print("No ODF files found in selected folder.")
        os.chdir(cwd)

    # Prepare output folder
    out_odf_path = prepare_output_folder(in_folder_path, out_folder_path, qc_operator)
    print("Created a output data folder name, Step_2_Quality_Flagging ")
    print(f"Path for Step_2_Quality_Flagging: {out_odf_path}")

    os.chdir(cwd)

    for idx, mtr_file in enumerate(mtr_files, start=1):
        print(f"Reading file {idx} of {len(mtr_files)}: {mtr_file}")
        print("Please wait...reading ODF file for QC visualization...")

        full_path = str(Path(in_folder_path, mtr_file))

        try:
            mtr = ThermographHeader()
            mtr.read_odf(full_path)
        except Exception as e:
            print(f"Failed to read ODF {full_path}: {e}")
            continue

        orig_df = mtr.data.data_frame
        # orig_df_stored = orig_df.copy()
        orig_df = orig_df.copy()
        orig_df.reset_index(drop=True, inplace=True)
        orig_df = pd.DataFrame(orig_df)

        initial_lat = mtr.event_header.initial_latitude
        initial_lon = mtr.event_header.initial_longitude
        start_datetime = mtr.event_header.start_date_time
        end_datetime = mtr.event_header.end_date_time
        organization = mtr.cruise_header.organization
        list_organization = ["DFO BIO", "FSRS"]

        # Extract temperature and time
        temp = orig_df["TE90_01"].to_numpy()
        sytm = orig_df["SYTM_01"].str.lower().str.strip("'")

        if "QTE90_01" in orig_df.columns:
            qflag = orig_df["QTE90_01"].to_numpy().astype(int)
        else:
            orig_df["QTE90_01"] = np.zeros(len(orig_df), dtype=int)
            qflag = orig_df["QTE90_01"].to_numpy().astype(int)

        try:
            dt = pd.to_datetime(sytm, format="%d-%b-%Y %H:%M:%S.%f")
        except (ValueError, TypeError):
            dt = pd.to_datetime(sytm, errors="coerce")

        # Create a DataFrame with Temperature as the variable and DateTime as the index.
        df = pd.DataFrame({"Temperature": temp, "qualityflag": qflag}, index=dt)
        df["qualityflag"] = np.where(df["Temperature"].isna(), 4, df["qualityflag"])

        if organization == list_organization[0]:
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
            deployment_jump_idx = df.index[temp_diff <= -rise_threshold]

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

            ## In Water Mask
            df.loc[df.index < start_in_water, "qualityflag"] = 4
            df.loc[df.index > end_in_water, "qualityflag"] = 4
            in_water_mask = (df.index >= start_in_water) & (df.index <= end_in_water)

            # Seasonal temperature limits
            sst_location = get_surface_temp_profile(initial_lat, initial_lon)
            seasonal_limits = sst_location["SurfaceTemperatureProfile"]
            df["Season"] = df.index.to_series().apply(get_season)
            for season, (tmin, tmax) in seasonal_limits.items():
                mask_season = df["Season"] == season
                mask_low = df["Temperature"] < tmin
                mask_high = df["Temperature"] > tmax
                mask_3 = in_water_mask & mask_season & (mask_low | mask_high)
                flagged = df.loc[mask_3, ["Season", "Temperature", "qualityflag"]]
                df.loc[mask_3, "qualityflag"] = 3
                if not flagged.empty:
                    print(f"\n🚩 Season: {season}")
                    print(f"Allowed range: {tmin} to {tmax}")
                    print(flagged)

            # Adaptive rolling STD limits for unstable data
            dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.0
            sample_minutes = dt_minutes.median()
            n_samples = 3
            rolling_minutes = sample_minutes * n_samples
            rolling_window = f"{int(round(rolling_minutes))}min"
            min_periods = n_samples - 1
            df["T_std_adaptive"] = (
                df["Temperature"].rolling(rolling_window, min_periods=min_periods).std()
            )
            base_std_threshold = 2.0
            base_sample_min = 60.0
            stable_std_threshold = base_std_threshold * (sample_minutes / base_sample_min) ** 0.5
            mask_unstable = df["T_std_adaptive"] > stable_std_threshold
            df.loc[mask_unstable, "qualityflag"] = 2
            df.loc[mask_unstable & ~df["qualityflag"].isin([3, 4]), "qualityflag"] = 2

            # Stable data points
            stable_mask = ~mask_unstable & in_water_mask
            df.loc[stable_mask & ~df["qualityflag"].isin([2, 3, 4]), "qualityflag"] = 1

            qc_df = pd.DataFrame(
                {
                    "SYTM_01": df.index.strftime("'%d-%b-%Y %H:%M:%S.00'").str.upper(),
                    "TE90_01": df["Temperature"].to_numpy(),
                    "QTE90_01": df["qualityflag"].astype(int).to_numpy(),
                }
            )
            if len(qc_df) != len(orig_df):
                raise ValueError(
                    f"Row count mismatch: original={len(orig_df)}, updated={len(qc_df)}"
                )

            # 2. Required columns check
            required_cols = {"SYTM_01", "TE90_01", "QTE90_01"}
            if not required_cols.issubset(orig_df.columns):
                missing = required_cols - set(orig_df.columns)
                raise KeyError(f"Missing required columns in original data: {missing}")

            # 3. Safe column update (preserves everything else)
            orig_df.loc[:, "SYTM_01"] = qc_df["SYTM_01"].astype(str).values
            orig_df.loc[:, "TE90_01"] = qc_df["TE90_01"].values
            orig_df.loc[:, "QTE90_01"] = qc_df["QTE90_01"].values

            # 4. Enforce integer QC flags
            orig_df["QTE90_01"] = orig_df["QTE90_01"].astype(int)

        if organization == list_organization[1]:
            ## In Water Mask
            df.loc[df.index < start_datetime, "qualityflag"] = 4
            df.loc[df.index > end_datetime, "qualityflag"] = 4
            in_water_mask = (df.index >= start_datetime) & (df.index <= end_datetime)

            # Seasonal temperature limits
            sst_location = get_surface_temp_profile(initial_lat, initial_lon)
            seasonal_limits = sst_location["SurfaceTemperatureProfile"]
            df["Season"] = df.index.to_series().apply(get_season)
            for season, (tmin, tmax) in seasonal_limits.items():
                mask_season = df["Season"] == season
                mask_low = df["Temperature"] < tmin
                mask_high = df["Temperature"] > tmax
                mask_3 = in_water_mask & mask_season & (mask_low | mask_high)
                flagged = df.loc[mask_3, ["Season", "Temperature", "qualityflag"]]
                df.loc[mask_3, "qualityflag"] = 3
                if not flagged.empty:
                    print(f"\n🚩 Season: {season}")
                    print(f"Allowed range: {tmin} to {tmax}")
                    print(flagged)

            # Adaptive rolling STD limits for unstable data
            dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.0
            sample_minutes = dt_minutes.median()
            n_samples = 3
            rolling_minutes = sample_minutes * n_samples
            rolling_window = f"{int(round(rolling_minutes))}min"
            min_periods = n_samples - 1
            df["T_std_adaptive"] = (
                df["Temperature"].rolling(rolling_window, min_periods=min_periods).std()
            )
            base_std_threshold = 6.0
            base_sample_min = 60.0
            stable_std_threshold = base_std_threshold * (sample_minutes / base_sample_min) ** 0.5
            mask_unstable = df["T_std_adaptive"] > stable_std_threshold
            df.loc[mask_unstable, "qualityflag"] = 2
            df.loc[mask_unstable & ~df["qualityflag"].isin([3, 4]), "qualityflag"] = 2

            # Stable data points
            stable_mask = ~mask_unstable & in_water_mask
            df.loc[stable_mask & ~df["qualityflag"].isin([2, 3, 4]), "qualityflag"] = 1

            qc_df = pd.DataFrame(
                {
                    "SYTM_01": df.index.strftime("'%d-%b-%Y %H:%M:%S.00'").str.upper(),
                    "TE90_01": df["Temperature"].to_numpy(),
                    "QTE90_01": df["qualityflag"].astype(int).to_numpy(),
                }
            )
            if len(qc_df) != len(orig_df):
                raise ValueError(
                    f"Row count mismatch: original={len(orig_df)}, updated={len(qc_df)}"
                )

            # 2. Required columns check
            required_cols = {"SYTM_01", "TE90_01", "QTE90_01"}
            if not required_cols.issubset(orig_df.columns):
                missing = required_cols - set(orig_df.columns)
                raise KeyError(f"Missing required columns in original data: {missing}")

            # 3. Safe column update (preserves everything else)
            orig_df.loc[:, "SYTM_01"] = qc_df["SYTM_01"].astype(str).values
            orig_df.loc[:, "TE90_01"] = qc_df["TE90_01"].values
            orig_df.loc[:, "QTE90_01"] = qc_df["QTE90_01"].values

            # 4. Enforce integer QC flags
            orig_df["QTE90_01"] = orig_df["QTE90_01"].astype(int)

        try:
            mtr.data.data_frame = orig_df
            mtr.add_history()
            mtr.add_to_history(
                f"REVIEWED AND UPDATED QUALITY CODE FLAGGING BY {qc_operator.upper()}"
            )
            mtr.update_odf()
            file_spec = mtr.generate_file_spec()
            mtr.file_specification = file_spec
            print(f"Writing file {idx} of {len(mtr_files)}: {mtr_file}")
            print("Please wait...writing QC ODF file...")
            out_file = Path(out_odf_path) / f"{file_spec}.ODF"
            mtr.write_odf(str(out_file), version=2.0)
            out_file_csv = Path(out_odf_path) / f"{file_spec}.csv"
            df.to_csv(out_file_csv)
            print(f"QC completed for [{idx}/{len(mtr_files)}]: {mtr_file}")
            print(f"Saved [{idx}/{len(mtr_files)}]: {out_file}")
        except Exception as e:
            print(f"Failed writing QC ODF for {mtr_file}: {e}")


def main_select_inputs():
    app = QApplication.instance()
    must_quit_app = app is None
    if must_quit_app:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    select_inputs = select_metadata_file_and_data_folder.SubWindowOne()
    select_inputs.show()

    result_container = {"finished": False, "input": None, "output": None, "operator": None}

    def on_accept():
        operator = select_inputs.line_edit_text.strip()
        input_path = select_inputs.input_data_folder
        output_path = select_inputs.output_data_folder

        if not operator or not input_path or not output_path:
            print("❌ Missing required fields.")
            return

        result_container["operator"] = operator
        result_container["input"] = input_path
        result_container["output"] = output_path
        result_container["finished"] = True
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
        )
    else:
        return None, None, None


def main():
    global exit_requested
    exit_requested = False
    input_path, output_path, operator = main_select_inputs()
    wildcard = "*.ODF"
    if not input_path or not output_path or not operator:
        print("QC start aborted: missing input, output, or operator.")
        return
    print(
        "QC Inputs Selected:\n"
        f"  • QC Operator : {operator.strip().title()}\n"
        f"  • Input Path  : {input_path}\n"
        f"  • Output Path : {output_path}"
    )
    qc_ai_thermograph_data(input_path, wildcard, output_path, operator)
    print("Finished batch successfully")
    print("Please Start QC for new batch.")


if __name__ == "__main__":
    main()
