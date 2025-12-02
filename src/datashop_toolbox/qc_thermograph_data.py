import glob
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector, Button
from matplotlib.path import Path
import matplotlib.dates as mdates
import numpy as np
import os
import pandas as pd
import pathlib
import sys

from PyQt6.QtWidgets import (
    QApplication,
)


from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.validated_base import get_current_date_time
from datashop_toolbox import select_metadata_file_and_data_folder



def run_qc_thermograph_data(input_path, output_path, qc_operator):
    wildcard = "*.ODF"
    task_completion= qc_thermograph_data(input_path, wildcard, output_path, qc_operator)
    if task_completion["finished"]:
        print("✅ QC Thermograph Data task completed successfully.")
    else:
        print("❌ QC Thermograph Data task did not complete.")
    return task_completion
   
    
def qc_thermograph_data(in_folder_path: str, wildcard: str, out_folder_path: str, qc_operator: str):
    
    global exit_requested
    exit_requested = False
    batch_result_container = {"finished": False}

    cwd = os.getcwd()

    # Find all files selected using the wildcard in the provided input directory.
    try:
        os.chdir(in_folder_path)
        print(f"Changed working dir to the input directory: {in_folder_path}")
    except Exception as e:
        raise RuntimeError(f"Cannot change directory: {e}")
    
    mtr_files = glob.glob(wildcard)
    if not mtr_files:
        print("❌ No ODF files found in selected folder.")
        return

    # Prepare output folder
    out_odf_path = os.path.join(out_folder_path, "Step_2_Quality_Flagging")
    os.makedirs(out_odf_path, exist_ok=True)
    print(f"Created a output data folder name: Step_2_Quality_Flagging and path for .odf files after initial QC: {out_odf_path}")

    os.chdir(cwd)

    for idx, mtr_file in enumerate(mtr_files, start=1):
        
        print(f"Reading file {idx} of {len(mtr_files)}: {mtr_file} for QC...please wait.")

        if exit_requested:
            break
 
        full_path = str(pathlib.Path(in_folder_path, mtr_file))
        
        mtr = ThermographHeader()

        mtr.read_odf(full_path)

        mtr.add_quality_flags()

        orig_df = mtr.data.data_frame

        # Extract temperature and time
        temp = orig_df['TE90_01'].to_numpy()
        sytm = orig_df['SYTM_01'].str.lower().str.strip("'")
        dt = pd.to_datetime(sytm, format='%d-%b-%Y %H:%M:%S.%f')

        # Create a DataFrame with Temperature as the variable and DateTime as the index.
        df = pd.DataFrame({'Temperature': temp}, index=dt)

        # Convert datetime to numeric for lasso selection
        xy = np.column_stack([mdates.date2num(df.index), df['Temperature']])

        # Store multiple selection groups
        selection_groups = []

        # Plot the temperature time series
        fig, ax = plt.subplots(figsize=(10, 6))
        pts = ax.scatter(df.index, df['Temperature'], s=10, color='blue')
        plt.title(f'[{idx}/{len(mtr_files)}] Time Series Data- {mtr_file}')
        plt.xlabel('Date Time')
        plt.ylabel('Temperature')
        plt.grid(True)

        # --- Buttons (tuple positions required in Python 3.13+) ---
        ax_continue = plt.axes((0.70, 0.01, 0.12, 0.06))
        ax_exit = plt.axes((0.85, 0.01, 0.12, 0.06))

        btn_continue = Button(ax_continue, "Continue")
        btn_exit = Button(ax_exit, "Exit")

        # --- Optional visual tweaks ---
        btn_continue.color = "lightgreen"
        btn_exit.color = "salmon"
        btn_continue.hovercolor = "limegreen"
        btn_exit.hovercolor = "red"

        def click_continue(event):
            plt.close(fig)  # close figure and continue

        def click_exit(event):
            global exit_requested
            exit_requested = True
            plt.close(fig)  # close figure and stop

        btn_continue.on_clicked(click_continue)
        btn_exit.on_clicked(click_exit)

        # Lasso callback
        def onselect(verts):
            path = Path(verts)
            selected_indices = np.nonzero(path.contains_points(xy))[0]
            selected_points = xy[selected_indices]
            ax.scatter(mdates.num2date(selected_points[:, 0]), selected_points[:, 1], color='red', s=20)
            plt.draw()

            # Store selected points
            selected_dt = mdates.num2date(selected_points[:, 0])
            selected_temp = selected_points[:, 1]
            selected_df = pd.DataFrame({'DateTime': selected_dt, 'Temperature': selected_temp, 'idx': selected_indices})
            selection_groups.append(selected_df)

        # Activate lasso
        lasso = LassoSelector(ax, onselect)

        plt.show()

        indices_to_flag = np.array([], dtype=int)
        indices_to_flag_as_bad = np.array([], dtype=int)

        # After closing the plot, you can access all selected points
        if selection_groups:
            for group in selection_groups:
                indices_to_flag = group['idx'].to_numpy()

                # # Determine the range of indices in indices_to_flag
                min_idx = min(indices_to_flag)
                max_idx = max(indices_to_flag)

                # Get all indices in the DataFrame
                all_indices = orig_df.index.tolist()

                # Find indices within the range that are not already flagged
                additional_indices = [i for i in all_indices if i not in indices_to_flag and min_idx <= i <= max_idx]

                # Append safely using np.concatenate
                indices_to_flag = np.concatenate((indices_to_flag, np.array(additional_indices, dtype=int)))

                orig_df.loc[indices_to_flag, 'QTE90_01'] = 4

                indices_to_flag_as_bad = np.append(indices_to_flag_as_bad, indices_to_flag)
        else:
            print("No points were selected.")

        orig_df.loc[~orig_df.index.isin(indices_to_flag_as_bad), 'QTE90_01'] = 1

        # Output revised ODF
        mtr.add_history()
        mtr.add_to_history(f'ADD QUALITY FLAG AND PERFORM VISUAL QC BY {qc_operator.upper()}')

        mtr.update_odf()
        file_spec = mtr.generate_file_spec()
        mtr.file_specification = file_spec

        print(f"Writing file {idx} of {len(mtr_files)}: {mtr_file} after QC...please wait.")
        out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
        mtr.write_odf(str(out_file), version=2.0)

        print(f"✔ QC completed for [{idx}/{len(mtr_files)}]: {mtr_file}")
        print(f"    → Saved [{idx}/{len(mtr_files)}]: {out_file}")
    
    if idx == len(mtr_files):
        print(f"🎉 QC process completed for all {len(mtr_files)} files.")
        batch_result_container["finished"] = True
    else:
        print(f"⚠️ QC process was interrupted before completion of {idx} of {len(mtr_files)} files.")
        batch_result_container["finished"] = False
    
    return batch_result_container
  

