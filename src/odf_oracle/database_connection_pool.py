import oracledb
import os
from dotenv import load_dotenv

def init_session(connection, requested_tag):
    """Modify some settings of the Oracle connection."""
    connection.current_schema = 'ODF_ARCHIVE'
    with connection.cursor() as cursor:
        cursor.execute("alter session set "
        "NLS_LANGUAGE = 'ENGLISH' "
        "NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI' "
        "NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'")
    connection.commit()

def get_database_pool():

    load_dotenv(r'C:\Users\JacksonJ\OneDrive - DFO-MPO\Documents\.env')
    username = os.environ.get("ODF_ARCHIVE_USERNAME")
    userpwd = os.environ.get("ODF_ARCHIVE_PASSWORD")
    oracle_host = os.environ.get("ORACLE_HOST")
    oracle_service_name = os.environ.get("ORACLE_SERVICE_NAME")

    oracledb.init_oracle_client()

    pool = oracledb.create_pool(
                                user = username, 
                                password = userpwd, 
                                host = oracle_host, 
                                port = 1521,
                                service_name = oracle_service_name,
                                min = 1, 
                                max = 5, 
                                increment = 1,
                                session_callback = init_session
                                )
    
    return pool