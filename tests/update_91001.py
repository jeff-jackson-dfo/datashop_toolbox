import glob
import os
from odf_toolbox.basehdr import BaseHeader
from odf_toolbox.odfhdr import OdfHeader
from odf_toolbox import odfutils

"""
UPDATE_91001: function to update ODF files for cruise 91001
with the correct metadata.

  ODSToolbox Version: 2.0

  Last Updated: 14-FEB-2025

  Source:
      Ocean Data and Information Services,
      Bedford Institute of Oceanography, DFO, Canada.
      DataServicesDonnees@dfo-mpo.gc.ca

  Description:
      update_91001 updates the 91001 ODF files.

  Usage:
      update_91001(wildcard)

  Input:
      wildcard : a wildcard to identify the file or files to process.

  Output:
      The updated version of the input ODF files.

  Example:
      update_91001('*.ODF')

  See also

  Copyright 2025, DFO, Bedford Institute of Oceanography, Canada.
  All Rights Reserved.

------------------------------------------------------------------------
  Author: Jeff Jackson
  Date: 10-FEB-2025

  Report any bugs to DataServicesDonnees@dfo-mpo.gc.ca

  Updates:

    Jeff Jackson (10-FEB-2025)
    - Ini version.

    Prodyut Roy (18-FEB-2025)
    - Added new lines.

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
files = glob.glob('CTD_91001*')

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

    odf = OdfHeader()

    # Read the ODF file
    odf.read_odf(file_name)

    # print(odf.event_header.print_object())

    # Add a new History Header to record the modifications that are made.
    odf.add_history()
    odf.add_to_log(f'{user} made the following modifications to this file:')

    param_list = odf.data.parameter_list
    new_param_list = ['PRES_01', 'TEMP_01', 'CRAT_01', 'PSAL_01', 'NETR_01', 'FLOR_01', 'OTMP_01', 'OPPR_01', 'DOXY_01']
    
    odf = odf.fix_parameter_codes(new_param_list)

    # min_depth = gsw.z_from_p(min(A.Data.PRES), A.Event_Header.Initial_Latitude)
    # max_depth = gsw.z_from_p(max(A.Data.PRES), A.Event_Header.Initial_Latitude)

    # Update Cruise_Header
    odf.cruise_header.organization= 'DFO BIO'
    odf.cruise_header.chief_scientist = 'GLEN HARRISON'
    odf.cruise_header.platform = 'HUDSON'
    odf.cruise_header.start_date = '19-SEP-2014 00:00:00.00'
    odf.cruise_header.end_date = '08-OCT-2014 00:00:00.00'
    odf.cruise_header.cruise_name = 'SCOTIAN SHELF AND SLOPE'
    odf.cruise_header.cruise_description = 'ATLANTIC ZONE MONITORING PROGRAM (AZMP)'

    # Update Event_Header
    odf.event_header.set_number = '999'
    odf.event_header.set_event_comment('Location Antarctica')
    odf.event_header.creation_date = odfutils.check_datetime(odf.event_header.creation_date)
    odf.event_header.orig_creation_date = odfutils.check_datetime(odf.event_header.orig_creation_date)
    odf.event_header.start_date_time = odfutils.check_datetime(odf.event_header.start_date_time)
    odf.event_header.end_date_time = odfutils.check_datetime(odf.event_header.end_date_time)

    odf.instrument_header.model = 'SBE 911'

    # Update the Polynomial_Cal_Headers
    odf.log_message('The PARAMETER_CODE field was not present in the POLYNOMIAL_CAL_HEADERS so it was added to replace the PARAMETER_NAME field that was present.')

    # odf.update_parameter('SYTM_01', 'units', 'GMT')   
    # odf.update_parameter('SYTM_01', 'print_field_width', 45)

    # Make sure that the event numbers are 3-digit strings.
    # event_str = odf.event_header.get_event_number()
    # event_str = event_str.strip("\' ")
    # event_int = int(event_str)
    # if len(event_str) < 3:
    #     odf.event_header.event_number(f"{event_int:03}")

    # Add history comments to document that the Slope and Offset values for the primary and secondary conductivity
    # channels were updated from their original acquisition values prior to reprocessing the CTD data files.
    # odf.add_to_log(
    #     'The primary conductivity (3561) and temperature (5081) sensors (pair 1) were replaced with sensors'
    #     ' (1874) and (2303) (pair 2) after the CTD collided with the bottom prior to event 136.')
    # odf.add_to_log('The primary conductivity [3561] calibration coefficient "Offset" was changed from its original '
    #                    'value [0.0] to [-0.00066] for sensor pair 1.')
    # odf.add_to_log('The primary conductivity [3561] calibration coefficient "Slope" was changed from its original '
    #                    'value [1.0] to [1.000039] for sensor pair 1.')
    # odf.add_to_log('The primary conductivity [1874] calibration coefficient "Offset" remained unchanged from its '
    #                    'original value [0.0] to [0.00048] for sensor pair 2.')
    # odf.add_to_log('The primary conductivity [1874] calibration coefficient "Slope" remained unchanged from its '
    #                    'original value [1.0] to [1.000016] for sensor pair 2.')
    # odf.add_to_log('The secondary conductivity [3562] calibration coefficient "Offset" was changed from its '
    #                    'original value [0.0] to [-0.00132].')
    # odf.add_to_log('The secondary conductivity [3562] calibration coefficient "Slope" was changed from its '
    #                    'original value [1.0] to [1.000272].')

    # Add history comments to document that the Soc values for the primary and secondary oxygen channels were updated
    # from their original acquisition values prior to reprocessing the CTD data files.
    # odf.add_to_log('The primary oxygen [0133] calibration coefficient "Soc" was changed from its original value '
    #                    'of [0.3903] to [0.4054].')
    # odf.add_to_log('The secondary oxygen [1588] calibration coefficient "Soc" was changed from its original value '
    #                    'of [0.5347] to [0.4523].')

    # Access the log records stored in the custom handler and add the logged changes to the History_Header.
    # log_records = odfutils.list_handler.log_records
    # for record in log_records:
    #     odf.add_to_log(record)

    # Update the Record_Header and other headers to revise the metadata after modifications have been performed.
    odf.update_odf()
    
    odf_file_text = odf.print_object(file_version = 2.0)
    # print(odf_file_text)

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

# Run the following script on the MATLAB command line once the
# update_HUD2014030.m script has finished. It creates new files with the
# quality flag fields after running the files through the GTSPP quality
# control checks.
# add_qfs_to_odf('*.ODF', 'C:\DEV\Data\2014\HUD2014030\CTD\DATASHOP_PROCESSING\Step_3_Update_Metadata',
# 'C:\DEV\Data\2014\HUD2014030\CTD\DATASHOP_PROCESSING\Step_4_Run_Automated_Checks', false, false)
