from datetime import datetime
import numpy as np
from icecream import ic

def sytm_to_timestamp(sytm: str, strid: str) -> datetime:
# def sytm_to_timestamp(sytm: str, strid: str) -> str:
    """
    Convert SYTM strings to Oracle timestamps.

    Parameters
    ----------
    sytm: str
        A date/time string in the ODF SYTM format.
    strid: str
        A string identifier indicating if it should be output as just a date 
        or a date/time string in the ODF SYTM format.

    Returns
    -------
    dstr: str
        A date string in Oracle's date or timestamp format according to 
        the datainsert function in MATLAB's Database toolbox.

    """

    dstr = ''
    if type(sytm) is np.str_:
        ndt = sytm.tolist()
        new_sytm = ndt.replace('\'', '')
        dt_object = datetime.strptime(new_sytm, '%d-%b-%Y %H:%M:%S.%f')
    else:
        if len(sytm) != 0:
            dt_object = datetime.strptime(sytm, '%d-%b-%Y %H:%M:%S.%f')
        else:
            dt_object = datetime.strptime('17-NOV-1858 00:00:00.00', '%d-%b-%Y %H:%M:%S.%f')
    if strid == 'datetime':
        dstr = dt_object.strftime('%Y-%m-%d %H:%M:%S.%f')
    elif strid == 'date':
        dstr = dt_object.strftime('%Y-%m-%d')

    # Check to make sure the dstr is not the ODF null value; if it is then change dstr to an empty string 
    # so that it is entered into Oracle as a null.
    if dstr[0:10] == '1858-11-17':
        dstr = ''

    # return dstr
    return dt_object


def main():

    sytm = "01-JUL-2017 10:45:19.00"
    ic(type(sytm))
    nps = np.str_(sytm)
    ic(nps)
    # sytm = ndt.replace('\'', '')
    dt_object = datetime.strptime(sytm, '%d-%b-%Y %H:%M:%S.%f')
    ic(dt_object)
    ts = sytm_to_timestamp(sytm, 'datetime')
    ic(ts)

if __name__ == "__main__":
     main()