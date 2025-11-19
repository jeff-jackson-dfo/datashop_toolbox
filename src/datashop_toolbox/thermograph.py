from datetime import datetime
import glob
import math
import os
import posixpath
import pytz
import re
import sys
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import ClassVar
from difflib import SequenceMatcher

from PyQt6.QtWidgets import (
    QApplication
)

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import check_datetime, get_current_date_time
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.parameterhdr import ParameterHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.lookup_parameter import lookup_parameter
from datashop_toolbox.qualityhdr import QualityHeader
from datashop_toolbox import select_metadata_file_and_data_folder


class ThermographHeader(OdfHeader):
    """
    Mtr Class: subclass of OdfHeader.
    This class is responsible for storing the metadata and data associated with a moored thermograph (MTR).
    """
    date_format: ClassVar[str] = r'%Y-%m-%d'
    time_format: ClassVar[str] = r'%H:%M:%S'


    def __init__(self) -> None:
        super().__init__()


    def get_date_format(self) -> str:
        return ThermographHeader.date_format
    

    def get_time_format(self) -> str:
        return ThermographHeader.time_format


    # @staticmethod
    # def is_date_only(value):
    #     if isinstance(value, date) and not isinstance(value, datetime):
    #         return True
    #     if isinstance(value, datetime):
    #         return value.time() == datetime.min.time()
    #     return False


    def start_date_time(self, df: pd.DataFrame) -> datetime:
        """ Retrieve the first date-time value from the data frame. """
        if 'date_time' in df.columns:
            start_date_time = df['date_time'].iloc[0]
        else:
            start_date = datetime.strptime(df['date'].iloc[0], ThermographHeader.date_format)
            start_time = datetime.strptime(df['time'].iloc[0], ThermographHeader.time_format).time()
            start_date_time = datetime.combine(start_date, start_time)
        return start_date_time


    def end_date_time(self, df: pd.DataFrame) -> datetime:
        """ Retrieve the last date-time value from the data frame. """
        if 'date_time' in df.columns:
            end_date_time = df['date_time'].iloc[-1]
        else:
            end_date = datetime.strptime(df['date'].iloc[-1], ThermographHeader.date_format)
            end_time = datetime.strptime(df['time'].iloc[-1], ThermographHeader.time_format).time()
            end_date_time = datetime.combine(end_date, end_time)
        return end_date_time


    def get_sampling_interval(self, df: pd.Series) -> float:
        """ Compute the time interval between the first two date-time values. """
        if 'date_time' in df.columns:
            datetime1 = df['date_time'][0]
            datetime2 = df['date_time'][1]
            time_interval = datetime2 - datetime1
            time_interval = float(time_interval.seconds)
        else:
            date1 = datetime.strptime(df['date'].iloc[0], ThermographHeader.date_format)
            time1 = datetime.strptime(df['time'].iloc[0], ThermographHeader.time_format).time()
            datetime1 = datetime.combine(date1, time1)
            date2 = datetime.strptime(df['date'].iloc[1], ThermographHeader.date_format)
            time2 = datetime.strptime(df['time'].iloc[1], ThermographHeader.time_format).time()
            datetime2 = datetime.combine(date2, time2)
            time_interval = datetime2 - datetime1
            time_interval = float(time_interval.seconds)
        return time_interval


    def create_sytm(self, df: pd.DataFrame) -> pd.DataFrame:
        """ Updated the data frame with the proper SYTM column. """
        if 'date_time' in df.columns:
            df['sytm'] = df['date_time'].map(lambda x: datetime.strftime(x, BaseHeader.SYTM_FORMAT)).str.upper()
            df = df.drop('date_time', axis=1)
            df['sytm'] = df['sytm'].str[:-4]
            df['sytm'] = df['sytm'].map(lambda x: "'" + str(x) + "'")
        else:
            df['dates'] = df['date'].map(lambda x: datetime.strptime(x, ThermographHeader.date_format).date())
            df['dates'] = df['dates'].astype("string")
            df['times'] = df['time'].map(lambda x: datetime.strptime(x, ThermographHeader.time_format).time())
            df['times'] = df['times'].astype("string")
            df['datetimes'] = df['dates'] + ' ' + df['times']
            df = df.drop(columns=['date', 'time', 'dates', 'times'], axis=1)
            df['datetimes'] = pd.to_datetime(df['datetimes'])
            df['sytm'] = df['datetimes'].map(lambda x: datetime.strftime(x, BaseHeader.SYTM_FORMAT)).str.upper()
            df = df.drop('datetimes', axis=1)
            df['sytm'] = df['sytm'].str[:-4]
            df['sytm'] = df['sytm'].map(lambda x: "'" + str(x) + "'")
        return df
    

    @staticmethod
    def check_datetime_format(date_string, format):
        try:
            datetime.strptime(date_string, format)
            return True
        except ValueError:
            return False


    @staticmethod
    def fix_datetime(df: pd.DataFrame, date_times: bool) -> pd.DataFrame:
        """ Fix the date and time columns in the data frame. """

        if date_times == False:
            # Replace all NaN values with 12:00 in times as this is not important other than to have a time.
            df['time'] = df['time'].fillna('12:00')

            # Add a datetime column.
            df['date'] = df['date'].astype("string")
            df['time'] = df['time'].astype("string")
        else:
            df['date'] = df['datetime'].dt.date.astype(str)
            df['time'] = df['datetime'].dt.time.astype(str)

        datetimes = []                
        for i in range(len(df)):
            date_str = df['date'].iloc[i]
            time_str = df['time'].iloc[i]
            datetime_str = ''

            # Check the date format.
            if ThermographHeader.check_datetime_format(df['date'][i], r"%d/%m/%Y"):
                meta_date_format = r"%d/%m/%Y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%d/%m/%y"):
                meta_date_format = "%d/%m/%y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%m-%Y"):
                meta_date_format = "%d-%m-%Y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%b-%d-%y"):
                meta_date_format = "%b-%d-%y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%B-%d-%y"):
                meta_date_format = "%B-%d-%y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%b-%y"):
                meta_date_format = "%d-%b-%y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%B-%y"):
                meta_date_format = "%d-%B-%y"

            # Check the time format.
            if ThermographHeader.check_datetime_format(df['time'][i], r"%H:%M"):
                meta_time_format = r"%H:%M"
            elif ThermographHeader.check_datetime_format(df['time'][i], r"%H:%M:%S"):
                meta_time_format = r"%H:%M:%S"
            elif ThermographHeader.check_datetime_format(df['time'][i], r"%H:%M:%S.%f"):
                meta_time_format = r"%H:%M:%S.%f"

            datetime_str = date_str + ' ' + time_str
            datetimes.append(datetime.strptime(datetime_str, f"{meta_date_format} {meta_time_format}"))
            # datetimes.append(datetime.strptime(datetime_str, ThermographHeader.date_format))

        df['datetime'] = datetimes

        return df


    @staticmethod
    def convert_to_decimal_degrees(pos: str) -> float:
        toks = str(pos).strip().split()
        if len(toks) == 2:
            deg = float(toks[0])
            dm = float(toks[1])
            dd = deg + dm/60
            return dd
        else:
            return float(pos)


    @staticmethod
    def extract_number(s: str) -> float | None:
        match = re.sub(r'[^0-9.]', '', s)
        return float(match) if match else None


    def populate_parameter_headers(self, df: pd.DataFrame):
        """ Populate the parameter headers and the data object. """
        parameter_list = list()
        print_formats = dict()
        number_of_rows = df.count().iloc[0]
        param_name = ''
        for column in df.columns:
            parameter_header = ParameterHeader()
            number_null = int(df[column].isnull().sum())
            number_valid = int(number_of_rows - number_null)
            if column == 'sytm':
                param_name = 'SYTM'
                param_code = f"{param_name}_01"
                parameter_header.type = param_name
                min_date = df[column].iloc[0].strip("\'")
                max_date = df[column].iloc[-1].strip("\'")
                parameter_header.minimum_value = min_date
                parameter_header.maximum_value = max_date
                parameter_header.null_string = BaseHeader.SYTM_NULL_VALUE
            elif column == 'temperature':
                param_name = 'TE90'
                parameter_header.type = 'DOUB'
            elif column == 'pressure':
                param_name = 'PRES'
                parameter_header.type = 'DOUB'
            elif column == 'depth':
                param_name = 'DEPH'
                parameter_header.type = 'DOUB'
            elif column == 'dissolved_oxygen':
                param_name = 'DOXY'
                parameter_header.type = 'DOUB'
            if parameter_header.type == 'DOUB':
                param_code = f"{param_name}_01"
                min_temp = df[column].min()
                max_temp = df[column].max()
                parameter_header.minimum_value = min_temp
                parameter_header.maximum_value = max_temp
                parameter_header.null_string = str(BaseHeader.NULL_VALUE)

            # parameter_info = lookup_parameter('oracle', param_name)
            parameter_info = lookup_parameter('sqlite', param_name)
            parameter_header.name = parameter_info.get('description')
            parameter_header.units = parameter_info.get('units')
            parameter_header.code = param_code
            parameter_header.angle_of_section = BaseHeader.NULL_VALUE
            parameter_header.magnetic_variation = BaseHeader.NULL_VALUE
            parameter_header.depth = BaseHeader.NULL_VALUE
            if param_name == 'SYTM':
                parameter_header.print_field_width = parameter_info.get('print_field_width')
                parameter_header.print_decimal_places = parameter_info.get('print_decimal_places')
                print_formats[param_code] = (f"{parameter_header.print_field_width}")
            else:
                parameter_header.print_field_width = parameter_info.get('print_field_width')
                parameter_header.print_decimal_places = parameter_info.get('print_decimal_places')
                print_formats[param_code] = (f"{parameter_header.print_field_width}."
                                            f"{parameter_header.print_decimal_places}")
            parameter_header.number_valid = number_valid
            parameter_header.number_null = number_null
            parameter_list.append(param_code)
            
            # Add the new parameter header to the list.
            self.parameter_headers.append(parameter_header)

        # Update the data object.
        self.data.parameter_list = parameter_list
        self.data.print_formats = print_formats
        self.data.data_frame = df
        return self
    

    @staticmethod
    def is_minilog_file(file_path: str) -> bool:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= 8:  # only check first 8 lines
                    break
                if "minilog" in line.lower():
                    return True
        return False


    @staticmethod
    def read_mtr(mtrfile: str, instrument_type: str = "minilog") -> dict:
        """ 
        Read an MTR data file and return a pandas DataFrame. 

        :mtrfile: Full path to the thermograph source data text file.
        :instrument_type: Type of instrument used to acquire the data ('minilog' or 'hobo')
        """
        
        mtr_dict = dict()
        instrument_type = instrument_type.lower()

        def similar(a, b):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        if instrument_type == 'minilog':
            # Detect number of header lines dynamically ---
            skiprows = 0
            with open(mtrfile, 'r', encoding='iso8859_1') as f:
                for i, line in enumerate(f):
                    stripped = line.strip()
                    # Detect the first data-like line - Typically starts with a date (e.g., "11/03/2014") or similar pattern 11-03-2014
                    if re.match(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})", stripped):
                        skiprows = i
                        break
                    elif stripped.startswith('* Date(yyyy-mm-dd),') or stripped.startswith('Date(yyyy-mm-dd),'):
                        skiprows = i+1
                        break
                    else:
                        skiprows = 8  # Default to 8 if no match found
                        break
            
            # Read the data lines from the MTR file
            dfmtr = pd.read_table(mtrfile, sep = ',', header = None, encoding = 'iso8859_1', skiprows = skiprows)
            # print(dfmtr.head())

            # rename the columns
            dfmtr.columns = ['date', 'time', 'temperature']

            # Get the instrument type and gauge (serial number) from the MTR file.
            inst_model, gauge, delTime_UTC = None, None, None
            with open(mtrfile, 'r', encoding = 'iso8859_1') as f:
                for i, line in enumerate(f):
                    if i >= skiprows:
                        break  # Stop after header lines
                    if 'Source Device:' in line:
                        info = line.split(':', 1)[1].strip()
                        parts = info.split('-')
                        inst_model = '-'.join(parts[:-1]).strip()
                        gauge = parts[-1].strip().strip(',')
                        continue
                    if line.startswith(('* ID=', 'ID=')):
                        inst_model = line.split('=', 1)[1].strip()
                        continue
                    if line.startswith(('* Serial Number=', 'Serial Number=')):
                        gauge = line.split('=', 1)[1].strip()
                        continue
                    if 'Minilog Initialized:' in line:
                        pattern = r'(?:\(UTC([+-]\d+)\)|\(GMT([+-]\d+)\))'
                        match = re.search(pattern, line, flags=re.IGNORECASE)
                        if match:
                            delTime_UTC = match.group(1).strip()
                            delTime_UTC = int(delTime_UTC) if str(delTime_UTC).lstrip('+-').isdigit() else 0
                        continue
            
            # --- Safety defaults: ask user if not found ---
            if inst_model is None:
                inst_model = input(f"⚠️ Input message for '{mtrfile}' file: Please input 'inst_model (example: Minilog-T)' to continue: ")
            if gauge is None:
                gauge = input(f"⚠️ Input message for '{mtrfile}' file: Please input 'gauge number(note: must be integer)' to continue: ")
            if delTime_UTC is None or delTime_UTC == 0:
                print("⚠️ No UTC/GMT offset found in column headers. Setting offset = 0 and assumed Timezone is UTC")
                delTime_UTC = 0
            else:
                print(f"✅ Detected time offset from header: UTC{delTime_UTC:+d}")
            
            # --- Assemble results ---
            if abs(delTime_UTC) == 0:
                mtr_dict['df'] = dfmtr
                mtr_dict['inst_model'] = inst_model
                mtr_dict['gauge'] = gauge.strip(",")
                mtr_dict['filename'] = mtrfile
            else:
                hours = abs(float(delTime_UTC))
                dfmtr['DateTime'] = pd.to_datetime(dfmtr['date'] + ' ' + dfmtr['time'])
                if float(delTime_UTC) < 0:
                    dfmtr['DateTime'] = dfmtr['DateTime'] + timedelta(hours=hours)
                else:
                    dfmtr['DateTime'] = dfmtr['DateTime'] - timedelta(hours=hours)
                dfmtr['date'] = dfmtr['DateTime'].dt.date.astype(str)
                dfmtr['time'] = dfmtr['DateTime'].dt.time.astype(str)
                dfmtr.drop(columns=['DateTime'], inplace=True)
                mtr_dict['df'] = dfmtr
                mtr_dict['inst_model'] = inst_model
                mtr_dict['gauge'] = gauge
                mtr_dict['filename'] = mtrfile

        elif instrument_type == 'hobo':
            # Detect number of header lines dynamically ---
            skiprows = 0
            pattern = re.compile(
                r"^\s*\d+,\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s*[APap][Mm],"
                )
            with open(mtrfile, 'r', encoding='iso8859_1') as f:
                for i, line in enumerate(f):
                    stripped = line.strip()
                    # Case 1: Header line (with column names)
                    if stripped.startswith('"#",') or stripped.startswith('"#","Date Time'):
                        skiprows = i
                        break
                    #Case 2: Direct data line (starts with record number, date-time, etc.)
                    elif pattern.match(stripped):
                        skiprows = i - 1 if i > 0 else 0  # avoid negative skiprows
                        break
                    else:
                        skiprows = 1
                        break  # Default to skipping first line if no match found

            # Read the data lines from the MTR file.
            dfmtr = pd.read_table(mtrfile, sep = ',', header = 0, encoding = 'utf-8', skiprows = 1)
            
            # drop the row number column & Extract offset value from UTC/GMT column header
            delTime_UTC = None
            for col in dfmtr.columns:
                if similar(col, "#") > 0.8:
                    dfmtr.drop(columns=[col], inplace=True)
                    continue
                match = re.search(r'(?:UTC|GMT)\s*([+-]\d{1,2})(?::?\d{2})?', col, flags=re.IGNORECASE)
                if match:
                    delTime_UTC = int(match.group(1))  # Extract numeric offset (e.g., -3, +2)
                    delTime_UTC = int(delTime_UTC) if str(delTime_UTC).lstrip('+-').isdigit() else 0
                    continue
            if delTime_UTC is None or delTime_UTC == 0:
                print("⚠️ No UTC/GMT offset found in column headers. Setting offset = 0 and assumed Timezone is UTC")
                delTime_UTC = 0
            else:
                print(f"✅ Detected time offset from header: UTC{delTime_UTC:+d}")
            
            possible_map = {
                "date_time": ["date time", "datetime", "date/time", "date-time"],
                "pressure": ["abs pres", "pressure", "absolute pressure"],
                "depth": ["sensor depth", "depth"],
                "temperature": ["temp", "temperature", "water temp", "temp °c"],
                "dissolved_oxygen": ["do conc", "dissolved oxygen", "do %"]
            }
        
            # Extract required info from columns and rename them with shorter names
            cols = dfmtr.columns
            column_names = []
            cols_to_keep = []
            inst_id = None
            for i, col in enumerate(cols):
                clean_col = col.strip().replace('"', '')
                cnames = col.split(",")
                cname = cnames[0]
                match_found = False
                for canonical, variants in possible_map.items():
                    if any(similar(cname, v) > 0.7 for v in variants):  # 70% similarity threshold
                        column_names.append(canonical)
                        cols_to_keep.append(i)
                        temp_lookup= possible_map["temperature"] 
                        if any(item in clean_col.lower() for item in temp_lookup) and ":" in clean_col:
                            # Extract instrument ID if present
                            try:
                                inst_id = clean_col.split(":")[1].split(",")[0].strip()
                            except Exception:
                                pass
                        match_found = True
                        break

                if not match_found:
                    print(f"⚠️ Warning: Unrecognized column '{col}' in file '{mtrfile}'. This column will be ignored.")
                    continue    
            
            # Keep only selected columns
            dfmtr = dfmtr[dfmtr.columns[cols_to_keep]]

            # Rename the kept columns
            dfmtr.columns = column_names

            # halifax_tz = pytz.timezone("America/Halifax")
            dt_format_string = "%m/%d/%y %I:%M:%S %p"
            dt_original = dfmtr['date_time']
            local_tz = timezone(timedelta(hours=delTime_UTC))
            datetime_objects = [
            datetime.strptime(dt_str, dt_format_string).replace(tzinfo=local_tz).astimezone(timezone.utc)
                            for dt_str in dt_original]
            dfmtr['date_time'] = datetime_objects
            
            ## Assemble results ---
            mtr_dict['df'] = dfmtr
            mtr_dict['gauge'] = inst_id
            mtr_dict['filename'] = mtrfile
            # print(mtr_dict)

        return mtr_dict


    @staticmethod
    def read_metadata(metafile: str, institution: str) -> pd.DataFrame:
        """
        Read a Metadata file and return a pandas DataFrame.

        :metafile: The file containing the metadata information.
        :institution: A string identifying the group who supplied the metadata. (currently "FSRS" or "BIO")
        """
        dfmeta = pd.DataFrame()

        if institution == 'FSRS':

            dfmeta = pd.read_table(metafile, encoding = 'iso8859_1')

            # Change some column types.
            dfmeta['LFA'].astype(int)
            dfmeta['Vessel Code'].astype(int)
            dfmeta['Gauge'].astype(int)
            dfmeta['Soak Days'].astype(int)

            # Drop some columns.
            dfmeta.drop(columns=['Date.1', 'Latitude', 'Longitude', 'Depth'], inplace = True)

            # Rename some columns.
            dfmeta.rename(columns={'Date': 'date', 'Time': 'time', 'LFA': 'lfa', 
                                'Vessel Code': 'vessel_code', 'Gauge': 'gauge', 
                                'Soak Days': 'soak_days', 
                                'Latitude (degrees)': 'latitude', 
                                'Longitude (degrees)': 'longitude',
                                'Depth (m)': 'depth', 'Temp': 'temperature'},
                                inplace = True)

            # Fix the date and time columns.
            dfmeta = ThermographHeader.fix_datetime(dfmeta, False)

        elif institution == 'BIO':

            dfmeta = pd.read_excel(metafile)

        return dfmeta


    def process_thermograph(self, institution_name: str, instrument_type: str, metadata_file_path: str, data_file_path: str, user_input_metadata):

        if institution_name == 'FSRS':
            # Get user input metadata values with defaults
            organization = user_input_metadata.get("organization", "FSRS")
            chief_scientist = user_input_metadata.get("chief_scientist", "SHANNON SCOTT-TIBBETTS")
            cruise_description = user_input_metadata.get("cruise_description", "FISHERMEN  AND SCIENTISTS RESEARCH SOCIETY")
            platform_name = user_input_metadata.get("platform_name", "FSRS CRUISE DATA (NO ICES CODE)")
            country_code = user_input_metadata.get("country_code", "1899")

            # print(f'\nProcessing Metadata file: {metadata_file_path}\n')
            meta = self.read_metadata(metadata_file_path, institution_name)
        
            # print(f'\nProcessing Thermograph Data file: {data_file_path}\n')
            mydict = self.read_mtr(data_file_path, instrument_type)

            df = mydict['df']
            inst_model = mydict['inst_model']
            gauge = mydict['gauge']
            # print(df.head())

            meta_subset = meta[meta['gauge'] == int(gauge)]
            # print(meta_subset.head())
            # print('\n')

            self.cruise_header.country_institute_code = country_code
            cruise_year = df['date'].to_string(index=False).split('-')[0]
            cruise_number = f'BCD{cruise_year}603'
            self.cruise_header.cruise_number = cruise_number
            self.cruise_header.platform = platform_name
            start_date = f"{self.start_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.start_date = start_date
            end_date = f"{self.end_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.end_date = end_date
            self.cruise_header.organization = organization
            self.cruise_header.chief_scientist = chief_scientist
            self.cruise_header.cruise_description = cruise_description
            
            self.event_header.data_type = 'MTR'
            self.event_header.event_qualifier1 = gauge
            self.event_header.event_qualifier2 = str(int(self.get_sampling_interval(df)))
            self.event_header.creation_date = get_current_date_time()
            self.event_header.orig_creation_date = get_current_date_time()
            self.event_header.start_date_time = self.start_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
            self.event_header.end_date_time = self.end_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
            lat = meta_subset['latitude'].iloc[0]
            long = meta_subset['longitude'].iloc[0]
            if lat < 0:
                lat = lat * -1
            if long > 0:
                long = long * -1
            self.event_header.initial_latitude = lat
            self.event_header.initial_longitude = long
            self.event_header.end_latitude = lat
            self.event_header.end_longitude = long
            depth = meta_subset['depth']
            self.event_header.min_depth = min(depth)
            self.event_header.max_depth = max(depth)
            self.event_header.event_number = str(meta_subset['vessel_code'].iloc[0])
            self.event_header.sampling_interval = float(self.get_sampling_interval(df))
            
            if 'minilog' in inst_model.lower():
                self.instrument_header.instrument_type = 'MINILOG'
            self.instrument_header.model = inst_model
            self.instrument_header.serial_number = gauge
            self.instrument_header.description = 'TEMPERATURE DATA LOGGER'

            new_df = self.create_sytm(df)

            self.populate_parameter_headers(new_df)

            for x, column in enumerate(new_df.columns):
                code = self.parameter_headers[x].code
                new_df.rename(columns={column: code}, inplace=True)

        elif institution_name == 'BIO':
            # Get user input metadata values with defaults
            organization = user_input_metadata.get("organization", "DFO BIO")
            chief_scientist = user_input_metadata.get("chief_scientist", "ADAM DROZDOWSKI")
            cruise_description = user_input_metadata.get("cruise_description", "LONG TERM TEMPERATURE MONITORING PROGRAM (LTTMP)")
            platform_name = user_input_metadata.get("platform_name", "BIO CRUISE DATA (NO ICES CODE)")
            country_code = user_input_metadata.get("country_code", "1810")

            # print(f'\nProcessing Metadata file: {metadata_file_path}\n')
            meta = self.read_metadata(metadata_file_path, institution_name)

            # print(f'\nProcessing Thermograph Data file: {data_file_path}\n')
            mydict = self.read_mtr(data_file_path, instrument_type)

            df = mydict['df']
            gauge = int(mydict['gauge'])
            # print(df.head())

            # Remove any leading or trailing spaces from the file names.
            meta['file_name'] = meta['file_name'].str.strip()
            # Make the file
            meta['file_name'] = meta['file_name'].str.lower()

            # path = Path(metadata_file_path)
            meta_subset = meta[meta['ID'] == float(gauge)]

            if len(meta_subset) > 1:
                path1 = Path(data_file_path)
                if instrument_type == 'hobo':
                    hobo_file = f"{path1.stem}.hobo".lower()
                    # print(hobo_file)
                    meta_subset = meta_subset[meta_subset['file_name'] == hobo_file]
                else:
                    minilog_file = f"{path1.stem}.vld".lower()
                    # print(minilog_file)
                    meta_subset = meta_subset[meta_subset['file_name'] == minilog_file]

            # print(meta_subset.head())
            # print('\n')

            matching_indices = meta_subset[meta_subset['ID'] == gauge].index

            if instrument_type.lower() == 'minilog':
                inst_model = (
                    mydict.get('inst_model')
                    or meta_subset.get('Instrument', pd.Series(['minilog II'])).iloc[0]
                    or "minilog II"
                )
            elif instrument_type.lower() == 'hobo':
                inst_model = meta_subset.get('Instrument', pd.Series(['hobo'])).iloc[0]
            else:
                inst_model = "hobo"

            self.cruise_header.country_institute_code = country_code
            if instrument_type == 'minilog':
                cruise_year = df['date'].to_string(index=False).split('-')[0]
            elif instrument_type == 'hobo':
                cruise_year = df['date_time'].to_string(index=False).split('-')[0]
            cruise_number = f'BCD{cruise_year}999'
            self.cruise_header.cruise_number = cruise_number
            self.cruise_header.platform = platform_name
            start_date = f"{self.start_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.start_date = start_date
            end_date = f"{self.end_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.end_date = end_date
            self.cruise_header.organization = organization
            self.cruise_header.chief_scientist = chief_scientist
            self.cruise_header.cruise_name = f"LTTMP BIO VARIOUS SITES ({meta_subset['location'].iloc[0]})"
            self.cruise_header.cruise_description = cruise_description
            
            self.event_header.data_type = 'MTR'
            self.event_header.event_qualifier1 = str(gauge)
            sampling_interval = self.get_sampling_interval(df)
            self.event_header.event_qualifier2 = str(int(sampling_interval))
            self.event_header.creation_date = get_current_date_time()
            self.event_header.orig_creation_date = get_current_date_time()
            self.event_header.start_date_time = self.start_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
            self.event_header.end_date_time = self.end_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
            lat = meta_subset['lat_dep'].iloc[0]
            if isinstance(lat, str):
                lat = self.convert_to_decimal_degrees(lat)
            long = meta_subset['lon_dep'].iloc[0]
            if isinstance(long, str):
                long = self.convert_to_decimal_degrees(long)
            if lat < 0:
                lat = abs(lat)
            if long > 0:
                long = long * -1
            self.event_header.initial_latitude = lat
            self.event_header.initial_longitude = long
            self.event_header.end_latitude = lat
            self.event_header.end_longitude = long
            depth = []
            min_val = None
            max_val = None
            dep_dep = str(meta_subset['dep_dep'].iloc[0])
            dep_dep = self.extract_number(dep_dep)
            if not pd.isna(dep_dep):
                depth.append(dep_dep)
            dep_rec = str(meta_subset['dep_rec'].iloc[0])
            dep_rec = self.extract_number(dep_rec)
            if not pd.isna(dep_rec):
                depth.append(dep_rec)
            valid_depths = [d for d in depth if not math.isnan(d)]                
            if valid_depths:  # avoid ValueError if list is empty
                min_val = min(valid_depths)
                max_val = max(valid_depths)
                self.event_header.min_depth = min_val
                self.event_header.max_depth = max_val
            self.event_header.event_number = f"{matching_indices[0]:03d}"
            if instrument_type == 'minilog':
                self.event_header.sampling_interval = float(self.get_sampling_interval(df))
                self.instrument_header.instrument_type = 'MINILOG'
            elif instrument_type == 'hobo':
                self.event_header.sampling_interval = sampling_interval            
                self.instrument_header.instrument_type = 'HOBO'
            self.instrument_header.model = inst_model
            self.instrument_header.serial_number = str(gauge)
            self.instrument_header.description = 'TEMPERATURE DATA LOGGER'

            new_df = self.create_sytm(df)

            self.populate_parameter_headers(new_df)

            for x, column in enumerate(new_df.columns):
                code = self.parameter_headers[x].code
                new_df.rename(columns={column: code}, inplace=True)
        
        return self


