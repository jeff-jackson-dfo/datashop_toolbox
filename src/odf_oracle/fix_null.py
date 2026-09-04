def fix_null(x):
    """Convert all null values in the input matrix to NaNs.

    Args:
        x: A number that may be equal to one of the following values:
            ``-99``, ``-99.9``, ``-999`` or ``-999.9``, which are
            possible ODF null values.

    Returns:
        ``x`` unchanged, or an empty string if ``x`` is one of the
        recognized ODF null values.
    """

    # Check to make sure the input number is not equal to any of the numeric
    # null values that are possible in an ODF formatted file. If it is a null
    # value then convert it to an empty string.
    if (x == -99) or (x == -99.9) or (x == -999) or (x == -999.9):
        y = ""
    else:
        y = x

    return y
