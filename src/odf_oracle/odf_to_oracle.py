import os
import glob
from dotenv import load_dotenv

from odf_toolbox.odfhdr import OdfHeader
from odf_oracle.database_connection_pool import get_database_pool
from odf_oracle import cruise_event_to_oracle
from odf_oracle import event_comments_to_oracle
from odf_oracle import meteo_to_oracle
from odf_oracle import meteo_comments_to_oracle
from odf_oracle import instrument_to_oracle
from odf_oracle import quality_to_oracle
from odf_oracle import quality_tests_to_oracle
from odf_oracle import quality_comments_to_oracle
from odf_oracle import history_to_oracle
from odf_oracle import compass_cal_to_oracle
from odf_oracle import polynomial_cal_to_oracle
from odf_oracle import general_cal_to_oracle
from odf_oracle import data_to_oracle


def odf_to_oracle(wildcard: str, user: str, password: str, oracle_host: str,
                  oracle_service_name: str, mypath: str) -> None:
    """
    Read ODF files and load them into the ODF_ARCHIVE Oracle database.

    Parameters
    ----------
    wildcard: str 
      used to identify specific ODF files in the supplied directory path.
    user: str
      The username for Oracle account.
    password: str
      The password for Oracle account.
    oracle_host: str
      Server on which Oracle database exists.
    oracle_service_name: str
      Oracle database service name.
    mypath: str
      Directory where ODF files to be loaded reside.

    Returns
    -------
    None
    """

    # Acquire a connection from the pool (will always have the new date and
    # timestamp formats).
    pool = get_database_pool()
    connection = pool.acquire()

    print(f'\nAttempting to load the ODF files in the folder << {mypath} >> '\
          'into ODF_ARCHIVE Oracle database')
    
    os.chdir(mypath)

    # Find all ODF files in the current directory using the input wildcard.
    os.listdir(path = mypath)
    filelist = glob.glob(wildcard)

    if len(filelist) == 0:
        print('No files found.')

    # Loop through the list of ODF files.
    for filename in filelist:
    
      print(f'\nWorking on loading ODF file << {filename} >>:')

      odf = OdfHeader()

      # Read the ODF file
      odf.read_odf(filename)

      # Change all null values to empty strings.
      df = odf.null2empty(odf.data.data_frame)
      odf.data.data_frame = df
      
      # # Load the Cruise_Header and Event_Header information into Oracle.
      odf_file = cruise_event_to_oracle(odf, connection, filename)

      # # Load the Event_Header.Event_Comments into Oracle.
      event_comments_to_oracle(odf, connection, odf_file)

      # # Load the Meteo_Header information into Oracle.
      meteo_to_oracle(odf, connection, odf_file)

      # # Load the Meteo_Header.Meteo_Comments into Oracle.
      meteo_comments_to_oracle(odf, connection, odf_file)

      # # Load the Quality_Header information into Oracle.
      quality_to_oracle(odf, connection, odf_file)

      # # Load the Quality_Header.Quality_Tests into Oracle.
      quality_tests_to_oracle(odf, connection, odf_file)

      # # Load the Quality_Header.Quality_Comments into Oracle.
      quality_comments_to_oracle(odf, connection, odf_file)

      # # Load the Instrument_Header information into Oracle.
      instrument_to_oracle(odf, connection, odf_file)

      # # Load the General_Cal_Header information into Oracle.
      general_cal_to_oracle(odf, connection, odf_file)

      # # Load the Polynomial_Cal_Header information into Oracle.
      polynomial_cal_to_oracle(odf, connection, odf_file)

      # # Load the Compass_Cal_Header information into Oracle.
      compass_cal_to_oracle(odf, connection, odf_file)

      # # Load the History_Header information into Oracle.
      history_to_oracle(odf, connection, odf_file)

      # # Load the Data into Oracle.
      data_to_oracle(odf, connection, odf_file)

      print(f'\n<< {filename} >> was successfully loaded into Oracle.\n')

    pool.drop(connection)
    pool.close()


def main():

  load_dotenv(r'C:\Users\JacksonJ\OneDrive - DFO-MPO\Documents\.env')
  username = os.environ.get("ODF_ARCHIVE_USERNAME")
  userpwd = os.environ.get("ODF_ARCHIVE_PASSWORD")
  oracle_host = os.environ.get("ORACLE_HOST")
  oracle_service_name = os.environ.get("ORACLE_SERVICE_NAME")
  
  odf_to_oracle(wildcard = '*.ODF', 
                user = username, 
                password = userpwd, 
                oracle_host = oracle_host,
                oracle_service_name = oracle_service_name,
                mypath = r'C:\\DEV\\LOAD_TO_ODF_ARCHIVE\\')
                # mypath = r'C:\\DEV\\TEMP\\TEST\\')
                # mypath = r'C:\\DEV\\GitHub\\odf_toolbox\\tests\\LOAD_TO_ORACLE\\')

if __name__ == "__main__":
  main()
