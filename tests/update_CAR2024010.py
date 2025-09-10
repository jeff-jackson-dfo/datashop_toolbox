import glob
from icecream import ic
import os
from odf_toolbox.basehdr import BaseHeader
from odf_toolbox.odfhdr import OdfHeader
from odf_toolbox import odfutils

"""
UPDATE_CAR2024010: function to update ODF files for cruise CAR2024010
with the correct metadata.

  ODSToolbox Version: 2.0

  Last Updated: 06-MAY-2025

  Source:
      Ocean Data and Information Services,
      Bedford Institute of Oceanography, DFO, Canada.
      DataServicesDonnees@dfo-mpo.gc.ca

  Description:
      update_CAR2024010 updates the CAR2024010 ODF files.

  Usage:
      update_CAR2024010(wildcard)

  Input:
      wildcard : a wildcard to identify the file or files to process.

  Output:
      The updated version of the input ODF files.

  Example:
      update_CAR2024010('*.ODF')

  See also

  Copyright 2025, DFO, Bedford Institute of Oceanography, Canada.
  All Rights Reserved.

------------------------------------------------------------------------
  Author: Jeff Jackson
  Date: 06-MAY-2025

  Report any bugs to DataServicesDonnees@dfo-mpo.gc.ca

  Updates:

    Jeff Jackson (06-MAY-2025)
    - Ini version.

------------------------------------------------------------------------
"""

# Change to the drive's root folder
os.chdir('\\')
drive = os.getcwd()

pathlist = ['DEV', 'GitHub', 'odf_toolbox', 'tests']

# Generate the top folder path
top_folder = os.path.join(drive, *pathlist)

path_to_orig = os.path.join(top_folder, 'ODF')
path_to_revised = os.path.join(top_folder, 'Step_1_Update_Metadata')

# Change to folder containing files to be modified
os.chdir(path_to_orig)

# Find all ODF files in the current directory.
files = glob.glob('D24010*')

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

    # Get the set number from the file name.
    setnum = int(file_name[6:9])

    # Update Cruise_Header
    cruise_number = odf.cruise_header.cruise_number
    odf.cruise_header.cruise_number = 'CAR2024010'
    odf.cruise_header.log_cruise_message('cruise_number', cruise_number, 'CAR2024010')
    organization = odf.cruise_header.organization
    odf.cruise_header.organization= 'DFO BIO'
    odf.cruise_header.log_cruise_message('organization', organization, 'DFO BIO')
    platform = odf.cruise_header.platform
    odf.cruise_header.platform = 'CAPT JACQUES CARTIER'
    odf.cruise_header.log_cruise_message('platform', platform, 'CAPT JACQUES CARTIER')
    start_date = odf.cruise_header.start_date
    odf.cruise_header.start_date = '24-JUN-2024 00:00:00.00'
    odf.cruise_header.log_cruise_message('start_date', start_date, '24-JUN-2024 00:00:00.00')
    end_date = odf.cruise_header.end_date
    odf.cruise_header.end_date = '06-AUG-2024 00:00:00.00'
    odf.cruise_header.log_cruise_message('end_date', end_date, '06-AUG-2024 00:00:00.00')
    cruise_name = odf.cruise_header.cruise_name
    odf.cruise_header.cruise_name = 'GEORGES BANK (NAFO AREA 4X)'
    odf.cruise_header.log_cruise_message('cruise_name', cruise_name, 'GEORGES BANK (NAFO AREA 4X)')
    cruise_description = odf.cruise_header.cruise_description
    odf.cruise_header.cruise_description = 'AZMP ECOSYSTEM TRAWL SURVEY'
    odf.cruise_header.log_cruise_message('cruise_description', cruise_description, 'AZMP ECOSYSTEM TRAWL SURVEY')

    if event == 2800:
        odf.event_header.event_number = '280'
        event = 280
        odf.event_header.log_event_message('2800', '280')

    chief_scientist = odf.cruise_header.chief_scientist
    if event <= 94 or event > 192:
        # Legs 1 and 3
        odf.cruise_header.chief_scientist = 'JAIME EMBERLEY'
        odf.cruise_header.log_cruise_message('chief_scientist', chief_scientist, 'JAIME EMBERLEY')
    elif event > 94 and event <= 192:
        # Leg 2
        odf.cruise_header.chief_scientist = 'RYAN MARTIN'
        odf.cruise_header.log_cruise_message('chief_scientist', chief_scientist, 'RYAN MARTIN')

    # Update Event_Header
    odf.event_header.creation_date = odfutils.check_datetime(odf.event_header.creation_date)
    odf.event_header.orig_creation_date = odfutils.check_datetime(odf.event_header.orig_creation_date)
    odf.event_header.start_date_time = odfutils.check_datetime(odf.event_header.start_date_time)
    odf.event_header.end_date_time = odfutils.check_datetime(odf.event_header.end_date_time)
    sampling_interval = odf.event_header.sampling_interval
    odf.event_header.sampling_interval = 0.5
    odf.event_header.log_event_message('sampling_interval', sampling_interval, '0.5')

    #% Extract the starting id from the first history header and replace the Event_Qualifier1 with this value.
    hh = odf.history_headers[0]
    for i, process in enumerate(hh.processes):
        id = process.find("ID_Start")
        if id != -1:
            toks = process.split(':')
            if len(toks) > 1:
                starting_id = toks[1].strip()
            else:
                starting_id = '000000'
            eq1 = odf.event_header.event_qualifier1
            odf.event_header.event_qualifier1 = starting_id
            odf.event_header.log_event_message('event_qualifier1', eq1, starting_id)

    # A SBE 25plus secured on a rosette frame was used to acquire the CTD  data for all events.
    odf.add_to_log('The conductivity sensor (3132) calibration coefficient "Offset" was changed from its original value [0.0] to [0.00044].')
    odf.add_to_log('The conductivity sensor (3132) calibration coefficient "Slope" was changed from its original value [1.0] to [0.999543].')
    odf.add_to_log('The oxygen sensor (1157) calibration coefficient "Soc" was changed from its original value of [0.5433] to [0.5681].')

    # Update the Record_Header and other headers to revise the metadata after modifications have been performed.
    odf.update_odf()
    
    # Update creation date
    creation_date =  odf.event_header.creation_date
    new_creation_date = odf.generate_creation_date()
    odf.event_header.creation_date = new_creation_date
    odf.event_header.log_event_message('creation_date', creation_date, new_creation_date)

    odf_file_text = odf.print_object(file_version = 2.0)

    os.chdir(path_to_revised)

    set_filename = f"CTD_{odf.cruise_header.cruise_number}_{setnum:03d}_{odf.event_header.event_qualifier1}_{odf.event_header.event_qualifier2}"
    odf.file_specification = set_filename

    # Output a new version of the ODF file using the proper file name.
    out_file = set_filename + '.ODF'
    print(os.getcwd() + "\\" + out_file)
    file1 = open(out_file, "w")
    file1.write(odf_file_text)
    file1.close()

    # Reset the shared log list
    BaseHeader.reset_log_list()

    os.chdir(path_to_orig)

os.chdir(top_folder)
