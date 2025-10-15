import glob
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
import matplotlib.dates as mdates
import numpy as np
import os
import pandas as pd
import pathlib

from datashop_toolbox.thermograph import ThermographHeader


def qc_thermograph_data(in_folder_path: str, wildcard: str, out_folder_path: str):

    cwd = os.getcwd()

    # Find all files selected using the wildcard in the provided input directory.
    os.chdir(in_folder_path)
    mtr_files = glob.glob(wildcard)

    os.chdir(cwd)

    for mtr_file in mtr_files:

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
        plt.title('Time Series Data')
        plt.xlabel('Date Time')
        plt.ylabel('Temperature')
        plt.grid(True)

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
        mtr.update_odf()
        file_spec = mtr.generate_file_spec()
        mtr.file_specification = file_spec
        qfs_out_file = f"{file_spec}_QFs.ODF"
        mtr.write_odf(out_folder_path + qfs_out_file, version = 2.0)


def main():

    input_path = 'C:/DFO-MPO/DEV/MTR/999_Test/'
    wildcard = '*.ODF'
    output_path = 'C:/DFO-MPO/DEV/MTR/999_Test/Step_1_Create_ODF/'
    qc_thermograph_data(input_path, wildcard, output_path)


if __name__ == main():
    
    main()