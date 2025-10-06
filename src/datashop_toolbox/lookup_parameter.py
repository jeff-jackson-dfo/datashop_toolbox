from odf_oracle.database_connection_pool import get_database_pool
import sqlite3
from typing import TypedDict
from pathlib import Path
from importlib.resources import files

class ParamInfo(TypedDict):
    description: str
    units: str
    print_field_width: int
    print_decimal_places: int

def lookup_parameter(database: str, parameter: str) -> ParamInfo:
    """ Get the parameter information from the a database."""

    parameter_info: ParamInfo = {"description": "Unknown", "units": "Unknown", "print_field_width": 0, "print_decimal_places": 0}
    
    match database:
        
        case 'oracle':
            # Acquire a connection from the pool (will always have the new date and timestamp formats).
            pool = get_database_pool()
            connection = pool.acquire()

            sql_statement = f"select * from ODF_PARAMETERS where code = '{parameter}'"
            with connection.cursor() as cursor:
                for row in cursor.execute(sql_statement):
                    result = row

                column_names = [desc[0].lower() for desc in cursor.description]
                pinfo = dict(zip(column_names, result))
                parameter_info["description"] = pinfo.get("description", "Unknown")
                parameter_info["units"] = pinfo.get("units", "Unknown")
                parameter_info["print_field_width"] = pinfo.get("print_field_width", 0)
                parameter_info["print_decimal_places"] = pinfo.get("print_decimal_places", 0)

            # Release the connection back to the pool and close the pool.
            pool.drop(connection)
            pool.close()

        case 'sqlite':

            db_path = Path(files("datashop_toolbox") / "database/parameters.db")
            print(db_path)
            with sqlite3.connect(db_path) as conn:

                sql_statement = f"select * from ODF_PARAMETERS where code = '{parameter}'"

                cursor = conn.execute(sql_statement)

                for row in cursor:
                    result = row

                column_names = [desc[0].lower() for desc in cursor.description]
                pinfo = dict(zip(column_names, result))
                parameter_info["description"] = pinfo.get("description", "Unknown")
                parameter_info["units"] = pinfo.get("units", "Unknown")
                parameter_info["print_field_width"] = pinfo.get("print_field_width", 0)
                parameter_info["print_decimal_places"] = pinfo.get("print_decimal_places", 0)

    return parameter_info


def main():

    # Get parameter information for TEMP from the ODF database.
    parameter = 'TEMP'
    # pinfo = lookup_parameter('oracle', parameter)
    pinfo = lookup_parameter('sqlite', parameter)
    print(pinfo)


if __name__ == '__main__':
    main()