import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.odfhdr import OdfHeader

col_formats = {
    'PRES_01':  '{:8.1f}',
    'QPRES_01': '{:>1d}',
    'TEMP_01':  '{:10.4f}',
    'QTEMP_01': '{:>1d}',
    'TE90_01':  '{:10.4f}',
    'QTE90_01': '{:>1d}',
    'PSAL_01':  '{:10.4f}',
    'QPSAL_01': '{:>1d}',
    'DOXY_01':  '{:8.3f}',
    'QDOXY_01': '{:>1d}',
}


def odf2exchange(odf_folder: Path, wildcard: str) -> None:
    """Generate CCHDO Exchange Formatted files from ODF files.

    Args:
        odf_folder: The path to the ODF files.
    """

    # Change to folder containing files to be modified
    os.chdir(odf_folder)

    # Find all ODF files in the current directory.
    files = odf_folder.glob(wildcard)

    # Loop through the list of ODF files and process both the DN and UP files.
    # Iterate through the list of input files.
    for file_name in files:

        print()
        print('#######################################################################')
        print(f'Processing file: {file_name.name}')
        print()

        # Read the ODF file in as an ODF object
        odf = OdfHeader()
        odf.read_odf(file_name.name)

        # Print Exchange header lines
        now = datetime.now()
        current_date = datetime.strftime(now, '%Y%m%d')
        operator_initials = 'JWJ'
        start_date = datetime.strptime(odf.cruise_header.start_date, BaseHeader.SYTM_FORMAT)
        sdate = start_date.strftime('%Y%m%d')
        if odf.cruise_header.platform.upper() == 'HUDSON':
            ship_code = '18HU'
        elif odf.cruise_header.platform.upper() == 'AMUNDSEN':
            ship_code = '18DL'
        elif odf.cruise_header.platform.upper() == 'ATLANTIS':
            ship_code = '33AT'
        elif odf.cruise_header.platform.upper() == 'CAPT JACQUES CARTIER':
            ship_code = '18QL'
        elif odf.cruise_header.platform.upper() == 'JAMES COOK':
            ship_code = '740H'
        elif odf.cruise_header.platform.upper() == 'LATALANTE':
            ship_code = '35A3'
        expocode = f'{ship_code}{sdate}'
        event = int(odf.event_header.event_number)
        output_path = Path(odf_folder, 'Exchange_Format/')
        if not output_path.is_dir():
            os.mkdir(output_path)
        output_file = Path(output_path, f'{expocode}_{event}_ct1.csv')
        with open(output_file, 'w', newline='') as f:
            f.write(f'CTD,{current_date}DFOBIO{operator_initials}\n')
            f.write('NUMBER_HEADERS = 10\n')
            f.write(f'EXPOCODE = {expocode}\n')
            f.write('SECT_ID = AR07W\n')
            f.write(f'STNNBR = {event}\n')
            f.write('CASTNO = 1\n')
            event_dt = datetime.strptime(odf.event_header.start_date_time, BaseHeader.SYTM_FORMAT)
            esdate = event_dt.strftime('%Y%m%d')
            estime = event_dt.strftime('%H%M')
            f.write(f'DATE = {esdate}\n')
            f.write(f'TIME = {estime}\n')
            f.write(f'LATITUDE = {odf.event_header.initial_latitude}\n')
            f.write(f'LONGITUDE = {odf.event_header.initial_longitude}\n')
            f.write(f'DEPTH =  {int(odf.event_header.sounding)}\n')
            # Check to see which scale the temperature is in: IPTS-68 or ITS-90?
            cols = odf.data.parameter_list
            if "TEMP_01" in cols:
                temp_scale = 'IPTS-68'
            elif "TE90_01" in cols:
                temp_scale = 'ITS-90'
            else:
                print("WARNING: Problem with temperature column handling.")
            output_df = odf.data.data_frame[['PRES_01','QPRES_01','TEMP_01','QTEMP_01','PSAL_01',
                                             'QPSAL_01','DOXY_01','QDOXY_01']]            
            formatted_cols = []
            for col in output_df.columns:
                if col.startswith('Q'):
                    # Convert flags to WOCE flags
                    output_df[col] = output_df[col].replace(2,3)
                    output_df[col] = output_df[col].replace(1,2)
                    formatted_cols.append(output_df[col].astype(int).map(col_formats[col].format))
                else:
                    formatted_cols.append(output_df[col].map(col_formats[col].format))
            formatted_df = pd.concat(formatted_cols, axis=1)
            f.write('CTDPRS,CTDPRS_FLAG_W,CTDTMP,CTDTMP_FLAG_W,CTDSAL,CTDSAL_FLAG_W,CTDOXY,CTDOXY_FLAG_W\n')
            f.write(f'DBAR,,{temp_scale},,PSS-78,,ML/L,\n')
            f.write(formatted_df.to_csv(index=False, header=False))
            f.write('END_DATA')

        print(f'Created CCHDO Exchange formatted file: {output_file}')
        print('#######################################################################')
        print()

    return


def main():

    odf_path = Path("C:/DFO-MPO/DEV/pythonProjects/CCHDO/ODF/")
    print(odf_path)

    # odf2exchange(odf_path, 'D*.ODF')
    odf2exchange(odf_path, '*_DN.ODF')

if __name__ == "__main__":
    main()
