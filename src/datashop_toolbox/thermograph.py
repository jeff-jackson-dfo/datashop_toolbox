import math
import os
import posixpath
import re
import sys
from datetime import UTC, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import ClassVar

import pandas as pd
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from datashop_toolbox import select_metadata_file_and_data_folder
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.lookup_parameter import lookup_parameter
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.parameterhdr import ParameterHeader
from datashop_toolbox.qualityhdr import QualityHeader
from datashop_toolbox.validated_base import get_current_date_time


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


    @staticmethod
    def clean_lfa(value):
        try:
            # Try converting to float first
            f = float(value)
            # If it's a whole number, convert to int
            if f.is_integer():
                return int(f)
            else:
                # If float has decimal, convert to int (truncate)
                return int(f)
        except (ValueError, TypeError):
            # If conversion fails (string or NaN), leave as is
            return value

    @staticmethod
    def clean_soakday(value):
        try:
            # Try converting to float first
            f = float(value)
            # If it's a whole number, convert to int
            if f.is_integer():
                return int(f)
            else:
                # If float has decimal, convert to int (truncate)
                return int(f)
        except (ValueError, TypeError):
            # If conversion fails (string or NaN), leave as is
            return 0

    @staticmethod
    def load_meta_file(metafile):
        ext = Path(metafile).suffix.lower()
        if ext in [".txt", ".tsv"]:
            df = pd.read_table(
                metafile,
                encoding="iso8859_1",
                sep="\t",
                engine="python",
                skip_blank_lines=False,
            )
        
        elif ext == ".csv":
            df = pd.read_csv(metafile, encoding="iso8859_1")
        
        elif ext in [".xls", ".xlsx"]:
            df = pd.read_excel(metafile)
        
        else:
            raise ValueError(f"Unsupported metadata file type: {ext}")
        
        return df



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
            cols_to_drop = ['date', 'time', 'dates', 'times']
            df.columns = df.columns.str.strip().str.lower()
            df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
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

        if not date_times:
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
            if ThermographHeader.check_datetime_format(df['date'][i], "%Y-%m-%d"):
                meta_date_format = "%Y-%m-%d"
                date_note = "ISO format (YYYY-MM-DD)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%Y/%m/%d"):
                meta_date_format = "%Y/%m/%d"
                date_note = "ISO format with slashes (YYYY/MM/DD)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%d/%m/%Y"):
                meta_date_format = "%d/%m/%Y"
                date_note = "Day/Month/Year with slashes (DD/MM/YYYY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%d/%m/%y"):
                meta_date_format = "%d/%m/%y"
                date_note = "Day/Month/2-digit Year (DD/MM/YY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%m-%Y"):
                meta_date_format = "%d-%m-%Y"
                date_note = "Day-Month-Year with dashes (DD-MM-YYYY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%b-%d-%y"):
                meta_date_format = "%b-%d-%y"
                date_note = "Abbreviated month-Day-Year (Mon-DD-YY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%b-%d-%Y"):
                meta_date_format = "%b-%d-%Y"
                date_note = "Abbreviated month-Day-Year (Mon-DD-YYYY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%B-%d-%y"):
                meta_date_format = "%B-%d-%y"
                date_note = "Full month name-Day-Year (Month-DD-YY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%B-%d-%Y"):
                meta_date_format = "%B-%d-%Y"
                date_note = "Full month name-Day-Year (Month-DD-YYYY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%b-%y"):
                meta_date_format = "%d-%b-%y"
                date_note = "Day-Abbreviated month-Year (DD-Mon-YY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%b-%Y"):
                meta_date_format = "%d-%b-%Y"
                date_note = "Day-Abbreviated month-Year (DD-Mon-YYYY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%B-%y"):
                meta_date_format = "%d-%B-%y"
                date_note = "Day-Full month-Year (DD-Month-YY)"

            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%B-%Y"):
                meta_date_format = "%d-%B-%Y"
                date_note = "Day-Full month-Year (DD-Month-YYYY)"

            else:
                meta_date_format = None
                date_note = "Unrecognized date format"
                print(date_note)


            # Check the time format.
            if ThermographHeader.check_datetime_format(df['time'][i], "%H:%M:%S.%f"):
                meta_time_format = "%H:%M:%S.%f"
                time_note = "Time with fractional seconds (HH:MM:SS.microseconds)"

            elif ThermographHeader.check_datetime_format(df['time'][i], "%H:%M:%S"):
                meta_time_format = "%H:%M:%S"
                time_note = "Time with seconds (HH:MM:SS)"

            elif ThermographHeader.check_datetime_format(df['time'][i], "%H:%M"):
                meta_time_format = "%H:%M"
                time_note = "Time without seconds (HH:MM)"

            else:
                meta_time_format = None
                time_note = "Unrecognized or missing time format"
                print(time_note)


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
        with open(file_path, encoding="utf-8", errors="ignore") as f:
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
            skiprows = 8
            with open(mtrfile, encoding='iso8859_1') as f:
                first_lines = [next(f) for _ in range(skiprows * 2)]  # read first skiprows*2 lines
                for i, line in enumerate(first_lines):  # Read up to twice the default skiprows
                    stripped = line.strip()
                    # Detect the first data-like line.
                    # Typically starts with a date (e.g., "11/03/2014") or similar pattern 11-03-2014
                    if re.match(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})", stripped):
                        skiprows = i
                        break
                    elif stripped.startswith('* Date(yyyy-mm-dd),') or stripped.startswith('Date(yyyy-mm-dd),'):
                        skiprows = i+1
                        break
            
            
            # Read the data lines from the MTR file
            dfmtr = pd.read_table(mtrfile, sep = ',', header = None, encoding = 'iso8859_1', skiprows = skiprows)
            # print(dfmtr.head())

            # rename the columns
            dfmtr.columns = ['date', 'time', 'temperature']

            # Get the instrument type and gauge (serial number) from the MTR file.
            inst_model, gauge, delTime_UTC = None, None, None
            with open(mtrfile, encoding = 'iso8859_1') as f:
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
            

            #--- Safety defaults: ask user if not found ---
            if inst_model is None or gauge is None:
                msg_text = f"""❌ Instrument model or Gauge number missing in MTR file header:
                    {mtrfile}
                    Example MTR file header info:
                    Source File: Minilog-II-T_351009_20130923_1.vld
                    Source Device: Minilog-II-T-351009
                    Study Description: Anonymous
                    Minilog Initialized: 2013-03-26 09:36:11 (UTC-3)
                    Study Start Time: 2013-03-26 10:00:00
                    Study Stop Time: 2013-09-23 09:00:00
                    Sample Interval: 00:00:00
                    """
                print(msg_text)
                print("⚠️ Alternate Option: Attempting to extract instrument model and gauge from filename...")
                filename = Path(mtrfile).name
                pattern = r"^(Minilog-[^_]+)_(\d+)_"
                match = re.search(pattern, filename)
                if match:
                    inst_model = match.group(1)
                    gauge = match.group(2)
                    print(f"✅ Extracted instrument model: {inst_model}, gauge: {gauge} from filename.")
                    print("Please check the above raw MTR file header info in the file" +
                          " and ensure it matches the extracted values.")

                else:
                    print("⚠️ Unable to extract instrument model and gauge from filename.")
                    print("You will be prompted to quit the application and restart the process" +
                          " after correcting the MTR file.")
                    app = QApplication.instance()
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setWindowTitle("Missing Instrument or Gauge model")
                    msg.setText(msg_text)
                    msg.setInformativeText("Please check the above raw MTR file header if present" +
                                           " and correct the file.")
                    msg.setInformativeText("You must quit the application and restart the process " +
                                           "after correcting the MTR file.") 
                    quit_btn = msg.addButton("Quit App", QMessageBox.ButtonRole.RejectRole)
                    ok_btn = msg.addButton("Ok", QMessageBox.ButtonRole.AcceptRole)
                    msg.setDefaultButton(ok_btn)
                    msg.exec()
                    if msg.clickedButton() == quit_btn:
                        app.quit()
                    if msg.clickedButton() == ok_btn:
                        raise Exception("MissingMetaHeaderinMTRReading: Missing instrument model or " +
                                        f"gauge number in file {mtrfile}.")


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
                dfmtr['DateTime'] = pd.to_datetime(dfmtr['date'].astype(str) + ' ' + dfmtr['time'].astype(str),
                                    format="mixed",
                                    dayfirst=True)
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
            skiprows = 1
            pattern = re.compile(
                r"^\s*\d+,\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s*[APap][Mm],"
                )
            with open(mtrfile, encoding='iso8859_1') as f:
                first_lines = [next(f) for _ in range(skiprows * 4)]  # read first skiprows*4 lines
                for i, line in enumerate(first_lines):  # Read up to four times the default skiprows
                    stripped = line.strip()
                    # Case 1: Header line (with column names)
                    if stripped.startswith('"#",') or stripped.startswith('"#","Date Time') or stripped.startswith('#,date_time'):  # noqa: E501
                        skiprows = i
                        break
                    #Case 2: Direct data line (starts with record number, date-time, etc.)
                    elif pattern.match(stripped):
                        skiprows = i - 1 if i > 0 else 0  # avoid negative skiprows
                        break

            # Read the data lines from the MTR file.
            dfmtr = pd.read_table(mtrfile, sep = ',', header = 0, encoding = 'utf-8', skiprows = skiprows)
            
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
            datetime.strptime(dt_str, dt_format_string).replace(tzinfo=local_tz).astimezone(UTC)
                            for dt_str in dt_original]
            dfmtr['date_time'] = datetime_objects

            ## Extract inst_model from file name if possible
            basefilename = os.path.basename(mtrfile)
            name_lower = basefilename.lower()
            inst_model = None
            # Priority order matters (more specific first)
            if re.search(r"hobo[\s\-]?u20", name_lower):
                inst_model = "hobo U20"
            elif re.search(r"hobo[\s\-]?u22", name_lower):
                inst_model = "hobo U22"
            elif re.search(r"hobou20", name_lower):
                inst_model = "hobo U20"
            elif re.search(r"hobou22", name_lower):
                inst_model = "hobo U22"
            elif re.search(r"\bhobo\b", name_lower):
                inst_model = "hobo"

            ## Assemble results ---
            mtr_dict['df'] = dfmtr
            mtr_dict['inst_model'] = inst_model
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
            dfmeta = ThermographHeader.load_meta_file(metafile)

            dfmeta = dfmeta.dropna(how="all")  # Drop rows where all elements are NaN

            # Change some column types.
            dfmeta['LFA'] = dfmeta['LFA'].apply(ThermographHeader.clean_lfa)
            dfmeta['Soak Days'] = dfmeta['Soak Days'].apply(ThermographHeader.clean_soakday)
            dfmeta['Vessel Code'] = dfmeta['Vessel Code'].astype('Int64')
            dfmeta['Gauge'] = dfmeta['Gauge'].astype('Int64')
            

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

        elif institution.strip().upper() in ('BIO', 'DFO BIO'):

            dfmeta = pd.read_excel(metafile)

        return dfmeta


    def process_thermograph(self, institution_name: str, instrument_type: str, 
                            metadata_file_path: str, data_file_path: str, user_input_metadata: dict) -> None:

        if institution_name == 'FSRS':
            # Get user input metadata values with defaults
            organization = user_input_metadata.get("organization") or "FSRS"
            chief_scientist = user_input_metadata.get("chief_scientist") or "SHANNON SCOTT-TIBBETTS"
            cruise_description = user_input_metadata.get("cruise_description") or "FISHERMEN AND SCIENTISTS RESEARCH SOCIETY"  # noqa: E501
            platform_name = user_input_metadata.get("platform_name") or "FSRS CRUISE DATA (NO ICES CODE)"
            country_code = user_input_metadata.get("country_code") or "1899"

            # print(f'\nProcessing Metadata file: {metadata_file_path}\n')
            meta = self.read_metadata(metadata_file_path, institution_name)
        
            # print(f'\nProcessing Thermograph Data file: {data_file_path}\n')
            mydict = self.read_mtr(data_file_path, instrument_type)
            # Extract data frame and gauge from the returned dictionary.
            df = mydict['df']
            gauge = mydict['gauge']
            # print(df.head())
            meta_subset = meta[meta['gauge'] == int(gauge)]
            # print(meta_subset.head())
            # print('\n')

            inst_model = mydict.get('inst_model')
            if not inst_model:
                if instrument_type.lower() == 'minilog':
                    inst_model = (
                        meta_subset.get('Instrument', pd.Series(['minilog II'])).iloc[0]
                        or "minilog II"
                    )
                elif instrument_type.lower() == 'hobo':
                    inst_model = (meta_subset.get('Instrument', pd.Series(['hobo'])).iloc[0]
                                or "hobo")
            
            self.cruise_header.country_institute_code = country_code
            if instrument_type == 'minilog':
                cruise_year = df['date'].to_string(index=False).split('-')[0]
            elif instrument_type == 'hobo':
                cruise_year = df['date_time'].to_string(index=False).split('-')[0]
            cruise_number = user_input_metadata.get("cruise_number") or f'BCD{cruise_year}603'
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
            organization = user_input_metadata.get("organization") or "DFO BIO"
            chief_scientist = user_input_metadata.get("chief_scientist") or "ADAM DROZDOWSKI"
            cruise_description = user_input_metadata.get("cruise_description") or "LONG TERM TEMPERATURE MONITORING PROGRAM (LTTMP)"  # noqa: E501
            platform_name = user_input_metadata.get("platform_name") or "BIO CRUISE DATA (NO ICES CODE)"
            country_code = user_input_metadata.get("country_code") or "1810"

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
                    meta_subset = meta_subset.copy()
                    meta_subset["file_name_norm"] = meta_subset["file_name"].astype(str).str.lower()
                    matched = meta_subset[meta_subset["file_name_norm"] == hobo_file]
                    if matched.empty:
                        matched = meta_subset[
                            meta_subset["file_name_norm"].str.replace(".hobo", "", regex=False) == path1.stem.lower()
                        ]
                    if not matched.empty:
                        meta_subset = matched
                    meta_subset.drop(columns="file_name_norm", inplace=True)
                    
                else:
                    minilog_file = f"{path1.stem}.vld".lower()
                    # print(minilog_file)
                    meta_subset = meta_subset.copy()
                    meta_subset["file_name_norm"] = meta_subset["file_name"].astype(str).str.lower()
                    matched = meta_subset[meta_subset["file_name_norm"] == minilog_file]
                    if matched.empty:
                        matched = meta_subset[
                            meta_subset["file_name_norm"].str.replace(".vld", "", regex=False) == path1.stem.lower()
                        ]
                    if not matched.empty:
                        meta_subset = matched
                    meta_subset.drop(columns="file_name_norm", inplace=True)
                    
                    
            # print(meta_subset.head())
            # print('\n')

            matching_indices = meta_subset[meta_subset['ID'] == gauge].index


            inst_model = mydict.get('inst_model')
            if not inst_model:
                if instrument_type.lower() == 'minilog':
                    inst_model = (
                        meta_subset.get('Instrument', pd.Series(['minilog II'])).iloc[0]
                        or "minilog II"
                    )
                elif instrument_type.lower() == 'hobo':
                    inst_model = (meta_subset.get('Instrument', pd.Series(['hobo'])).iloc[0]
                                or "hobo")
            
            self.cruise_header.country_institute_code = country_code
            if instrument_type == 'minilog':
                cruise_year = df['date'].to_string(index=False).split('-')[0]
            elif instrument_type == 'hobo':
                cruise_year = df['date_time'].to_string(index=False).split('-')[0]
            cruise_number = user_input_metadata.get("cruise_number") or f'BCD{cruise_year}999'
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

        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        select_inputs = select_metadata_file_and_data_folder.MainWindow()
                
        def on_accept():
            # Read values from UI
            metadata_file_path = select_inputs.metadata_file
            input_data_folder_path = select_inputs.input_data_folder
            output_data_folder_path = select_inputs.output_data_folder
            operator = select_inputs.line_edit_text.strip()
            institution = select_inputs.institution.upper()
            instrument = select_inputs.instrument.lower()
            user_input_metadata = select_inputs.user_input_meta

            if not operator:
                operator, ok = QInputDialog.getText(
                    select_inputs,
                    "Data processor Name Required",
                    "Please enter the name of the analyst performing the data processing:",
                )
                if not ok or not operator.strip():
                    print("❌ Operator name is required. Batch cancelled.")
                    return

            if not metadata_file_path or not input_data_folder_path or not output_data_folder_path:
                print(
                    "❌ Missing metadata, input or output folder. Please try again or exit program."
                )
                return

            if institution == "BIO":
                match = re.search(r"BCD\d+999", metadata_file_path, re.IGNORECASE)
                if match:
                    cruise_number = match.group(0)
                elif "_" in metadata_file_path:
                    cruise_number = metadata_file_path.split("_")[1].split(".")[0]
                else:
                    cruise_number = metadata_file_path

                batch_id = f"MTR_{cruise_number}_{instrument}_{institution}"

            elif institution == "FSRS":
                pattern = r"\b(LFA)\b\s+(\d+_\d+)"
                match = re.search(pattern, metadata_file_path, re.IGNORECASE)
                if match:
                    cruise_number = match.group(1).upper() + "-" + match.group(2).replace("_", "")
                else:
                    cruise_number = metadata_file_path
                batch_id = f"MTR_{cruise_number}_{instrument}_{institution}"

            else:
                batch_id = f"MTR_{Path.name(metadata_file_path).split('.')[0]}_{instrument}_{institution}"  

        
            select_inputs.result = {
            "metadata_file_path": metadata_file_path,
            "input_data_folder_path": input_data_folder_path,
            "output_data_folder_path": output_data_folder_path,
            "operator": operator,
            "institution": institution,
            "instrument": instrument,
            "batch_id":batch_id,
            "user_input_metadata": user_input_metadata,
            }

            select_inputs.close()
            app.quit()
                
        def on_reject():
            select_inputs.close()
            app.quit()
                
        select_inputs.buttonBox.accepted.connect(on_accept)
        select_inputs.buttonBox.rejected.connect(on_reject)
        select_inputs.show()
        app.exec()
        
        result = getattr(select_inputs, "result", None)

        if result:
            metadata_file_path = result['metadata_file_path']
            input_data_folder_path = result['input_data_folder_path']
            output_data_folder_path = result['output_data_folder_path']
            operator = result['operator']
            institution = result['institution']
            instrument = result['instrument']
            batch_id = result['batch_id']
            user_input_metadata = result['user_input_metadata']

            os.chdir(input_data_folder_path)
            all_files = list(Path('.').glob("*.csv"))

            base_name_output = "Step_1_Create_ODF"
            out_folder_path = Path(output_data_folder_path).resolve()
            out_odf_path = Path(out_folder_path / base_name_output)
            odf_path = Path(out_odf_path).resolve()
            odf_path.mkdir(parents=True, exist_ok=True)

            for idx, file_name in enumerate(all_files, start=1):
                file_name = file_name.name
                mtr_path = posixpath.join(input_data_folder_path, file_name)

                mtr = ThermographHeader()

                history_header = HistoryHeader()
                history_header.creation_date = get_current_date_time()
                history_header.set_process(f"INITIAL FILE CREATED BY {operator.upper()}")
                mtr.history_headers.append(history_header)

                mtr.process_thermograph(
                    institution, instrument, metadata_file_path, mtr_path, user_input_metadata
                )

                file_spec = mtr.generate_file_spec()
                mtr.file_specification = file_spec
                mtr.add_quality_flags()

                quality_header = QualityHeader()
                quality_header.quality_date = get_current_date_time()
                quality_header.add_quality_codes()
                mtr.quality_header = quality_header

                mtr.update_odf()

                odf_file_path = posixpath.join(odf_path, file_spec + ".ODF")
                mtr.write_odf(odf_file_path, version=2.0)
                
                # Reset the shared log list
                BaseHeader.reset_log_list()
                
                if idx == len(all_files):
                    print(f"=== End processing MTR file {idx} of {len(all_files)}: {file_name} ===")
                    print(f"✅ [{idx}/{len(all_files)}] Batch end : {batch_id} ✅ \n")

    else:
        
        institution_List = ['BIO', 'FSRS']
        instrument_List = ['minilog', 'hobo']
        user_input_metadata_BIO = {'organization': 'DFO BIO', 
                               'chief_scientist': 'ADAM DROZDOWSKI', 
                               'cruise_description': 'LONG TERM TEMPERATURE MONITORING PROGRAM (LTTMP)', 
                               'platform_name': 'BIO CRUISE DATA (NO ICES CODE)', 
                               'country_code': '1810'}
        user_input_metadata_FSRS = {'organization': 'FSRS', 
                        'chief_scientist': 'SHANNON SCOTT-TIBBETTS', 
                        'cruise_description': 'FISHERMEN  AND SCIENTISTS RESEARCH SOCIETY', 
                        'platform_name': 'FSRS CRUISE DATA (NO ICES CODE)', 
                        'country_code': '1899'}
        user_input_metadata_List = [user_input_metadata_BIO, user_input_metadata_FSRS]

        ## User Need to Change it here ##############
        metadata_file_path = r"C:\Users\ROYPR\Desktop\DFO-ODIS-SSPPI\ViewMTR_Data\hobo\MTR_Hobos_MetaData_BCD2014999.xlsx"  # noqa: E501
        input_data_folder_path= r"C:\Users\ROYPR\Desktop\DFO-ODIS-SSPPI\ViewMTR_Data\hobo\MTR_Hobos_RAW_CSV"
        output_data_folder_path = r"C:\Users\ROYPR\Desktop\DFO-ODIS-SSPPI\ViewMTR_Data\hobo"
        operator = "DFO-User"
        institution = institution_List[0]
        instrument = instrument_List[1]
        batch_id = "XXXX-YYYY"
        user_input_metadata = user_input_metadata_List[0]

        ### ****************************************  #######
        def normalize_path(path: str) -> str:
            if not isinstance(path, str):
                raise TypeError(f"path must be str, got {type(path).__name__}")
            return path.replace("\\", "/")


        metadata_file_path = normalize_path(metadata_file_path)
        input_data_folder_path = normalize_path(input_data_folder_path)
        output_data_folder_path = normalize_path(output_data_folder_path)

        select_inputs = {
            "metadata_file_path": metadata_file_path,
            "input_data_folder_path": input_data_folder_path,
            "output_data_folder_path": output_data_folder_path,
            "operator": operator,
            "institution": institution,
            "instrument": instrument,
            "batch_id":batch_id,
            "user_input_metadata": user_input_metadata,
            }
        
        if select_inputs:
            metadata_file_path = select_inputs['metadata_file_path']
            input_data_folder_path = select_inputs['input_data_folder_path']
            output_data_folder_path = select_inputs['output_data_folder_path']
            operator = select_inputs['operator']
            institution = select_inputs['institution']
            instrument = select_inputs['instrument']
            batch_id = select_inputs['batch_id']
            user_input_metadata = select_inputs['user_input_metadata']

            os.chdir(input_data_folder_path)
            all_files = list(Path('.').glob("*.csv"))

            base_name_output = "Step_1_Create_ODF"
            out_folder_path = Path(output_data_folder_path).resolve()
            out_odf_path = Path(out_folder_path / base_name_output)
            odf_path = Path(out_odf_path).resolve()
            odf_path.mkdir(parents=True, exist_ok=True)

            for idx, file_name in enumerate(all_files, start=1):
                file_name = file_name.name
                mtr_path = posixpath.join(input_data_folder_path, file_name)

                mtr = ThermographHeader()

                history_header = HistoryHeader()
                history_header.creation_date = get_current_date_time()
                history_header.set_process(f"INITIAL FILE CREATED BY {operator.upper()}")
                mtr.history_headers.append(history_header)

                mtr.process_thermograph(
                    institution, instrument, metadata_file_path, mtr_path, user_input_metadata
                )

                file_spec = mtr.generate_file_spec()
                mtr.file_specification = file_spec
                mtr.add_quality_flags()

                quality_header = QualityHeader()
                quality_header.quality_date = get_current_date_time()
                quality_header.add_quality_codes()
                mtr.quality_header = quality_header

                mtr.update_odf()

                odf_file_path = posixpath.join(odf_path, file_spec + ".ODF")
                mtr.write_odf(odf_file_path, version=2.0)              

                # Reset the shared log list
                BaseHeader.reset_log_list()
                
                if idx == len(all_files):
                    print(f"=== End processing MTR file {idx} of {len(all_files)}: {file_name} ===")
                    print(f"✅ [{idx}/{len(all_files)}] Batch end : {batch_id} ✅ \n")


if __name__ == "__main__":
   
    main()
