from datashop_toolbox.generalhdr import GeneralCalHeader


def general_cal_comments_to_oracle(
    general_cal_header: GeneralCalHeader, connection, gg: int, filename: str
) -> None:
    """
    Load comments from a GENERAL_CAL_Header into Oracle.

    Args:
        general_cal_header: A general calibration header object.
        connection: Oracle database connection object.
        gg: Iterator identifying the order of the GENERAL_CAL_HEADERS
            in the ODF file.
        filename: The ODF file name.
    """

    # Create a cursor to the open connection.
    with connection.cursor() as cursor:
        # Loop through the General_Cal_Header.General_Cal_Equation.
        calibration_comments = general_cal_header.calibration_comments

        # Check to see if the GENERAL_CAL_HEADER contains any CALIBRATION_COMMENTS.
        if calibration_comments is None:
            print("No General_Cal_Header.Calibration_Comments were present to load into Oracle.")

        elif type(calibration_comments) is list:
            for comment_number, calibration_comment in enumerate(calibration_comments):
                # Execute the Insert SQL statement.
                cursor.execute(
                    "INSERT INTO ODF_GENERAL_CAL_COMMENTS "
                    "(GENERAL_CAL_HEADER_NUMBER, CALIBRATION_COMMENT_NUMBER, "
                    "CALIBRATION_COMMENT, ODF_FILENAME)"
                    " VALUES (:calibration_comments_no, :comment_no, "
                    ":comments, :fname)",
                    {
                        "calibration_comments_no": gg,
                        "comment_no": comment_number,
                        "comments": calibration_comment,
                        "fname": filename,
                    },
                )

                connection.commit()

        elif type(calibration_comments) is str:
            # Execute the Insert SQL statement.
            cursor.execute(
                "INSERT INTO ODF_GENERAL_CAL_COMMENTS "
                "(GENERAL_CAL_HEADER_NUMBER, CALIBRATION_COMMENT_NUMBER, "
                "CALIBRATION_COMMENT, ODF_FILENAME) "
                "VALUES (:calibration_comments_no, :comment_no, "
                ":comments, :fname)",
                {
                    "calibration_comments_no": gg,
                    "comment_no": 1,
                    "comments": calibration_comments,
                    "fname": filename,
                },
            )

            connection.commit()
