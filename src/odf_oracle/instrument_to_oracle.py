from odf_toolbox.odfhdr import OdfHeader

def instrument_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None:
    """
    Load the ODF object's instrument header metadata into Oracle.

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

    # Check to see if the ODF structure contains an Instrument_Header.
    if odfobj.instrument_header is None:

        print('No Instrument_Header was present to load into Oracle.')

    else:

        # Create a cursor to the open connection.
        with connection.cursor() as cursor:

            # Execute the Insert SQL statement.
            cursor.execute(
                "INSERT INTO ODF_INSTRUMENT (INST_TYPE, INST_MODEL, SERIAL_NUMBER, "
                "DESCRIPTION, ODF_FILENAME) VALUES ("
                ":itype, :imodel, :snum, :description, :fname)",
                {
                    'itype': odfobj.instrument_header.instrument_type,
                    'imodel': odfobj.instrument_header.model,
                    'snum': odfobj.instrument_header.serial_number,
                    'description': odfobj.instrument_header.description,
                    'fname': infile
                }
            )

            # Commit the changes to the database.
            connection.commit()

            print('Instrument_Header successfully loaded into Oracle.')
