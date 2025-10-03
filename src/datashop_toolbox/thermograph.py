from datetime import datetime
import os
import pytz
import pandas as pd
from pathlib import Path
from typing import ClassVar

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import check_datetime, get_current_date_time
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.parameterhdr import ParameterHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.lookup_parameter import lookup_parameter

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


    def sampling_interval(self, df: pd.Series) -> int:
        """ Compute the time interval between the first two date-time values. """
        date1 = datetime.strptime(df['date'].iloc[0], ThermographHeader.date_format)
        time1 = datetime.strptime(df['time'].iloc[0], ThermographHeader.time_format).time()
        datetime1 = datetime.combine(date1, time1)
        date2 = datetime.strptime(df['date'].iloc[1], ThermographHeader.date_format)
        time2 = datetime.strptime(df['time'].iloc[1], ThermographHeader.time_format).time()
        datetime2 = datetime.combine(date2, time2)
        time_interval = datetime2 - datetime1
        time_interval = time_interval.seconds
        return time_interval


    def create_sytm(self, df: pd.DataFrame) -> pd.DataFrame:
        """ Updated the data frame with the proper SYTM column. """
        if 'date_time' in df.columns:
            df['dates'] = df['date_time'].map(lambda x: datetime.strptime(x, ThermographHeader.date_format).date())
            df['dates'] = df['dates'].astype("string")
            df['times'] = df['date_time'].map(lambda x: datetime.strptime(x, ThermographHeader.time_format).time())
            df['times'] = df['times'].astype("string")
            df['datetimes'] = df['dates'] + ' ' + df['times']
            df = df.drop(columns=['date', 'time', 'dates', 'times'], axis=1)
            df['datetimes'] = pd.to_datetime(df['datetimes'])
            df['sytm'] = df['datetimes'].map(lambda x: datetime.strftime(x, BaseHeader.SYTM_FORMAT)).str.upper()
            df = df.drop('datetimes', axis=1)
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
        toks = pos.split(' ')
        deg = float(toks[0])
        dm = float(toks[1])
        dd = deg + dm/60
        return dd

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

        if instrument_type == 'minilog':

            # Read the data lines from the MTR file.
            dfmtr = pd.read_table(mtrfile, sep = ',', header = None, encoding = 'iso8859_1', skiprows = 8)
            print(dfmtr.head())

            # rename the columns
            dfmtr.columns = ['date', 'time', 'temperature']

            # Get the instrument type and gauge (serial number) from the MTR file.
            with open(mtrfile, 'r', encoding = 'iso8859_1') as f:
                for i in range(8):
                    line = f.readline()
                    if 'Source Device:' in line:
                        info = line.split(':')[1]
                        inst_model = info.rsplit('-', 1)[0]
                        gauge = info.split('-')[-1].strip()
                        break
            
            mtr_dict['df'] = dfmtr
            mtr_dict['inst_model'] = inst_model
            mtr_dict['gauge'] = gauge
            mtr_dict['filename'] = mtrfile

        elif instrument_type == 'hobo':

            # Read the data lines from the MTR file.
            dfmtr = pd.read_table(mtrfile, sep = ',', header = 0, encoding = 'utf-8', skiprows = 1)
            
            # drop the row number column
            dfmtr.drop(columns=['#'], inplace=True)

            # Extract required info from columns and rename them with shorter names
            cols = dfmtr.columns
            column_names = []
            cols_to_keep = []
            for i, col in enumerate(cols):
                cnames = col.split(",")
                cname = cnames[0]
                if cname == "Date Time":
                    column_names.append("date_time")
                    cols_to_keep.append(i)
                elif cname == "Abs Pres":
                    column_names.append("pressure")
                    cols_to_keep.append(i)
                    toks = cnames[1].split(":")
                    inst_id = toks[1]
                elif cname == "Temp":
                    column_names.append("temperature")
                    cols_to_keep.append(i)
                elif cname == "DO conc":
                    column_names.append("dissolved_oxygen")
                    cols_to_keep.append(i)
                else: # ignore other columns
                    continue

            # Keep only selected columns
            dfmtr = dfmtr[dfmtr.columns[cols_to_keep]]

            # Rename the kept columns
            dfmtr.columns = column_names

            # halifax_tz = pytz.timezone("America/Halifax")
            dt_format_string = "%m/%d/%y %I:%M:%S %p"
            dt_halifax = dfmtr['date_time']
            datetime_objects = [datetime.strptime(dt_str, dt_format_string).astimezone(pytz.utc) for dt_str in dt_halifax]
            dfmtr['date_time'] = datetime_objects

            mtr_dict['df'] = dfmtr
            mtr_dict['gauge'] = inst_id
            mtr_dict['filename'] = mtrfile
            print(mtr_dict)

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

    def process_thermograph(self, institution_name: str, instrument_type: str, metadata_file_path: str, data_file_path: str):

        if institution_name == 'FSRS':

            print(f'\nProcessing Metadata file: {metadata_file_path}\n')
            meta = self.read_metadata(metadata_file_path, institution_name)
        
            print(f'\nProcessing Thermograph Data file: {data_file_path}\n')
            mydict = self.read_mtr(data_file_path, instrument_type)

            df = mydict['df']
            inst_model = mydict['inst_model']
            gauge = mydict['gauge']
            print(df.head())

            meta_subset = meta[meta['gauge'] == int(gauge)]
            print(meta_subset.head())
            print('\n')

            self.cruise_header.country_institute_code = 1899
            cruise_year = df['date'].to_string(index=False).split('-')[0]
            cruise_number = f'BCD{cruise_year}603'
            self.cruise_header.cruise_number = cruise_number
            start_date = f"{self.start_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.start_date = start_date
            end_date = f"{self.end_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.end_date = end_date
            self.cruise_header.organization = 'FSRS'
            self.cruise_header.chief_scientist = 'Shannon Scott-Tibbetts'
            self.cruise_header.cruise_description = 'Fishermen and Scientists Research Society'
            
            self.event_header.data_type = 'MTR'
            self.event_header.event_qualifier1 = gauge
            self.event_header.event_qualifier2 = str(self.sampling_interval(df))
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
            self.event_header.sampling_interval = float(self.sampling_interval(df))
            
            if 'minilog' in inst_model.lower():
                self.instrument_header.instrument_type = 'MINILOG'
            self.instrument_header.model = inst_model
            self.instrument_header.serial_number = gauge
            self.instrument_header.description = 'Temperature data logger'

            new_df = self.create_sytm(df)

            self.populate_parameter_headers(new_df)

            for x, column in enumerate(new_df.columns):
                code = self.parameter_headers[x].code
                new_df.rename(columns={column: code}, inplace=True)

        elif institution_name == 'BIO':

            print(f'\nProcessing Metadata file: {metadata_file_path}\n')
            meta = self.read_metadata(metadata_file_path, institution_name)

            print(f'\nProcessing Thermograph Data file: {data_file_path}\n')
            mydict = self.read_mtr(data_file_path, instrument_type)

            df = mydict['df']
            if 'inst_model' in mydict:
                inst_model = mydict['inst_model']
            gauge = mydict['gauge']
            print(df.head())

            # path = Path(metadata_file_path)
            meta_subset = meta[meta['ID'] == int(gauge)]

            if len(meta_subset) > 1:
                path1 = Path(data_file_path)
                # path2 = Path(str(meta['file_name']))
                print(f"{path1.stem}.hobo")
                meta_subset = meta[meta['file_name'] == f"{path1.stem}.hobo"]

            print(meta_subset.head())
            print('\n')

            matching_indices = meta[meta['ID'] == int(gauge)].index

            inst_model = meta_subset['Instrument'].iloc[0]

            self.cruise_header.country_institute_code = 1810
            if instrument_type == 'minilog':
                cruise_year = df['date'].to_string(index=False).split('-')[0]
            elif instrument_type == 'hobo':
                cruise_year = df['date_time'].to_string(index=False).split('-')[0]
            cruise_number = f'BCD{cruise_year}999'
            self.cruise_header.cruise_number = cruise_number
            start_date = f"{self.start_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.start_date = start_date
            end_date = f"{self.end_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
            self.cruise_header.end_date = end_date
            self.cruise_header.organization = 'DFO BIO'
            self.cruise_header.chief_scientist = 'Adam Drozdowski'
            self.cruise_header.cruise_description = ''
            
            self.event_header.data_type = 'MTR'
            self.event_header.event_qualifier1 = gauge
            if instrument_type == 'minilog':
                self.event_header.event_qualifier2 = str(self.sampling_interval(df))
            elif instrument_type == 'hobo':
                sampling_interval = float(meta_subset['Sampling@ (min)'].iloc[0]) * 60
                self.event_header.event_qualifier2 = str(meta_subset['Sampling@ (min)'].iloc[0])  
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
                lat = lat * -1
            if long > 0:
                long = long * -1
            self.event_header.initial_latitude = lat
            self.event_header.initial_longitude = long
            self.event_header.end_latitude = lat
            self.event_header.end_longitude = long
            depth = []
            dep_dep = str(meta_subset['dep_dep'].iloc[0])
            depth.append(dep_dep.split(' ')[0])
            dep_rec = str(meta_subset['dep_rec'].iloc[0])
            depth.append(dep_rec.split(' ')[0])
            self.event_header.min_depth = min(depth)
            self.event_header.max_depth = max(depth)
            self.event_header.event_number = f"{matching_indices[0]:03d}"
            if instrument_type == 'minilog':
                self.event_header.sampling_interval = float(self.sampling_interval(df))
            elif instrument_type == 'hobo':
                self.event_header.sampling_interval = sampling_interval
            
            if 'minilog' in inst_model.lower():
                self.instrument_header.instrument_type = 'MINILOG'
            self.instrument_header.model = inst_model
            self.instrument_header.serial_number = gauge
            self.instrument_header.description = 'Temperature data logger'

            new_df = self.create_sytm(df)

            self.populate_parameter_headers(new_df)

            for x, column in enumerate(new_df.columns):
                code = self.parameter_headers[x].code
                new_df.rename(columns={column: code}, inplace=True)
        
        return self


