import os

import oracledb
from dotenv import load_dotenv


def init_session(connection, requested_tag):
    """Modify some settings of the Oracle connection.

    Args:
        connection: Oracle connection to configure, used as the pool's
            ``session_callback``.
        requested_tag: Unused; accepted for compatibility with
            ``oracledb``'s ``session_callback`` signature.
    """
    connection.current_schema = "ODF_ARCHIVE"
    with connection.cursor() as cursor:
        cursor.execute(
            "alter session set "
            "NLS_LANGUAGE = 'ENGLISH' "
            "NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI' "
            "NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'"
        )
    connection.commit()


def get_database_pool():
    """Create an Oracle connection pool for the ODF_ARCHIVE database.

    Reads the username, password, host, and service name from
    environment variables loaded from a fixed ``.env`` file path, and
    initializes the Oracle client before creating the pool.

    Returns:
        An ``oracledb`` connection pool with 1-5 connections,
        configured via :func:`init_session` on each new session.
    """

    load_dotenv(r"C:\Users\JacksonJ\OneDrive - DFO-MPO\Documents\.env")
    username = os.environ.get("ODF_ARCHIVE_USERNAME")
    userpwd = os.environ.get("ODF_ARCHIVE_PASSWORD")
    oracle_host = os.environ.get("ORACLE_HOST")
    oracle_service_name = os.environ.get("ORACLE_SERVICE_NAME")

    oracledb.init_oracle_client()

    pool = oracledb.create_pool(
        user=username,
        password=userpwd,
        host=oracle_host,
        port=1521,
        service_name=oracle_service_name,
        min=1,
        max=5,
        increment=1,
        session_callback=init_session,
    )

    return pool
