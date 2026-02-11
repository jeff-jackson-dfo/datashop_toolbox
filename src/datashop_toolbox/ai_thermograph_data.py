import glob
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector, Button, RadioButtons, CheckButtons
from matplotlib.path import Path
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle, Patch
import matplotlib.colors as mcolors
import numpy as np
import os
import shutil
from datetime import datetime
import pandas as pd
import pathlib
import sys
import time
import json
from PySide6.QtWidgets import (
    QApplication,QMessageBox)
from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.validated_base import get_current_date_time
from datashop_toolbox import select_metadata_file_and_data_folder


def regional_meta_BIOREGIONS():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    bioregions_file_path = os.path.join(
        BASE_DIR,
        "map",
        "All_Federal_Marine_Bioregions.geojson"
    )
    try:
        with open(bioregions_file_path, "r") as f:
            BIOREGIONS = json.load(f)["features"]
    except FileNotFoundError:
        print(f"Error: The file '{bioregions_file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{bioregions_file_path}'. Check file format.")

    return BIOREGIONS


def regional_meta_TEMP_CLIMATOLOGY():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    temp_climatology_path = os.path.join(
        BASE_DIR,
        "map",
        "temp_climatology.txt"
    )
    try:
        with open(temp_climatology_path, "r") as file:
            TEMP_CLIMATOLOGY = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{temp_climatology_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{temp_climatology_path}'. Check file format.")
    return TEMP_CLIMATOLOGY


def point_in_polygon(lon, lat, polygon):
    inside = False
    n = len(polygon)

    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        if ((y1 > lat) != (y2 > lat)):
            xinters = (lat - y1) * (x2 - x1) / (y2 - y1 + 1e-12) + x1
            if lon < xinters:
                inside = not inside

    return inside


def get_bioregion(lat, lon):
    bioregions = regional_meta_BIOREGIONS()
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
    temp_climatology = regional_meta_TEMP_CLIMATOLOGY()
    region = get_bioregion(lat, lon)
    
    if region is None:
        temps = temp_climatology.get("DFO-Special Region")
        return {
            "Latitude": lat,
            "Longitude": lon,
            "Bioregion": "DFO-Special Region",
            "SurfaceTemperatureProfile": temps
        }
    
    temps = temp_climatology.get(region)
    
    return {
        "Latitude": lat,
        "Longitude": lon,
        "Bioregion": region,
        "SurfaceTemperatureProfile": temps
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
    in_folder_path = os.path.abspath(in_folder_path)
    
    base_name_output = "Step_2_Assign_QFlag"
    out_folder_path = os.path.abspath(out_folder_path)
    out_odf_path = os.path.join(out_folder_path, base_name_output)
    out_odf_path = os.path.abspath(out_odf_path)

    
    if base_name_input.lower() in in_folder_path.lower():
        if (not os.path.exists(out_odf_path)) and (out_odf_path != in_folder_path):
            print(f"Initial QC Mode: No existing output folder found. Creating new folder, name : Step_2_Assign_QFlag")
            os.makedirs(out_odf_path, exist_ok=True)
            print(f"Created output folder: {out_odf_path}")
        else:
            print(f"Initial QC Mode: Overwriting existing output folder, name : Step_2_Assign_QFlag")
            shutil.rmtree(out_odf_path)
            os.makedirs(out_odf_path, exist_ok=True)
            print(f"Overwriting existing folder: {out_odf_path}")
   
    return out_odf_path


def qc_AI_thermograph_data(in_folder_path: str, wildcard: str, out_folder_path: str, qc_operator: str):

    cwd = os.getcwd()

    try:
        os.chdir(in_folder_path)
        print(f"Changed working dir to the input directory: {in_folder_path}")
    except Exception as e:
        print(f"Cannot change directory: {e}")

    mtr_files = glob.glob(wildcard)
    if not mtr_files:
        print("No ODF files found in selected folder.")
        os.chdir(cwd)
      
    # Prepare output folder
    out_odf_path = prepare_output_folder(in_folder_path, out_folder_path, qc_operator)
    print(f"Created a output data folder name, Step_2_Quality_Flagging ")
    print(f"Path for Step_2_Quality_Flagging: {out_odf_path}")

    os.chdir(cwd)

    for idx, mtr_file in enumerate(mtr_files, start=1):
       
        print(f"Reading file {idx} of {len(mtr_files)}: {mtr_file}")
        print(f"Please wait...reading ODF file for QC visualization...")

        full_path = str(pathlib.Path(in_folder_path, mtr_file))
        
        try:
            mtr = ThermographHeader()
            mtr.read_odf(full_path)
        except Exception as e:
            print(f"Failed to read ODF {full_path}: {e}")
            continue

        orig_df = mtr.data.data_frame
        orig_df_stored = orig_df.copy()
        orig_df =orig_df.copy()
        orig_df.reset_index(drop=True, inplace=True)
        orig_df= pd.DataFrame(orig_df)

        Initial_lat= mtr.event_header.initial_latitude
        Initial_lon= mtr.event_header.initial_longitude
        Start_datetime= mtr.event_header.start_date_time
        End_datetime= mtr.event_header.end_date_time
        organization =mtr.cruise_header.organization
        list_organization= ['DFO BIO','FSRS']

        # Extract temperature and time
        temp = orig_df['TE90_01'].to_numpy()
        sytm = orig_df['SYTM_01'].str.lower().str.strip("'")
        
        if 'QTE90_01' in orig_df.columns:
            qflag = orig_df['QTE90_01'].to_numpy().astype(int)
        else:
            orig_df['QTE90_01']= np.zeros(len(orig_df), dtype=int)
            qflag = orig_df['QTE90_01'].to_numpy().astype(int)
        
        try:
            dt = pd.to_datetime(sytm, format='%d-%b-%Y %H:%M:%S.%f')
        except (ValueError, TypeError):
            dt = pd.to_datetime(sytm, errors="coerce")

       
        # Create a DataFrame with Temperature as the variable and DateTime as the index.
        df = pd.DataFrame({'Temperature': temp, 'qualityflag': qflag}, index=dt)
        df['qualityflag'] = np.where(df['Temperature'].isna(), 4, df['qualityflag'])
        
        if organization== list_organization[0]:
            dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.0
            dTdt = df["Temperature"].diff() / dt_minutes
            dTdt = dTdt.replace([np.inf, -np.inf], np.nan)
            dT = df["Temperature"].diff()
            df["dTdt"] = dTdt
            df["dT"] = dT
            
            DROP_THRESHOLD = -0.2   # °C per sample minute (deployment)
            RISE_THRESHOLD =  0.2   # °C per sample minute (recovery)
            TEMP_JUMP_MAG = 2.0     # °C jump per sample interval
            
            deployment_rate_idx = df.index[dTdt < DROP_THRESHOLD]
            deployment_jump_idx = df.index[dT <= -TEMP_JUMP_MAG]

            deployment_candidates_rate = [
                {
                    "time": t,
                    "type": "rate",
                    "severity": abs(dTdt.loc[t]),   # °C/min
                    "temp_drop": abs(dT.loc[t]) if not pd.isna(dT.loc[t]) else 0.0
                }
                for t in deployment_rate_idx
            ]

            deployment_candidates_jump = [
                {
                    "time": t,
                    "type": "jump",
                    "severity": abs(dT.loc[t]),     # °C
                    "temp_drop": abs(dT.loc[t])
                }
                for t in deployment_jump_idx
            ]

            # --- Pick strongest from each ---
            best_rate = max(
                deployment_candidates_rate,
                key=lambda x: x["severity"],
                default=None
            )

            best_jump = max(
                deployment_candidates_jump,
                key=lambda x: x["severity"],
                default=None
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
           
            recovery_rate_idx = df.index[df["dTdt"] > RISE_THRESHOLD]
            recovery_jump_idx = df.index[df["dT"] >= TEMP_JUMP_MAG]

            recovery_candidates_rate = [
                {
                    "time": t,
                    "type": "rate",
                    "severity": abs(df.loc[t, "dTdt"]),   # °C/min
                    "temp_rise": abs(df.loc[t, "dT"]) if pd.notna(df.loc[t, "dT"]) else 0.0
                }
                for t in recovery_rate_idx
            ]

            recovery_candidates_jump = [
                {
                    "time": t,
                    "type": "jump",
                    "severity": abs(df.loc[t, "dT"]),     # °C
                    "temp_rise": abs(df.loc[t, "dT"])
                }
                for t in recovery_jump_idx
            ]

            # --- Pick strongest from each ---
            best_rate = max(
                recovery_candidates_rate,
                key=lambda x: x["severity"],
                default=None
            )

            best_jump = max(
                recovery_candidates_jump,
                key=lambda x: x["severity"],
                default=None
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
            
            
            ## In Water Mask
            df.loc[df.index < start_in_water, "qualityflag"] = 4
            df.loc[df.index > end_in_water, "qualityflag"] = 4
            in_water_mask = (df.index >= start_in_water) & (df.index <= end_in_water)


            # Seasonal temperature limits
            sst_location= get_surface_temp_profile(Initial_lat, Initial_lon)
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
            dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.
            sample_minutes = dt_minutes.median()
            N_SAMPLES = 3
            rolling_minutes = sample_minutes * N_SAMPLES
            rolling_window = f"{int(round(rolling_minutes))}min"
            min_periods = N_SAMPLES - 1
            df["T_std_adaptive"] = (
                df["Temperature"]
                .rolling(rolling_window, min_periods=min_periods)
                .std()
            )
            BASE_STD_THRESHOLD = 2.0
            BASE_SAMPLE_MIN = 60.0
            STABLE_STD_THRESHOLD = (BASE_STD_THRESHOLD * (sample_minutes / BASE_SAMPLE_MIN) ** 0.5)
            mask_unstable = df["T_std_adaptive"] > STABLE_STD_THRESHOLD
            df.loc[mask_unstable, "qualityflag"] = 2
            df.loc[mask_unstable & ~df["qualityflag"].isin([3, 4]), "qualityflag"] = 2
            
            # Stable data points
            stable_mask = ~mask_unstable & in_water_mask
            df.loc[stable_mask & ~df["qualityflag"].isin([2, 3, 4]),"qualityflag"] = 1

            qc_df  = pd.DataFrame({
                        "SYTM_01": df.index.strftime("'%d-%b-%Y %H:%M:%S.00'").str.upper(),
                        "TE90_01": df["Temperature"].to_numpy(),
                        "QTE90_01": df["qualityflag"].astype(int).to_numpy()
                    })
            if len(qc_df) != len(orig_df):
                raise ValueError(
                    f"Row count mismatch: "
                    f"original={len(orig_df)}, updated={len(qc_df)}"
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
    
        
        if organization== list_organization[1]:
            ## In Water Mask
            df.loc[df.index < Start_datetime, "qualityflag"] = 4
            df.loc[df.index > End_datetime, "qualityflag"] = 4
            in_water_mask = (df.index >= Start_datetime) & (df.index <= End_datetime)
            
            # Seasonal temperature limits
            sst_location= get_surface_temp_profile(Initial_lat, Initial_lon)
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
            dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.
            sample_minutes = dt_minutes.median()
            N_SAMPLES = 3
            rolling_minutes = sample_minutes * N_SAMPLES
            rolling_window = f"{int(round(rolling_minutes))}min"
            min_periods = N_SAMPLES - 1
            df["T_std_adaptive"] = (
                df["Temperature"]
                .rolling(rolling_window, min_periods=min_periods)
                .std()
            )
            BASE_STD_THRESHOLD = 6.0
            BASE_SAMPLE_MIN = 60.0
            STABLE_STD_THRESHOLD = (BASE_STD_THRESHOLD * (sample_minutes / BASE_SAMPLE_MIN) ** 0.5)
            mask_unstable = df["T_std_adaptive"] > STABLE_STD_THRESHOLD
            df.loc[mask_unstable, "qualityflag"] = 2
            df.loc[mask_unstable & ~df["qualityflag"].isin([3, 4]), "qualityflag"] = 2
            
            # Stable data points
            stable_mask = ~mask_unstable & in_water_mask
            df.loc[stable_mask & ~df["qualityflag"].isin([2, 3, 4]),"qualityflag"] = 1

            qc_df  = pd.DataFrame({
                        "SYTM_01": df.index.strftime("'%d-%b-%Y %H:%M:%S.00'").str.upper(),
                        "TE90_01": df["Temperature"].to_numpy(),
                        "QTE90_01": df["qualityflag"].astype(int).to_numpy()
                    })
            if len(qc_df) != len(orig_df):
                raise ValueError(
                    f"Row count mismatch: "
                    f"original={len(orig_df)}, updated={len(qc_df)}"
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
            mtr.add_to_history(f'REVIEWED AND UPDATED QUALITY CODE FLAGGING BY {qc_operator.upper()}')
            mtr.update_odf()
            file_spec = mtr.generate_file_spec()
            mtr.file_specification = file_spec
            print(f"Writing file {idx} of {len(mtr_files)}: {mtr_file}")
            print(f"Please wait...writing QC ODF file...")
            out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
            mtr.write_odf(str(out_file), version=2.0)
            out_file_csv = pathlib.Path(out_odf_path) / f"{file_spec}.csv"
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
    print( "QC Inputs Selected:\n"
            f"  • QC Operator : {operator.strip().title()}\n"
            f"  • Input Path  : {input_path}\n"
            f"  • Output Path : {output_path}"
            )
    qc_AI_thermograph_data(input_path, wildcard, output_path, operator)
    print("Finished batch successfully")
    print("Please Start QC for new batch.")

    

if __name__ == "__main__":
    main()
    
















