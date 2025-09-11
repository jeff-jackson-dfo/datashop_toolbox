import collections

from odf_toolbox.odfhdr import OdfHeader
from odf_oracle.sytm_to_timestamp import sytm_to_timestamp

def polynomial_cal_to_oracle(odfobj: OdfHeader, connection, infile: str):
    """"
    Load the polynomial cal header metadata from the ODF object into Oracle.

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

        # Check to see if the ODF structure contains an POLYNOMIAL_CAL_HEADER.
        if odfobj.polynomial_cal_headers is None:

            print('No POLYNOMIAL_CAL_HEADER was present to load into Oracle.')

        # Only one POLYNOMIAL_CAL_HEADER to process.
        elif type(odfobj.polynomial_cal_headers) is collections.OrderedDict:

            # Get the information from the current POLYNOMIAL_CAL_HEADER.
            param = odfobj.polynomial_cal_headers[0].parameter_code
            cdt = odfobj.polynomial_cal_headers[0].calibration_date
            adt = odfobj.polynomial_cal_headers[0].application_date
            coef = odfobj.polynomial_cal_headers[0].coefficients
            caldate = sytm_to_timestamp(cdt, 'datetime')
            appdate = sytm_to_timestamp(adt, 'datetime')
            pch = []
            cursor.prepare(
                "INSERT INTO ODF_POLY_CAL (PARAMETER_CODE, CALIBRATION_DATE, "
                "APPLICATION_DATE, COEFFICIENT_NUMBER, "
                "COEFFICIENT_VALUE, ODF_FILENAME) VALUES (:1, :2, :3, :4, :5, :6)")
            if type(coef) is list:
                # Loop through the POLYNOMIAL_CAL_HEADER's Coefficients.
                # All calibrations start with intercept; i.e. coefficient 0.
                for i, c in enumerate(coef):
                    pch.append((param, caldate, appdate, i, c, infile))

                # Execute the Insert SQL statement.
                cursor.executemany(None, pch)

            elif type(coef) is str:

                pch.append((param, caldate, appdate, 0, coef, infile))

                # Execute the Insert SQL statement.
                cursor.executemany(None, pch)

            # Commit the changes to the database.
            connection.commit()

            print('Polynomial_Cal_Header successfully loaded into Oracle.')

        # Multiple POLYNOMIAL_CAL_HEADERs to process.
        elif type(odfobj.polynomial_cal_headers) is list:

            # Loop through the HISTORY_HEADERs.
            for i, polynomial_cal_header in enumerate(odfobj.polynomial_cal_headers):

                # Get the information from the current POLYNOMIAL_CAL_HEADER.
                param = polynomial_cal_header.parameter_code
                cdt = polynomial_cal_header.calibration_date
                adt = polynomial_cal_header.application_date
                ncoef = polynomial_cal_header.number_coefficients
                coeffs = polynomial_cal_header.coefficients
                caldate = sytm_to_timestamp(cdt, 'datetime')
                appdate = sytm_to_timestamp(adt, 'datetime')
                pch = []
                cursor.prepare(
                    "INSERT INTO ODF_POLY_CAL (PARAMETER_CODE, CALIBRATION_DATE, "
                    "APPLICATION_DATE, COEFFICIENT_NUMBER, "
                    "COEFFICIENT_VALUE, ODF_FILENAME) "
                    "VALUES (:1, :2, :3, :4, :5, :6)")
                if ncoef > 1:
                    # Loop through the POLYNOMIAL_CAL_HEADER's Coefficients.
                    # All calibrations start with intercept; i.e. coefficient 0.
                    for j, coef in enumerate(coeffs):
                        pch.append((param, caldate, appdate, j, coef, infile))

                    # Execute the Insert SQL statement.
                    cursor.executemany(None, pch)

                else:

                    pch.append((param, caldate, appdate, 0, coeffs, infile))

                    # Execute the Insert SQL statement.
                    cursor.executemany(None, pch)

                # Commit the changes to the database.
                connection.commit()

                print('Polynomial_Cal_Header successfully loaded into Oracle.')
