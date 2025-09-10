import glob
from icecream import ic
import os
from odf_toolbox.basehdr import BaseHeader
from odf_toolbox.odfhdr import OdfHeader
from odf_toolbox import odfutils

"""
UPDATE_BCD2024669: function to update ODF files for cruise BCD2024669
with the correct metadata.

  ODSToolbox Version: 2.0

  Last Updated: 02-JUL-2025

  Source:
      Ocean Data and Information Services,
      Bedford Institute of Oceanography, DFO, Canada.
      DataServicesDonnees@dfo-mpo.gc.ca

  Description:
      update_BCD2024669 updates the BCD2024669 ODF files.

  Usage:
      update_BCD2024669(wildcard)

  Input:
      wildcard : a wildcard to identify the file or files to process.

  Output:
      The updated version of the input ODF files.

  Example:
      update_BCD2024669('*.ODF')

  See also

  Copyright 2025, DFO, Bedford Institute of Oceanography, Canada.
  All Rights Reserved.

------------------------------------------------------------------------
  Author: Jeff Jackson
  Date: 02-JUL-2025

  Report any bugs to DataServicesDonnees@dfo-mpo.gc.ca

  Updates:

    Jeff Jackson (02-JUL-2025)
    - Initial version.

------------------------------------------------------------------------
"""

# Change to the drive's root folder
os.chdir('\\')
drive = os.getcwd()

pathlist = ['DEV', 'Data', '2024', 'BCD2024669', 'CTD', 'DATASHOP_PROCESSING']

# Generate the top folder path
top_folder = os.path.join(drive, *pathlist)

path_to_orig = os.path.join(top_folder, 'Step_7_Visual_Inspection')
path_to_revised = os.path.join(top_folder, 'Date_Fixed')

# Change to folder containing files to be modified
os.chdir(path_to_orig)

# Find all ODF files in the current directory.
files = glob.glob('CTD_BCD2024669_00*')

# Query the user for his/her name so he/she may be identified in the
# history header as the responsible data quality control person.
# user = input('Please enter the name of the analyst performing this data processing: ')
user = 'Jeff Jackson'

# Loop through the list of ODF files and process both the DN and UP files.
# Iterate through the list of input files.
for file_name in files:

    print()
    print('#######################################################################')
    print('Processing ' + file_name)
    print('#######################################################################')
    print()

    # Create an OdfHeader object
    odf = OdfHeader()

    # Read in an ODF file to populate the OdfHeader object
    odf.read_odf(file_name)

    # Add a new History Header to record the modifications that are made.
    odf.add_history()
    odf.add_to_log(f'The following edits were performed by {user}.')

    # Get the event number from the EVENT_HEADER.
    event = int(odf.event_header.event_number)

    # Update Event_Header
    if event == 2:
        edt = odf.event_header.end_date_time
        idx = 1
        replacement = "6"
        ledt = list(edt)
        ledt[idx] = replacement
        res = ''.join(ledt)
        odf.event_header.end_date_time = res
        sytm = odf.data.data_frame['SYTM_01'].str.replace('07-MAR-2024', '06-MAR-2024')
        odf.data.data_frame['SYTM_01'] = sytm
    elif event == 4:
        idx = 1
        replacement = "2"
        sdt = odf.event_header.start_date_time
        edt = odf.event_header.end_date_time
        lsdt = list(sdt)
        ledt = list(edt)
        lsdt[idx] = replacement
        sres = ''.join(lsdt)
        odf.event_header.start_date_time = sres
        ledt[idx] = replacement
        eres = ''.join(ledt)
        odf.event_header.end_date_time = eres
        sytm = odf.data.data_frame['SYTM_01'].str.replace('03-MAY-2024', '02-MAY-2024')
        odf.data.data_frame['SYTM_01'] = sytm
    else:
        continue  # Skip any other events

    # Update the Record_Header and other headers to revise the metadata after modifications have been performed.
    odf.update_odf()
    
    # Update creation date
    creation_date =  odf.event_header.creation_date
    new_creation_date = odf.generate_creation_date()
    odf.event_header.creation_date = new_creation_date
    odf.event_header.log_event_message('creation_date', creation_date, new_creation_date)

    odf_file_text = odf.print_object(file_version = 2.0)

    os.chdir(path_to_revised)

    # Output a new version of the ODF file using the proper file name.
    out_file = odf.generate_file_spec() + '.ODF'
    print(os.getcwd() + "\\" + out_file)
    file1 = open(out_file, "w")
    file1.write(odf_file_text)
    file1.close()

    # Reset the shared log list
    BaseHeader.reset_log_list()

    os.chdir(path_to_orig)

os.chdir(top_folder)
