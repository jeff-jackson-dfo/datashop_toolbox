from odf_toolbox.odfhdr import OdfHeader

def quality_comments_to_oracle(odfobj: OdfHeader, connection, infile: str):
    """
    Load the ODF object's quality header comments into Oracle.
  
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

    if odfobj.quality_header is None:

        print('No QUALITY_HEADER Comments were present to load into Oracle.')

    else:

        # Create a cursor to the open connection.
        with connection.cursor() as cursor:

            # Loop through the Quality_Header.Quality_Comments.
            quality_comments = odfobj.quality_header.quality_comments
            
            if type(quality_comments) is list:

                for q, quality_comment in enumerate(quality_comments):

                    # Execute the Insert SQL statement.
                    cursor.execute(
                        "INSERT INTO ODF_QUALITY_COMMENTS (QUALITY_COMMENT_NUMBER, "
                        "QUALITY_COMMENT, ODF_FILENAME) VALUES "
                        "(:comment_no, :comments, :fname)",
                        {
                            'comment_no': q,
                            'comments': quality_comment,
                            'fname': infile
                        }
                        )
                    connection.commit()

            elif type(quality_comments) is str:
                
                # Execute the Insert SQL statement.
                cursor.execute(
                    "INSERT INTO ODF_QUALITY_COMMENTS (QUALITY_COMMENT_NUMBER, "
                    "QUALITY_COMMENT, ODF_FILENAME) VALUES ("
                    ":comment_no, :comments, :fname)",
                    {
                        'comment_no': 1,
                        'comments': quality_comments,
                        'fname': infile
                    }
                    )
                connection.commit()

            print('Quality_Header.Quality_Comments successfully loaded into Oracle.')