def main_select_inputs():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    select_inputs = select_metadata_file_and_data_folder.SubWindowOne()
    select_inputs.show()

    result_container = {"finished": False, "input": None, "output": None, "operator": None}

    def on_accept():
        operator = select_inputs.qc_name.strip()
        input_path = select_inputs.input_data_folder
        output_path = select_inputs.output_data_folder

        if not operator or not input_path or not output_path:
            print("❌ Missing required fields.")
            return

        result_container["operator"] = operator
        result_container["input"] = input_path
        result_container["output"] = output_path
        result_container["finished"] = True

        # select_inputs.hide()
        # app.quit()

    def on_reject():
        print("❌ QC cancelled by user.")
        #app.quit()
        result_container["finished"] = False

    select_inputs.buttonBox.accepted.connect(on_accept)
    select_inputs.buttonBox.rejected.connect(on_reject)

    app.exec()

    if result_container["finished"]:
        return (
            result_container["input"],
            result_container["output"],
            result_container["operator"],
        )
    else:
        return None, None, None


def reload_main():    
    QApplication.quit()
    #sys.exit(0)
    main()
    

def main():    
    input_path, output_path, operator = main_select_inputs()
    if input_path and output_path and operator:
        returnM = run_qc_thermograph_data(input_path, output_path, operator)
        if returnM["finished"]:
            QApplication.quit()
            #sys.exit(0)
            reload_main()
    else:
        print("💤 Program exited with no QC action.") 



if __name__ == "__main__":
    main()

















# def main():

#     # input_path = 'C:/DFO-MPO/DEV/MTR/999_Test/'
#     input_path = 'C:/Users/ROYPR/Desktop/DFO-ODIS-SSPPI/Python_Development/MTR_Data/minilog/Step_1_Create_ODF'

#     wildcard = '*.ODF'
#     qc_operator='Test Operator'


#     # output_path = 'C:/DFO-MPO/DEV/MTR/999_Test/Step_1_Create_ODF/'
#     output_path = 'C:/Users/ROYPR/Desktop/DFO-ODIS-SSPPI/Python_Development/MTR_Data/minilog'

#     qc_thermograph_data(input_path, wildcard, output_path, qc_operator)


# if __name__ == main():
    
#     main()