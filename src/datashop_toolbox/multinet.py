from datetime import datetime
import pandas as pd
import numpy as np
import os
from typing import NoReturn, ClassVar

from odf_toolbox.lookup_parameter import lookup_parameter
from odf_toolbox.basehdr import BaseHeader
from odf_toolbox.odfhdr import OdfHeader
from odf_toolbox.cruisehdr import CruiseHeader
from odf_toolbox.eventhdr import EventHeader
from odf_toolbox.historyhdr import HistoryHeader
from odf_toolbox.recordhdr import RecordHeader
from odf_toolbox.parameterhdr import ParameterHeader
from odf_toolbox.records import DataRecords
from odf_toolbox import odfutils

class MultinetHeader(OdfHeader):
    """
    Multinet Class: subclass of OdfHeader.
    This class is responsible for storing the metadata and data associated with a HYDRO-BIOS multinet CTD profile.
    """
    date_format: ClassVar[str] = r'%Y-%m-%d'
    time_format: ClassVar[str] = r'%H:%M:%S'

    def __init__(self, calibrations = None) -> NoReturn:
        super().__init__()
        self.calibrations = calibrations if calibrations is not None else dict()

    @property
    def calibrations(self):
        return self._calibrations
    
    @calibrations.setter
    def calibrations(self, cals: dict) -> NoReturn:
        self._calibrations = cals


    def get_date_format(self) -> str:
        return MultinetHeader.date_format
    
    def get_time_format(self) -> str:
        return MultinetHeader.time_format

    def start_date_time(self, df: pd.Series) -> datetime:
        """ Retrieve the first date-time value from the data frame. """
        start_date = datetime.strptime(df['date'].iloc[0], MultinetHeader.date_format)
        start_time = datetime.strptime(df['time'].iloc[0], MultinetHeader.time_format).time()
        start_date_time = datetime.combine(start_date, start_time)
        return start_date_time

    def end_date_time(self, df: pd.Series) -> datetime:
        """ Retrieve the last date-time value from the data frame. """
        end_date = datetime.strptime(df['date'].iloc[-1], MultinetHeader.date_format)
        end_time = datetime.strptime(df['time'].iloc[-1], MultinetHeader.time_format).time()
        end_date_time = datetime.combine(end_date, end_time)
        return end_date_time

    def sampling_interval(self, df: pd.Series) -> int:
        """ Compute the time interval between the first two date-time values. """
        date1 = datetime.strptime(df['date'].iloc[0], MultinetHeader.date_format)
        time1 = datetime.strptime(df['time'].iloc[0], MultinetHeader.time_format).time()
        datetime1 = datetime.combine(date1, time1)
        date2 = datetime.strptime(df['date'].iloc[1], MultinetHeader.date_format)
        time2 = datetime.strptime(df['time'].iloc[1], MultinetHeader.time_format).time()
        datetime2 = datetime.combine(date2, time2)
        time_interval = datetime2 - datetime1
        time_interval = time_interval.seconds
        return time_interval

    def create_sytm(self, df: pd.DataFrame) -> pd.DataFrame:
        """ Updated the data frame with the proper SYTM column. """
        df['dates'] = df['date'].apply(lambda x: datetime.strptime(x, MultinetHeader.date_format).date())
        df['dates'] = df['dates'].astype("string")
        df['times'] = df['time'].apply(lambda x: datetime.strptime(x, MultinetHeader.time_format).time())
        df['times'] = df['times'].astype("string")
        df['datetimes'] = df['dates'] + ' ' + df['times']
        df = df.drop(columns=['date', 'time', 'dates', 'times'], axis=1)
        df['datetimes'] = pd.to_datetime(df['datetimes'])
        df['sytm'] = df['datetimes'].apply(lambda x: datetime.strftime(x, BaseHeader.SYTM_FORMAT)).str.upper()
        df = df.drop('datetimes', axis=1)
        df['sytm'] = df['sytm'].str[:-4]
        df['sytm'] = df['sytm'].apply(lambda x: "'" + str(x) + "'")
        return df
    
    @staticmethod
    def check_datetime_format(date_string, format):
        try:
            datetime.strptime(date_string, format)
            return True
        except ValueError:
            return False

    def fix_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """ Fix the date and time columns in the data frame. """

        # Replace all NaN values with 12:00 in times as this is not important other than to have a time.
        df['time'] = df['time'].fillna('12:00')

        # Add a datetime column.
        df['date'] = df['date'].astype("string")
        df['time'] = df['time'].astype("string")
        datetimes = []

        for i in range(len(df)):
            date_str = df['date'].iloc[i]
            time_str = df['time'].iloc[i]
            datetime_str = ''

            # Check the date format.
            if MultinetHeader.check_datetime_format(df['date'][i], r"%d/%m/%Y"):
                meta_date_format = r"%d/%m/%Y"
            elif MultinetHeader.check_datetime_format(df['date'][i], "%d-%m-%Y"):
                meta_date_format = "%d-%m-%Y"
            elif MultinetHeader.check_datetime_format(df['date'][i], "%b-%d-%y"):
                meta_date_format = "%b-%d-%y"
            elif MultinetHeader.check_datetime_format(df['date'][i], "%d-%b-%y"):
                meta_date_format = "%d-%b-%y"

            datetime_str = date_str + ' ' + time_str
            datetimes.append(datetime.strptime(datetime_str, MultinetHeader.date_format))

        df['datetime'] = datetimes

        # Check if the date and time columns are in the correct format.
        if not self.check_datetime_format(df['date'].iloc[0], MultinetHeader.date_format):
            raise ValueError(f"Date format is incorrect. Expected format: {MultinetHeader.date_format}")
        if not self.check_datetime_format(df['time'].iloc[0], MultinetHeader.time_format):
            raise ValueError(f"Time format is incorrect. Expected format: {MultinetHeader.time_format}")

        # Convert the date and time columns to datetime objects.
        df['date'] = pd.to_datetime(df['date'], format=MultinetHeader.date_format)
        df['time'] = pd.to_datetime(df['time'], format=MultinetHeader.time_format).dt.time
        return df

    @staticmethod
    def read_tab_delimited_file(file_path):
        """
        Reads a text file with header lines and tab-delimited data, 
        returning header and data separately.
        """
        header_lines = []
        column_names = []
        data_rows = []

        with open(file_path, 'r') as file:
            reading_header = True
            for line in file:
                line = line.strip()
                if reading_header:
                    if not line:
                        continue  # Skip empty lines in header
                    if '\t' in line:
                        reading_header = False
                        column_names = line.split('\t')
                        continue
                    header_lines.append(line)
                else:
                    data_rows.append(line.split('\t'))
        return header_lines, column_names, data_rows

    @staticmethod
    def fix_column_names(names: list) -> list:
        new_names = []
        for name in names:
            name = name.lower()
            toks = name.split("[")
            parts = toks[0].strip().split(" ")
            if len(parts) > 1:
                complete_part = ''
                n = len(parts)
                for x, part in enumerate(parts):
                    part = part.replace(".", "")
                    complete_part += part
                    if x < n - 1:
                        complete_part += "_"
                new_names.append(complete_part)
            else:
                new_names.append(parts[0])
        return new_names

    @staticmethod
    def split_calibration(cal_string: str) -> list:
        """
        Splits a calibration string into a list of floats.
        Example input: 'Cal0: -2.43644E+0  Cal1: 5.90671E-4  Cal2: 0E+0'
        Returns a list of floats.
        """
        toks = cal_string.split("Cal") 
        Cal = []
        for i, tok in enumerate(toks):
            if i == 0:
                continue
            else:
                t = tok.split(":")
                s = f"Cal.append({float(t[1].strip())})"
                eval(s)
        return Cal

    def extract_calibrations(self, header_lines) -> NoReturn: 
        temp_line = False
        cond_line = False
        pres_line = False
        vol_line = False
        tcal = []
        ccal = []
        pcal = []
        vcal = []
        calibrations = dict()
        for line in header_lines:
            if temp_line:
                tcal = self.split_calibration(line)
                temp_line = False
            if line.startswith('Temperature [°C]'):
                temp_line = True
            if cond_line:
                ccal = self.split_calibration(line)
                cond_line = False
            elif line.startswith('Conductivity [mS/cm]'):
                cond_line = True
            if pres_line:
                pcal = self.split_calibration(line)
                pres_line = False
            elif line.startswith('Pressure [dbar]'):
                pres_line = True
            if vol_line:
                vcal = self.split_calibration(line)
                vol_line = False
            elif line.startswith('Volume [m³]'):
                vol_line = True
        self.calibrations['temperature'] = [float(element) for element in tcal]
        self.calibrations['conductivity'] = [float(element) for element in ccal]
        self.calibrations['pressure'] = [float(element) for element in pcal]
        if len(vcal) == 1:
            self.calibrations['volume'] = float(vcal[0])
        else:
            self.calibrations['volume'] = vcal
    
    @staticmethod
    def compute_conductivity(conductivity_raw: pd.Series, ccal: list) -> float:
        """
        Computes the conductivity in mS/cm by applying a calibration equation to the raw conductivity values.
        """
        conductivity_mS = ccal[0] + ccal[1] * conductivity_raw + ccal[2] * (conductivity_raw ** 2)
        return conductivity_mS

    @staticmethod
    def compute_temperature(temp_raw: pd.Series, tcal: list) -> float:
        """
        Computes the temperature in Celsius by applying a calibration equation to the raw temperature voltavaluesge.
        """
        temp_celsius = tcal[0] + tcal[1] * temp_raw + tcal[2] * (temp_raw ** 2)
        return temp_celsius

    @staticmethod
    def compute_pressure(pressure_raw: pd.Series, pressure_temp_raw: pd.Series, pcal: list) -> float:
        """
        Computes the pressure in dbar by applying a calibration equation to the raw pressure values.
        """
        pressure_offset = pcal[0] + pcal[1] * pressure_temp_raw + pcal[2] * pressure_temp_raw ** 2
        pressure_data = pressure_raw - pressure_offset
        pressure_tk = pcal[3] + pcal[4] * pressure_temp_raw + pcal[5] * pressure_temp_raw ** 2
        pressure_tempcomp = pressure_data * pressure_tk
        pressure_dbar = pcal[6] + pcal[7] * pressure_tempcomp + pcal[8] * pressure_tempcomp ** 2
        return pressure_dbar

    @staticmethod
    def compute_volume(volume_raw: pd.Series, vcal: float) -> float:
        """
        Computes the volume in m**3 by applying a calibration equation to the raw volume values.
        """
        if vcal >= 0.25:
            x = 1
            volume_m3 = x * volume_raw
        else:
            x = 0.1
            volume_m3 = x * volume_raw
        return volume_m3

    @staticmethod
    def compute_flow(flow_raw: pd.Series) -> float:
        """
        Computes the flow rate by applying a calibration to the raw flow rate.
        """
        return flow_raw * 0.1

    @staticmethod
    def compute_flow_ratio(flow_in: pd.Series, flow_out: pd.Series) -> pd.Series:
        """
        Computes the flow rate by applying a calibration to the raw flow rate.
        """
        fin = flow_in[0:5]
        fin[0] = 5
        print(fin)
        fin = fin.values
        fout = flow_out[0:5].values
        print(fout)
        # flow_ratio = fin.div(fout, fill_value=0)
        flow_ratio = fout and fin / fout or 0
        print(flow_ratio)
        flow_ratio_cleaned = flow_ratio.replace([np.inf, -np.inf], 0)
        # flow_ratio = flow_in.div(flow_out)
        # flow_ratio_cleaned = flow_ratio.replace([np.inf, -np.inf], 0)
        return flow_ratio_cleaned

    def populate_odf_headers(self, df: pd.DataFrame):
        """ Populate the ODF headers and the data object. """
        # Create the ODF header.
        self.odf_header.cruise_header = CruiseHeader()
        self.odf_header.cruise_header.cruise_name = 'LAT2025146'
        self.odf_header.cruise_header.start_date = '26-MAY-2025 10:00:00.00'
        self.odf_header.cruise_header.end_date = '27-MAY-2025 16:00:00.00'

        self.odf_header.cruise_header.institution = 'GEOMAR Helmholtz Centre for Ocean Research Kiel'

        self.odf_header.cruise_header.cruise_code = df['cruise'].iloc[0]
        self.odf_header.event_header = EventHeader()
        self.data.odf_header.sampling_interval = self.sampling_interval(df)
        self.data.odf_header.start_date_time = self.start_date_time(df)
        self.data.odf_header.end_date_time = self.end_date_time(df)
        self.data.odf_header.station_name = df['station'].iloc[0]
        self.data.odf_header.station_code = df['station'].iloc[0]
        self.data.odf_header.latitude = df['latitude'].iloc[0]
        self.data.odf_header.longitude = df['longitude'].iloc[0]
        self.data.odf_header.geolocation = odfutils.get_geolocation(
            df['latitude'].iloc[0], df['longitude'].iloc[0])
        return self

    def populate_parameter_headers(self, df: pd.DataFrame):
        """ Populate the parameter headers and the data object. """
        parameter_list = list()
        print_formats = dict()
        number_of_rows = df.count().iloc[0]
        for column in df.columns:
            parameter_header = ParameterHeader()
            number_null = int(df[column].isnull().sum())
            number_valid = int(number_of_rows - number_null)
            if column == 'sytm':
                # parameter_info = lookup_parameter('oracle', 'SYTM')
                parameter_info = lookup_parameter('sqlite', 'SYTM')
                parameter_header.type = 'SYTM'
                parameter_header.name = parameter_info.get('description')
                parameter_header.units = parameter_info.get('units')
                parameter_header.code = 'SYTM_01'
                parameter_header.null_string = BaseHeader.SYTM_NULL_VALUE
                parameter_header.print_field_width = parameter_info.get('print_field_width')
                parameter_header.print_decimal_places = parameter_info.get('print_decimal_places')
                parameter_header.angle_of_section = BaseHeader.NULL_VALUE
                parameter_header.magnetic_variation = BaseHeader.NULL_VALUE
                parameter_header.depth = BaseHeader.NULL_VALUE
                min_date = df[column].iloc[0].strip("\'")
                max_date = df[column].iloc[-1].strip("\'")
                parameter_header.minimum_value = min_date
                parameter_header.maximum_value = max_date
                parameter_header.number_valid = number_valid
                parameter_header.number_null = number_null
                parameter_list.append('SYTM_01')
                print_formats['SYTM_01'] = (f"{parameter_header.print_field_width}")
            elif column == 'temperature':
                # parameter_info = lookup_parameter('oracle', 'TE90')
                parameter_info = lookup_parameter('sqlite', 'TE90')
                parameter_header.type = 'DOUB'        
                parameter_header.name = parameter_info.get('description')
                parameter_header.units = parameter_info.get('units')
                parameter_header.code = 'TE90_01'
                parameter_header.null_string = str(BaseHeader.NULL_VALUE)
                parameter_header.print_field_width = parameter_info.get('print_field_width')
                parameter_header.print_decimal_places = parameter_info.get('print_decimal_places')
                parameter_header.angle_of_section = BaseHeader.NULL_VALUE
                parameter_header.magnetic_variation = BaseHeader.NULL_VALUE
                parameter_header.depth = BaseHeader.NULL_VALUE
                min_temp = df[column].min()
                max_temp = df[column].max()
                parameter_header.minimum_value = min_temp
                parameter_header.maximum_value = max_temp
                parameter_header.number_valid = number_valid
                parameter_header.number_null = number_null
                parameter_list.append('TE90_01')
                print_formats['TE90_01'] = (f"{parameter_header.print_field_width}."
                                            f"{parameter_header.print_decimal_places}")
            
            # Add the new parameter header to the list.
            self.parameter_headers.append(parameter_header)

        # Update the data object.
        self.data.parameter_list = parameter_list
        self.data.print_formats = print_formats
        self.data.data_frame = df
        return self

    def read_multinet_files(file_type: str, file_path: str) -> pd.DataFrame:
        """
        Main function to read a tab-delimited file and print the header and data lines.
        """

        multinet = MultinetHeader()
        headers, columns, data = multinet.read_tab_delimited_file(file_path)

        if headers is not None and data is not None:
            df = pd.DataFrame(data)
            column_names = []
            for i, column in enumerate(columns):
                column_names.append(column)
            df.columns = multinet.fix_column_names(column_names)
            multinet.populate_odf_headers(headers)
            multinet.populate_parameter_headers(df)
            # print(df.head())

        match file_type:

            case 'raw':
                # When reading the raw data files extract the calibrations and apply them to the 
                # proper channel to compute the desired parameters.

                multinet.extract_calibrations(headers)
                flow_vol_raw = df["flow_vol_raw"]
                
                pressure_raw = df["pressure_raw"].astype(float)
                pressure_temp_raw = df["pressure_temp_raw"].astype(float)
                pressure = multinet.compute_pressure(pressure_raw, pressure_temp_raw, multinet.calibrations["pressure"])
                df['pressure'] = round(pressure, 1)

                temperature_raw = df["temperature_raw"].astype(float)
                temperature = multinet.compute_temperature(temperature_raw, multinet.calibrations["temperature"])
                df['temperature'] = round(temperature, 3)

                conductivity_raw = df["conductivity_raw"].astype(float)
                conductivity = multinet.compute_conductivity(conductivity_raw, multinet.calibrations["conductivity"])
                df['conductivity'] = round(conductivity, 3)

                volume = multinet.compute_volume(flow_vol_raw, multinet.calibrations["volume"])
                df['volume'] = volume

                flow_in_raw = df["flow_in_raw"].astype(float)
                flow_in = multinet.compute_flow(flow_in_raw)
                df['flow_in'] = round(flow_in, 1)

                flow_out_raw = df["flow_out_raw"].astype(float)
                flow_out = multinet.compute_flow(flow_out_raw)
                df['flow_out'] = round(flow_out, 1)

                # flow_ratio = multinet.compute_flow_ratio(df['flow_in'],  df['flow_out'])
                # df['flow_ratio'] = round(flow_ratio, 2)

            case 'computed':

                file_path = 'C:/dev/lat2025146/multinet/data/MPS_5715_25-05-04_10-57-17 Data.txt'

        return df

def main():

    raw_file_path = 'C:/dev/lat2025146/multinet/data/MPS_5715_25-05-04_10-57-17 Raw Data.txt'
    df_raw = MultinetHeader.read_multinet_files("raw", raw_file_path)
    print(df_raw.head())

    data_file_path = 'C:/dev/lat2025146/multinet/data/MPS_5715_25-05-04_10-57-17 Data.txt'
    df_data = MultinetHeader.read_multinet_files("data", data_file_path)
    # print(df_data.head())

if __name__ == "__main__":
    main()