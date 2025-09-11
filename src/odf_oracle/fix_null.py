def fix_null(x):
    """
    ------------------------------------------------------------------------
    FIX_NULL: Convert all null values in the input matrix to NaNs.

    ODSToolbox Version: 2.0

    Creation Date: 26-SEP-2014
    Last Updated: 26-SEP-2014

    @author: Jeff Jackson

    @version: 1.0

    @copyright: 2014, Fisheries and Oceans Canada. All Rights Reserved.

    Source:
        Ocean Data and Information Services,
        Bedford Institute of Oceanography, DFO, Canada.
        DataServicesDonnees@dfo-mpo.gc.ca

    @summary: Convert all null values in the input matrix to NaNs.

    Usage: y = fix_null(x)

    Input:
        x: A number that may be equal to one of the following values: -99,
        -99.9, -999 or -999.9 which are possible ODF null values.

    Output:
        y: The input number or an empty string.

    Example:
        out = fix_null(in)

    Notes:

    Updates:

      Jeff Jackson (25-AUG-2022)
      - Reformatted code and made some minor modifications suggested by PyCharm.

    Report any bugs to DataServicesDonnees@dfo-mpo.gc.ca
    ------------------------------------------------------------------------
    """

    # Check to make sure the input number is not equal to any of the numeric
    # null values that are possible in an ODF formatted file. If it is a null
    # value then convert it to an empty string.
    if (x == -99) or (x == -99.9) or (x == -999) or (x == -999.9):
        y = ''
    else:
        y = x

    return y
