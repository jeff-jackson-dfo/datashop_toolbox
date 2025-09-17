import contextlib
from datetime import datetime
from icecream import ic
import io
import json
import netCDF4 as nc
import os
import pandas as pd
from typing import NoReturn

from odf_toolbox.odfhdr import OdfHeader
from odf_toolbox.parameterhdr import ParameterHeader
from odf_toolbox.historyhdr import HistoryHeader
from odf_toolbox.lookup_parameter import lookup_parameter

class NetCdfHeader(OdfHeader):
    """
    NetCdfHeader Class: subclass of OdfHeader.

    This class is used to convert a NetCDF file to ODF.
    """

    def __init__(self):
        """
        Method that initializes an NetCdf class object.
        """
        super().__init__()
        self._sytm_format = '%d-%b-%Y %H:%M:%S.%f'
        
    def generate_creation_date(self) -> str:
        """ Generate a creation date in SYTM format. """
        creation_date = datetime.now().strftime(self._sytm_format)[:-4].upper()
        return creation_date

    def populate_parameter_headers(self, df: pd.DataFrame, seabird_names: list, 
                                long_names: list,  units: list) -> NoReturn:
        """ Populate the parameter headers and the data object. """
        parameter_list = list()
        print_formats = dict()
        number_of_rows = df.count().iloc[0]
        for idx, column in enumerate(df):
            parameter_header = ParameterHeader()
            number_null = int(df[column].isnull().sum())
            number_valid = int(number_of_rows - number_null)
            if column == 'sytm':
                param = 'SYTM'
            elif column == 'scan':
                param = 'CNTR'
            elif column == 'latitude':
                param = 'LATD'
            elif column == 'longitude':
                param = 'LONG'
            elif column == 'depth':
                param = 'DEPH'
            elif column == 'temp':
                param = 'TE90'
            elif column == 'sal':
                param = 'PSAL'
            elif column == 'cond':
                param = 'CNDC'
            elif column == 'pres':
                param = 'PRES'
            elif column == 'sig':
                param = 'SIGT'
            elif column == 'sigp':
                param = 'SIGP'
            elif column[0:4] == 'oxy':
                param = 'DOXY'
            elif column == 'ph':
                param = 'PHPH'
            elif column[0:5] == 'sbeox':
                param = 'OXYV'
            elif column == 'flor':
                param = 'FLOR'
            elif column == 'turb':
                param = 'TURB'
            elif column == 'wet':
                param = 'CDOM'
            elif column == 'par':
                param = 'PSAR'
            elif column == 'tra':
                param = 'ATBE'
            elif column == 'trp|trans':
                param = 'TRAN'
            elif column == 'oxypsat':
                param = 'OSAT'
            elif column == 'flag':
                param = 'FFFF'

            try:
                pnum = int(column[-1])
            except ValueError:
                if column[0:5] == 'sbeox':
                    pnum = int(column[5]) + 1
                else:
                    pnum = 1
            param_code = f'{param}_{pnum:02d}'

            # Get the parameter information from the lookup table.
            parameter_info = lookup_parameter(param)
            if param == 'SYTM':
                parameter_header.set_type('SYTM', read_operation=True)
                parameter_header.set_null_value('17-NOV-1858 00:00:00.00', read_operation=True)
                min_date = df[column].iloc[0].strip("\'")
                max_date = df[column].iloc[-1].strip("\'")
                parameter_header.set_minimum_value(min_date, read_operation=True)
                parameter_header.set_maximum_value(max_date, read_operation=True)
                print_formats[param_code] = (parameter_header.get_print_field_width())
            else:
                parameter_header.set_type('DOUB', read_operation=True)    
                parameter_header.set_null_value('-99.0', read_operation=True)
                min_value = df[column].min()
                max_value = df[column].max()
                parameter_header.set_minimum_value(min_value, read_operation=True)
                parameter_header.set_maximum_value(max_value, read_operation=True)
                print_formats[param_code] = (f"{parameter_header.get_print_field_width()}."
                                            f"{parameter_header.get_print_decimal_places()}")

            parameter_header.set_name(parameter_info.get('description'), read_operation=True)
            parameter_header.set_units(parameter_info.get('units'), read_operation=True)
            parameter_header.set_code(param_code, read_operation=True)
            parameter_header.set_print_field_width(parameter_info.get('print_field_width'), read_operation=True)
            parameter_header.set_print_decimal_places(parameter_info.get('print_decimal_places'), read_operation=True)
            parameter_header.set_angle_of_section('-99.0', read_operation=True)
            parameter_header.set_magnetic_variation('-99.0', read_operation=True)
            parameter_header.set_depth('-99.0', read_operation=True)
            parameter_header.set_number_valid(number_valid, read_operation=True)
            parameter_header.set_number_null(number_null, read_operation=True)
            parameter_list.append(param_code)
            
            # Add the new parameter header to the list.
            self.parameter_headers.append(parameter_header)

        # Update the data object.
        self.data.set_parameter_list(parameter_list)
        self.data.set_print_formats(print_formats)
        df = df.set_axis(parameter_list, axis='columns')
        self.data.set_data_frame(df)
        return self
    
    def main():

        captured_output = io.StringIO()

        with contextlib.redirect_stdout(captured_output):

            # Generate an empty MTR object.
            netcdf = NetCdfHeader()

            # operator = input('Enter the name of the operator: ')
            operator = 'Jeff Jackson'

            # Change to the drive's root folder
            os.chdir('\\')
            drive = os.getcwd()
            pathlist = ['DEV', 'pythonProjects', 'netcdf', 'data']
            top_folder = os.path.join(drive, *pathlist)
            os.chdir(top_folder)

            netcdf_file = 'cab054_2024_001.pcnv.nc'
            netcdf_path = os.path.join(top_folder, netcdf_file)
            print(f'\nProcessing NetCDF file: {netcdf_path}\n')

            # Read in the NetCDF file.
            ds = nc.Dataset(netcdf_path)

            # Update the Cruise Header.
            netcdf.cruise_header.set_country_institute_code(1805, read_operation=True)
            cruise_year = ds.__dict__['year']
            cruise_number = f'CAB{cruise_year}054'
            netcdf.cruise_header.set_cruise_number(cruise_number, read_operation=True)
            netcdf.cruise_header.set_organization(ds.__dict__['institution'], read_operation=True)
            netcdf.cruise_header.set_chief_scientist('', read_operation=True)
            sdate = ds.__dict__['time_coverage_start']
            start_date = datetime.strptime(sdate, '%Y-%m-%dT%H:%M:%SZ').strftime(r'%d-%b-%Y %H:%M:%S').upper() + '.00'
            netcdf.cruise_header.set_start_date(start_date, read_operation=True)
            edate = ds.__dict__['time_coverage_end']
            end_date = datetime.strptime(edate, '%Y-%m-%dT%H:%M:%SZ').strftime(r'%d-%b-%Y %H:%M:%S').upper() + '.00'
            netcdf.cruise_header.set_end_date(end_date, read_operation=True)
            netcdf.cruise_header.set_platform(ds.__dict__['platform_name'], read_operation=True)
            netcdf.cruise_header.set_cruise_description(ds.__dict__['title'], read_operation=True)

            # Update the Event Header.
            netcdf.event_header.set_data_type('CTD', read_operation=True)
            netcdf.event_header.set_event_number(ds.__dict__['comment'], read_operation=True)
            netcdf.event_header.set_event_qualifier1('1', read_operation=True)
            netcdf.event_header.set_event_qualifier2('DN', read_operation=True)
            cdatetime = netcdf.generate_creation_date()
            netcdf.event_header.set_creation_date(cdatetime, read_operation=True)
            netcdf.event_header.set_orig_creation_date(cdatetime, read_operation=True)
            sdatetime = ds.__dict__['start_time']
            start_datetime = datetime.strptime(sdatetime, '%Y-%m-%dT%H:%M:%S').strftime(r'%d-%b-%Y %H:%M:%S').upper() + '.00'
            netcdf.event_header.set_start_date_time(start_datetime, read_operation=True)
            netcdf.event_header.set_end_date_time('17-NOV-1858 00:00:00.00', read_operation=True)
            netcdf.event_header.set_initial_latitude(ds.__dict__['latitude'], read_operation=True)
            netcdf.event_header.set_initial_longitude(ds.__dict__['longitude'], read_operation=True)
            # netcdf.event_header.set_end_latitude(lat[-1], read_operation=True)
            # netcdf.event_header.set_end_longitude(lon[-1], read_operation=True)
            # netcdf.event_header.set_min_depth(meta['depth'].iloc[0], read_operation=True)
            # netcdf.event_header.set_max_depth(meta['depth'].iloc[0], read_operation=True)

            # netcdf.event_header.set_sounding(ds.__dict__['sounder_depth'], read_operation=True)

            # netcdf.event_header.set_event_number(str(meta['vessel_code'].iloc[0]), read_operation=True)
            interval = ds.__dict__['interval'].split(': ')[-1]
            netcdf.event_header.set_sampling_interval(interval, read_operation=True)
            netcdf.event_header.set_station_name(ds.__dict__['station'], read_operation=True)
            netcdf.event_header.set_event_comments(ds.__dict__['qa_applied'].replace('\n', '. '), read_operation=True)
            netcdf.event_header.set_event_comments(f"Sample Label Range: {ds.__dict__['stickers']}", read_operation=False)

            # Update the Instrument Header.
            netcdf.instrument_header.set_instrument_type('Sea-Bird', read_operation=True)
            netcdf.instrument_header.set_model(ds.__dict__['instrument_type'], read_operation=True)
            netcdf.instrument_header.set_serial_number(ds.__dict__['instrument'], read_operation=True)
            netcdf.instrument_header.set_description('Profiling CTD', read_operation=True)

            # Create a History Header.        
            history_header = HistoryHeader()
            history_header.set_creation_date(netcdf.generate_creation_date(), read_operation=True)
            history_header.set_process(f'Initial file creation by {operator}', read_operation=True)
            # Add processing notes to the history header.
            processing = json.loads(ds.__dict__['processing'])
            process_line = list()
            for process in processing:
                process_string = ''
                for key, value in process.items():
                    value = value.strip("\n")
                    value = ' '.join(value.split())
                    if key == 'module' and value == 'on-instrument':
                        process_string = 'Instrument setting: '
                    elif key == 'module' and value != 'on-instrument':
                        process_line.append(f"Module {value.upper()}: ")
                    elif key == 'message':
                        process_string = process_string + f"{value.strip()}"
                        process_line.append(process_string)
                    elif key == 'version':
                        process_line.append(f"\tSeaSave version used: {value.strip()}")
                    elif key == 'in':
                        process_line.append(f"\tFile(s) used: {value.strip()}")
                    else:
                        process_line.append(f"\t{key}: {value}")
            for process in process_line:
                history_header.set_process(process, read_operation=True)
            # Append new history header to the history headers list.
            netcdf.history_headers.append(history_header)

            # Create data dictionary.
            data_dict = dict()
            long_names = list()
            seabird_names = list()
            units = list()
            for name, variable in ds.variables.items():
                # print(variable.getncattr('long_name'))
                values = ds[name][:]
                if name == "index" or name == "time":
                    continue
                elif name == "latitude" or name == "longitude":
                    if float(values):
                        continue
                    else:
                        data_dict[name] = values
                else:
                    long_name = variable.getncattr('long_name')
                    long_names.append(long_name)
                    code = variable.getncattr('legacy_p_code')
                    seabird_names.append(code)
                    try:
                        unit = variable.getncattr('units')
                        units.append(unit)
                    except AttributeError:
                        unit = ''
                        units.append(unit)
                    data_dict[code] = values

            df = pd.DataFrame(data_dict)
            # print(df.head())
            # print(df.columns)
            odf = netcdf.populate_parameter_headers(df, seabird_names, long_names, 
                                                    units)

            netcdf.update_odf()

            # file_spec = netcdf.generate_file_spec()
            # odf_file_path = os.path.join(top_folder, file_spec + '.ODF')
            # netcdf.write_odf(odf_file_path, version=2)

            print(netcdf.print_object())

        print(captured_output.getvalue())


if __name__ == "__main__":
    NetCdfHeader.main()