def main():

    # Generate an empty MTR object.
    mtr = ThermographHeader()

    operator = 'Jeff Jackson'

    # institution_name = 'FSRS'
    # instrument_type = 'minilog'
    # metadata_file = 'C:/DFO-MPO/DEV/MTR/FSRS_data_2013_2014/LatLong LFA 30_14.txt' # FSRS
    # data_folder_path = 'C:/DFO-MPO/DEV/MTR/FSRS_data_2013_2014/LFA 30/' # FSRS
    # data_file_path = 'C:/DFO-MPO/DEV/MTR/FSRS_data_2013_2014/LFA 30/Minilog-II-T_354633_2014jmacleod_1.csv' # FSRS

    institution_name = 'BIO'
    # instrument_type = 'minilog'
    instrument_type = 'hobo'
    metadata_file = 'C:/DFO-MPO/DEV/MTR/999_Test/MetaData_BCD2015999_Reformatted.xlsx' # BIO
    data_folder_path = 'C:/DFO-MPO/DEV/MTR/999_Test/'  # BIO
    # data_file_path = 'C:/DFO-MPO/DEV/MTR/999_Test/Liscomb_15m_352964_20160415_1.csv'  # BIO
    data_file_path = 'C:/DFO-MPO/DEV/MTR/999_Test/Baddeck_10011598.csv'  # BIO

    history_header = HistoryHeader()
    history_header.creation_date = get_current_date_time()
    history_header.set_process(f'Initial file creation by {operator}')
    mtr.history_headers.append(history_header)

    mtr.process_thermograph(institution_name, instrument_type, metadata_file, data_file_path)

    os.chdir(data_folder_path)

    file_spec = mtr.generate_file_spec()
    mtr.file_specification = file_spec

    mtr.update_odf()

    odf_file_path = os.path.join(data_folder_path, file_spec + '.ODF')
    mtr.write_odf(odf_file_path, version = 2.0)
    

if __name__ == "__main__":
    main()
