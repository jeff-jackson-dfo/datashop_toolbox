import glob
import os
import sys

from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.validated_base import get_current_date_time

from PyQt6.QtWidgets import (
    QApplication
)
from datashop_toolbox import select_metadata_file_and_data_folder

# Create the GUI to select the metadata file and data folder
app = QApplication(sys.argv)
select_file_folder = select_metadata_file_and_data_folder.MainWindow()
select_file_folder.show()
app.exec()

if select_file_folder.result != "accept":
    print('\n****  Operation cancelled by user, exiting program.  ****\n')
    exit()

if select_file_folder.metadata_file == '' or select_file_folder.data_folder == '':
    print('\n****  Improper selections made, exiting program.  ****\n')
    exit()
else:
    metadata_file_path = select_file_folder.metadata_file
    data_folder_path = select_file_folder.data_folder

# Get the operator's name so it is identified in the history header.
if select_file_folder.line_edit_text == '':
    operator = input('Please enter the name of the analyst performing the data processing: ')
else:
    operator = select_file_folder.line_edit_text

# Change to folder containing files to be modified
os.chdir(data_folder_path)

# Find all CSV files in the current directory.
files = glob.glob('*.CSV')

# Check if no data files were found.
if files == []:
    print(f"****  No data files found in selected folder {data_folder_path}  ****\n")
else:
    # Create the required subfolder, if necessary
    if not os.path.isdir(os.path.join(data_folder_path, 'Step_1_Create_ODF')):
        os.mkdir('Step_1_Create_ODF')
    odf_path = os.path.join(data_folder_path, 'Step_1_Create_ODF')

# Loop through the CSV files to generate an ODF file for each.
for file_name in files:

    print()
    print('#######################################################################')
    print(f'Processing MTR file: {file_name}')
    print('#######################################################################')
    print()

    mtr_path = os.path.join(data_folder_path, file_name)

    print(f'\nProcessing MTR raw file: {mtr_path}\n')

    mtr = ThermographHeader()

    # Read the MTR file into a DataFrame
    mydict = mtr.read_mtr(mtr_path)
    df = mydict['df']
    inst_model = mydict['inst_model']
    gauge = mydict['gauge']
    # time.sleep(4.0) # Pause for 4 seconds

    print(f'\nProcessing metadata file: {metadata_file_path}\n')

    meta = mtr.read_metadata(metadata_file_path, 'fsrs')

    # Subset "meta" to only include the rows for the gauge of interest.
    meta = meta[meta['gauge'] == int(gauge)]
    print(meta)
    print('\n')

    mtr.cruise_header.country_institute_code = 1899
    cruise_year = df['date'].to_string(index=False).split('-')[0]
    cruise_number = f'BCD{cruise_year}603'
    mtr.cruise_header.cruise_number = cruise_number
    start_date = f"{mtr.start_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
    mtr.cruise_header.start_date = start_date
    end_date = f"{mtr.end_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
    mtr.cruise_header.end_date = end_date
    mtr.cruise_header.organization = 'FSRS'
    mtr.cruise_header.chief_scientist = 'Shannon Scott-Tibbetts'
    mtr.cruise_header.cruise_description = 'Fishermen and Scientists Research Society'
    
    mtr.event_header.data_type = 'MTR'
    mtr.event_header.event_qualifier1 = gauge
    mtr.event_header.event_qualifier2 = str(mtr.sampling_interval(df))
    mtr.event_header.creation_date = get_current_date_time()
    mtr.event_header.orig_creation_date = get_current_date_time()
    mtr.event_header.start_date_time = mtr.start_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
    mtr.event_header.end_date_time = mtr.end_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
    lat = meta['latitude'].iloc[0]
    long = meta['longitude'].iloc[0]
    if lat < 0:
        lat = lat * -1
    if long > 0:
        long = long * -1
    mtr.event_header.initial_latitude = lat
    mtr.event_header.initial_longitude = long
    mtr.event_header.end_latitude = lat
    mtr.event_header.end_longitude = long
    depth = meta['depth']
    mtr.event_header.min_depth = min(depth)
    mtr.event_header.max_depth = max(depth)
    mtr.event_header.event_number = str(meta['vessel_code'].iloc[0])
    mtr.event_header.sampling_interval = float(mtr.sampling_interval(df))
    
    if 'minilog' in inst_model.lower():
        mtr.instrument_header.instrument_type = 'MINILOG'
    mtr.instrument_header.model = inst_model
    mtr.instrument_header.serial_number = gauge
    mtr.instrument_header.description = 'Temperature data logger'

    history_header = HistoryHeader()
    history_header.creation_date = get_current_date_time()
    history_header.set_process(f'Initial file creation by {operator}')
    mtr.history_headers.append(history_header)

    new_df = mtr.create_sytm(df)

    mtr.populate_parameter_headers(new_df)

    for x, column in enumerate(new_df.columns):
        code = mtr.parameter_headers[x].code
        new_df.rename(columns={column: code}, inplace=True)

    file_spec = mtr.generate_file_spec()
    mtr.file_specification = file_spec

    mtr.update_odf()

    odf_file_path = os.path.join(odf_path, file_spec + '.ODF')
    mtr.write_odf(odf_file_path, version = 2.0)

    # Reset the shared log list
    BaseHeader.reset_log_list()    
