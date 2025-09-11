from odf_toolbox.odfhdr import OdfHeader

def meteo_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None:
    """
    Load the meteo header metadata from the ODF object into Oracle.

    Parameters
    ----------
    odfobj: OdfHeader class object
        An ODF object.
    connection: oracledb connection
        Oracle database connection object.
    infile: str
        ODF file currently being loaded into the database.

    Returns
    -------
    None
    """

    # Check to see if the ODF object contains an METEO_HEADER.
    if odfobj.meteo_header is None:

        print('No METEO_HEADER was present to load into Oracle.')

    else:

        # Create a cursor to the open connection.
        with connection.cursor() as cursor:

            # Execute the Insert SQL statement.
            cursor.execute(
                "INSERT INTO ODF_METEO (AIR_TEMPERATURE, ATMOSPHERIC_PRESSURE, "
                "WIND_SPEED, WIND_DIRECTION, SEA_STATE, "
                "CLOUD_COVER, ICE_THICKNESS, ODF_FILENAME) "
                "VALUES (:at, :ap, :ws, :wd, :ss, :cc, :ice, :fname)",
                {
                    'at': odfobj.meteo_header.air_temperature,
                    'ap': odfobj.meteo_header.atmospheric_pressure,
                    'ws': odfobj.meteo_header.wind_speed,
                    'wd': odfobj.meteo_header.wind_direction,
                    'ss': odfobj.meteo_header.sea_state,
                    'cc': odfobj.meteo_header.cloud_cover,
                    'ice': odfobj.meteo_header.ice_thickness,
                    'fname': infile
                }
                )

            # Commit the changes to the database.
            connection.commit()

            print('Meteo_Header successfully loaded into Oracle.')
