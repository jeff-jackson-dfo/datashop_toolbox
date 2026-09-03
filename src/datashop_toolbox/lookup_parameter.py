import sqlite3
from importlib import resources
from typing import TypedDict

from odf_oracle.database_connection_pool import get_database_pool


class ParamInfo(TypedDict):
    """Metadata describing an ODF parameter code.

    Attributes:
        description: Descriptive name of the parameter.
        units: Units in which the parameter is recorded.
        print_field_width: Field width used when printing the
            parameter.
        print_decimal_places: Number of decimal places used when
            printing the parameter.
    """

    description: str
    units: str
    print_field_width: int
    print_decimal_places: int


def lookup_parameter(database: str, parameter: str) -> ParamInfo:
    """Get the parameter information from the a database.

    Args:
        database: Which database backend to query — ``"oracle"`` to
            use the ODF Oracle connection pool, or ``"sqlite"`` to
            query the packaged ``parameters.db`` SQLite database. Any
            other value returns the default "Unknown" info unchanged.
        parameter: Parameter code to look up, e.g. ``"TEMP"``.

    Returns:
        A :class:`ParamInfo` dict with the parameter's description,
        units, and print formatting. Fields default to ``"Unknown"``
        or ``0`` if the parameter is not found or ``database`` is not
        recognized.
    """

    parameter_info: ParamInfo = {
        "description": "Unknown",
        "units": "Unknown",
        "print_field_width": 0,
        "print_decimal_places": 0,
    }

    match database:
        case "oracle":
            # Acquire a connection from the pool (will always have the new date and timestamp formats).
            pool = get_database_pool()
            connection = pool.acquire()

            sql_statement = f"select * from ODF_PARAMETERS where code = '{parameter}'"
            with connection.cursor() as cursor:
                for row in cursor.execute(sql_statement):
                    result = row

                column_names = [desc[0].lower() for desc in cursor.description]
                pinfo = dict(zip(column_names, result, strict=False))
                parameter_info["description"] = pinfo.get("description", "Unknown")
                parameter_info["units"] = pinfo.get("units", "Unknown")
                parameter_info["print_field_width"] = pinfo.get("print_field_width", 0)
                parameter_info["print_decimal_places"] = pinfo.get("print_decimal_places", 0)

            # Release the connection back to the pool and close the pool.
            pool.drop(connection)
            pool.close()

        case "sqlite":
            # Get a safe, real filesystem path to the packaged parameters.db
            with resources.as_file(
                resources.files("datashop_toolbox.database").joinpath("parameters.db")
            ) as db_path:
                with sqlite3.connect(db_path) as conn:
                    sql_statement = f"select * from ODF_PARAMETERS where code = '{parameter}'"

                    cursor = conn.execute(sql_statement)

                    for row in cursor:
                        result = row

                    column_names = [desc[0].lower() for desc in cursor.description]
                    pinfo = dict(zip(column_names, result, strict=False))
                    parameter_info["description"] = pinfo.get("description", "Unknown")
                    parameter_info["units"] = pinfo.get("units", "Unknown")
                    parameter_info["print_field_width"] = pinfo.get("print_field_width", 0)
                    parameter_info["print_decimal_places"] = pinfo.get("print_decimal_places", 0)

    return parameter_info


def main():

    # Get parameter information for TEMP from the ODF database.
    parameter = "TEMP"
    # pinfo = lookup_parameter('oracle', parameter)
    pinfo = lookup_parameter("sqlite", parameter)
    print(pinfo)


if __name__ == "__main__":
    main()
