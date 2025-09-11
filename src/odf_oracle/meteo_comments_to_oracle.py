from odf_toolbox.odfhdr import OdfHeader
from icecream import ic

def meteo_comments_to_oracle(odfobj: OdfHeader, connection, infile):
    """
    Load the meteo header comments into Oracle.

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

        print('No METEO_HEADER Comments to load into Oracle.')

    else:

        # Create a cursor to the open connection.
        with connection.cursor() as cursor:

            # Loop through the Meteo_Header.Meteo_Comments.
            meteo_comments = odfobj.meteo_header.meteo_comments

            if type(meteo_comments) is list:

                for j, meteo_comment in enumerate(meteo_comments):

                    # Execute the Insert SQL statement.
                    cursor.execute(
                        "INSERT INTO ODF_METEO_COMMENTS (METEO_COMMENT_NUMBER, "
                        "METEO_COMMENT, ODF_FILENAME) "
                        "VALUES (:comment_no, :comments, :filename)",
                        {
                            'comment_no': j,
                            'comments': meteo_comment,
                            'filename': infile
                        }
                        )
                    connection.commit()

            elif type(meteo_comments) is str:

                meteo_comments.strip("\' ")

                # Execute the Insert SQL statement.
                cursor.execute(
                    "INSERT INTO ODF_METEO_COMMENTS (METEO_COMMENT_NUMBER, METEO_COMMENT, ODF_FILENAME) VALUES (:comment_no, :comments, :filename)",
                    {
                        'comment_no': 1,
                        'comments': meteo_comments,
                        'filename': infile
                    }
                )
                connection.commit()

            print('Meteo_Header.Meteo_Comments successfully loaded into Oracle.')
