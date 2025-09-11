from odf_toolbox.generalhdr import GeneralCalHeader

def general_cal_equation_to_oracle(general_cal_header: GeneralCalHeader, 
                                   connection, 
                                   gg: int, 
                                   filename: str) -> None:
    """
    Load a GENERAL_CAL_Header equation into Oracle.
  
    Parameters
    ----------
    general_cal_header: GeneralCalHeader class object
    connection: Oracle database connection object.
    gg: int
        Iterator identifying the order of the GENERAL_CAL_HEADERS in the 
        ODF file.
    filename: str
        The ODF file name.
    
    Returns
    -------
    None
    """

    # Create a cursor to the open connection.
    with connection.cursor() as cursor:

        # Loop through the General_Cal_Header.General_Cal_Equation.
        calibration_equation = general_cal_header.calibration_equation

        # Check to see if the GENERAL_CAL_HEADER contains any CALIBRATION_EQUATION(s).
        if calibration_equation is None:

            print('No General_Cal_Header.Calibration_Equation was present to load into Oracle.')

        elif type(calibration_equation) is str:

            # Execute the Insert SQL statement.
            cursor.execute(
                "INSERT INTO ODF_GENERAL_CAL_EQUATION "
                "(GENERAL_CAL_HEADER_NUMBER, CALIBRATION_EQUATION_NUMBER, "
                "CALIBRATION_EQUATION, ODF_FILENAME) "
                "VALUES (:cc_no, :equation_no, :equation, :fname)",
                {
                    'cc_no': gg,
                    'equation_no': 1,
                    'equation': calibration_equation,
                    'fname': filename
                }
                )
            
            connection.commit()
