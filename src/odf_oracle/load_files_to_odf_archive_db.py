from dotenv import load_dotenv
import os
from odf_oracle.odf_to_oracle import odf_to_oracle

load_dotenv("C:\\Users\\JacksonJ\\OneDrive - DFO-MPO\\Documents\\.env")
username = str(os.environ.get("ODF_ARCHIVE_USERNAME"))
userpwd = str(os.environ.get("ODF_ARCHIVE_PASSWORD"))
oracle_host = str(os.environ.get("ORACLE_HOST"))
oracle_service_name = str(os.environ.get("ORACLE_SERVICE_NAME"))

odf_to_oracle(wildcard = '*.ODF', 
              user = username, 
              password = userpwd, 
              oracle_host = oracle_host, 
              oracle_service_name = oracle_service_name, 
              mypath = "C:\\DFO-MPO\\DEV\\LOAD_TO_ODF_ARCHIVE\\")
