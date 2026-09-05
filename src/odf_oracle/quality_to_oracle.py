from datashop_toolbox.odfhdr import OdfHeader
from odf_oracle.sytm_to_timestamp import sytm_to_timestamp


def quality_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None:
    """
    Load the ODF object's quality header information into Oracle.

    Args:
        odfobj: An ODF object.
        connection: Oracle database connection object.
        infile: ODF file currently being loaded into the database.
    """

    # Check to see if the ODF structure contains an QUALITY_HEADER.
    if odfobj.quality_header is None:
        print("No QUALITY_HEADER was present to load into Oracle.")

    else:
        # Create a cursor to the open connection.
        with connection.cursor() as cursor:
            # Get the quality date and time from the ODF object.
            qdate = odfobj.quality_header.quality_date

            # Execute the Insert SQL statement.
            cursor.execute(
                "INSERT INTO ODF_QUALITY (QUALITY_DATE, ODF_FILENAME) "
                "VALUES (TO_TIMESTAMP(:qdate, 'YYYY-MM-DD HH24:MI:SS.FF'), :fname)",
                {"qdate": sytm_to_timestamp(qdate, "datetime"), "fname": infile},
            )

            # Commit the changes to the database.
            connection.commit()

            print("Quality_Header successfully loaded into Oracle.")