def main():

    use_gui = True

    if use_gui:

        # Create the GUI to select the metadata file and data folder
        app = QApplication(sys.argv)
        select_inputs = select_metadata_file_and_data_folder.MainWindow()
        select_inputs.show()
        app.exec()

        if select_inputs.result != "accept":
            print('\n****  Operation cancelled by user, exiting program.  ****\n')
            exit()

        if select_inputs.metadata_file == '' or select_inputs.data_folder == '':
            print('\n****  Improper selections made, exiting program.  ****\n')
            exit()
        else:
            metadata_file_path = select_inputs.metadata_file
            data_folder_path = select_inputs.data_folder

        # Get the operator's name so it is identified in the history header.
        if select_inputs.line_edit_text == '':
            operator = input('Please enter the name of the analyst performing the data processing: ')
        else:
            operator = select_inputs.line_edit_text

        institution = select_inputs.institution.upper()
        instrument = select_inputs.instrument.lower()

        # Change to folder containing files to be modified
        os.chdir(data_folder_path)

        # Find all CSV files in the current directory.
        files = glob.glob('*.CSV')

        # Check if no data files were found.
        if files == []:
            print(f"****  No data files found in selected folder {data_folder_path}  ****\n")
        else:
            # Create the required subfolder, if necessary
            if not os.path.isdir(os.path.join(data_folder_path, 'Step_1_Create_ODF')):
                os.mkdir('Step_1_Create_ODF')
            odf_path = os.path.join(data_folder_path, 'Step_1_Create_ODF')

        # Loop through the CSV files to generate an ODF file for each.
        for file_name in files:

            print()
            print('#######################################################################')
            print(f'Processing MTR file: {file_name}')
            print('#######################################################################')
            print()

            mtr_path = posixpath.join(data_folder_path, file_name)

            mtr = ThermographHeader()

            history_header = HistoryHeader()
            history_header.creation_date = get_current_date_time()
            history_header.set_process(f'INITIAL FILE CREATED BY {operator.upper()}')
            mtr.history_headers.append(history_header)

            mtr.process_thermograph(institution.upper(), instrument.lower(), metadata_file_path, mtr_path, user_input_metadata)

            file_spec = mtr.generate_file_spec()
            mtr.file_specification = file_spec

            mtr.update_odf()

            odf_file_path = os.path.join(odf_path, file_spec + '.ODF')
            mtr.write_odf(odf_file_path, version = 2.0)

            # Reset the shared log list
            BaseHeader.reset_log_list() 

    else:

        # Generate an empty MTR object.
        mtr = ThermographHeader()

        operator = 'Jeff Jackson'

        # institution_name = 'FSRS'
        # instrument_type = 'minilog'
        # metadata_file = 'C:/DFO-MPO/DEV/MTR/FSRS_data_2013_2014/LatLong LFA 30_14.txt' # FSRS
        # data_folder_path = 'C:/DFO-MPO/DEV/MTR/FSRS_data_2013_2014/LFA 30/' # FSRS
        # data_file_path = 'C:/DFO-MPO/DEV/MTR/FSRS_data_2013_2014/LFA 30/Minilog-II-T_354633_2014jmacleod_1.csv' # FSRS

        institution_name = 'BIO'
        #instrument_type = 'minilog'
        instrument_type = 'hobo'
        metadata_file = 'C:/MTR_Data_Processing/BCD2014999/MetaData_BCD2014999.xlsx' # BIO
        # metadata_file = 'C:/DFO-MPO/DEV/MTR/999_Test/MetaData_BCD2015999_Reformatted.xlsx' # BIO
        # data_folder_path = 'C:/DFO-MPO/DEV/MTR/999_Test/'  # BIO
        # data_folder_path = 'C:/DFO-MPO/DEV/MTR/BCD2014999/Hobo/'  # BIO
        data_folder_path = 'C:/MTR_Data_Processing/BCD2014999/RAW_Data/Hobos/MTR_Hobos_RAW_CSV'  # BIO
        # data_file_path = 'C:/DFO-MPO/DEV/MTR/999_Test/Liscomb_15m_352964_20160415_1.csv'  # BIO
        # data_file_path = 'C:/DFO-MPO/DEV/MTR/999_Test/cape_sable_summer_2014.csv'  # BIO
        # data_file_path = 'C:/DFO-MPO/DEV/MTR/999_Test/LTTMP_summer2014_HLFX_1273003_south.csv'  # BIO
        # data_file_path = 'C:/DFO-MPO/DEV/MTR/BCD2014999/Hobo/Dundee_10231582.csv'  # BIO
        data_file_path = 'C:/MTR_Data_Processing/BCD2014999/RAW_Data/Hobos/MTR_Hobos_RAW_CSV/baddeck_summer2014_1001597.csv'  # BIO
        # data_file_path = 'C:/DFO-MPO/DEV/MTR/999_Test/Whycocomagh_885_north_10m.csv'  # BIO

        history_header = HistoryHeader()
        history_header.creation_date = get_current_date_time()
        history_header.set_process(f'Initial file creation by {operator}')
        mtr.history_headers.append(history_header)

        mtr.process_thermograph(institution_name.upper(), instrument_type.lower(), metadata_file, data_file_path)

        os.chdir(data_folder_path)

        file_spec = mtr.generate_file_spec()
        mtr.file_specification = file_spec

        mtr.add_quality_flags()

        quality_header = QualityHeader()
        quality_header.quality_date = get_current_date_time()
        quality_header.add_quality_codes()
        mtr.quality_header = quality_header

        mtr.update_odf()

        odf_file_path = os.path.join(data_folder_path, file_spec + '.ODF')
        mtr.write_odf(odf_file_path, version = 2.0)
    

if __name__ == "__main__":
    main()
