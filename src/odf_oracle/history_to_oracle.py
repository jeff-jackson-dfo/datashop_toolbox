from icecream import ic

from odf_toolbox.odfhdr import OdfHeader
from odf_oracle.sytm_to_timestamp import sytm_to_timestamp

def history_to_oracle(odfobj: OdfHeader, connection, infile: str):
    """
    Load the ODF object's history header metadata into Oracle.
  
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

    # Check to see if the ODF structure contains a History_Header.
    if not odfobj.history_headers:

        print('No History_Header was present to load into Oracle.')

    else:

        # Create a cursor to the open connection.
        with connection.cursor() as cursor:

            cursor.execute(
                "ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'"
                " NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'")

            # Loop through the HISTORY_HEADERs.
            for h, history_header in enumerate(odfobj.history_headers):

                # Loop through the HISTORY_HEADER's PROCESS lines.
                process_list = history_header.processes
                cdt = history_header.creation_date
                cdate = sytm_to_timestamp(cdt, 'datetime')
                hp = []
                if type(process_list) is list:
                    
                    for p in process_list:
                        hp.append((h, cdate, p, infile))

                    # Execute the Insert SQL statement and commit to the database.
                    cursor.prepare(
                        "INSERT INTO ODF_HISTORY (HIST_NUM, CREATION_DATE, "
                        "PROCESS, ODF_FILENAME) VALUES (:1, :2, :3, :4)")
                    cursor.executemany(None, hp)
                    connection.commit()

                elif type(process_list) is str:
                    
                    # Execute the Insert SQL statement.
                    cursor.execute(
                        "INSERT INTO ODF_HISTORY (HIST_NUM, CREATION_DATE, "
                        "PROCESS, ODF_FILENAME) VALUES (:hist_num, "
                        ":creation_date, :process, :filename)",
                        {
                            'hist_num': h,
                            'creation_date': cdate,
                            'process': process_list,
                            'filename': infile
                        }
                        )
                    
                    # Commit the changes to the database.
                    connection.commit()
                
            print('History_Headers successfully loaded into Oracle.')
