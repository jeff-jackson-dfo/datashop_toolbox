import glob
import os
import posixpath
import sys
from PyQt6.QtWidgets import (
    QApplication
)

from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.validated_base import get_current_date_time
from datashop_toolbox import select_metadata_file_and_data_folder

# Create the GUI to select the metadata file and data folder
app = QApplication(sys.argv)
select_inputs = select_metadata_file_and_data_folder.MainWindow()
select_inputs.show()
app.exec()

if select_inputs.result != "accept":
    print('\n****  Operation cancelled by user, exiting program.  ****\n')
    exit()

if select_inputs.metadata_file == '' or select_inputs.data_folder == '':
    print('\n****  Improper selections made, exiting program.  ****\n')
    exit()
else:
    metadata_file_path = select_inputs.metadata_file
    data_folder_path = select_inputs.data_folder

# Get the operator's name so it is identified in the history header.
if select_inputs.line_edit_text == '':
    operator = input('Please enter the name of the analyst performing the data processing: ')
else:
    operator = select_inputs.line_edit_text

institution = select_inputs.institution.upper()
instrument = select_inputs.instrument.lower()

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
    odf_path = posixpath.join(data_folder_path, 'Step_1_Create_ODF')

# Loop through the CSV files to generate an ODF file for each.
for file_name in files:

    print()
    print('#######################################################################')
    print(f'Processing MTR file: {file_name}')
    print('#######################################################################')
    print()

    mtr_path = posixpath.join(data_folder_path, file_name)
    print(f'\nProcessing MTR raw file: {mtr_path}\n')

    mtr = ThermographHeader()

    history_header = HistoryHeader()
    history_header.creation_date = get_current_date_time()
    history_header.set_process(f'Initial file creation by {operator}')
    mtr.history_headers.append(history_header)

    mtr.process_thermograph(institution, instrument, metadata_file_path, mtr_path)

    file_spec = mtr.generate_file_spec()
    mtr.file_specification = file_spec

    mtr.update_odf()

    odf_file_path = posixpath.join(odf_path, file_spec + '.ODF')
    mtr.write_odf(odf_file_path, version = 2.0)

    # Reset the shared log list
    BaseHeader.reset_log_list() 
