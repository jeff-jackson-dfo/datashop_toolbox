from odf_toolbox.odfhdr import OdfHeader
from icecream import ic

def event_comments_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None:
    """
    Load the ODF object's event header comments into Oracle.

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

    # Create a cursor to the open connection.
    with connection.cursor() as cursor:

        # Get the Event_Comments.
        event_comments = odfobj.event_header.event_comments
        
        if type(event_comments) is list:

            # Loop through the Event_Comments.
            for event_comment in event_comments:
                # Execute the Insert SQL statement.
                cursor.execute(
                    "INSERT INTO ODF_EVENT_COMMENTS (EVENT_COMMENTS, "
                    "ODF_FILENAME) VALUES (:comments, :filename)",
                    {
                        'comments': event_comment,
                        'filename': infile
                    }
                    )
                connection.commit()

        elif type(event_comments) is str:
            
            # Execute the Insert SQL statement.
            cursor.execute("INSERT INTO ODF_EVENT_COMMENTS (EVENT_COMMENTS, "
            "ODF_FILENAME) VALUES (:comments, :filename)",
                        {
                            'comments': event_comments,
                            'filename': infile
                        }
                        )
            connection.commit()

        print('Event_Header.Event_Comments successfully loaded into Oracle.')
