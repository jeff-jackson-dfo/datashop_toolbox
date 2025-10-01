from datetime import datetime
import pytz
import pandas as pd
import os
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


    def start_date_time(self, df: pd.Series) -> datetime:
        """ Retrieve the first date-time value from the data frame. """
        start_date = datetime.strptime(df['date'].iloc[0], ThermographHeader.date_format)
        start_time = datetime.strptime(df['time'].iloc[0], ThermographHeader.time_format).time()
        start_date_time = datetime.combine(start_date, start_time)
        return start_date_time


    def end_date_time(self, df: pd.Series) -> datetime:
        """ Retrieve the last date-time value from the data frame. """
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

        if instrument_type == 'minilog':

            # Read the data lines from the MTR file.
            dfmtr = pd.read_table(mtrfile, sep = ',', header = None, encoding = 'iso8859_1', skiprows = 8)
            
            # rename the columns
            dfmtr.columns = ['date', 'time', 'temperature']

            mtr_dict['df'] = dfmtr

            # Get the instrument type and gauge (serial number) from the MTR file.
            with open(mtrfile, 'r', encoding = 'iso8859_1') as f:
                for i in range(8):
                    line = f.readline()
                    if 'Source Device:' in line:
                        info = line.split(':')[1]
                        inst_model = info.rsplit('-', 1)[0]
                        gauge = info.split('-')[-1].strip()
                        break
            
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
                # print(cnames)
                cname = cnames[0]
                # print(cname)
                if cname == "Date Time":
                    column_names.append("date_time")
                    cols_to_keep.append(i)
                elif cname == "Abs Pres":
                    column_names.append("pressure")
                    cols_to_keep.append(i)
                elif cname == "Temp":
                    column_names.append("temperature")
                    cols_to_keep.append(i)
                    toks = cnames[1].split(":")
                    inst_id = toks[0]
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
            mtr_dict['inst_id'] = inst_id
            mtr_dict['filename'] = mtrfile

        return mtr_dict


    @staticmethod
    def read_metadata(metafile: str, meta_source: str) -> pd.DataFrame:
        """
        Read a Metadata file and return a pandas DataFrame.

        :metafile: The file containing the metadata information.
        :meta_source: A string identifying the group who supplied the metadata. (currently "fsrs" or "bio")
        """

        if meta_source == 'fsrs':

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

        elif meta_source == 'bio':

            dfmeta = pd.read_excel(metafile)

        return dfmeta


def main():

    # Generate an empty MTR object.
    mtr = ThermographHeader()

    # operator = input('Enter the name of the operator: ')
    operator = 'Jeff Jackson'

    # meta_source = 'fsrs'
    meta_source = 'bio'

    if meta_source == 'fsrs':

        # Change to the drive's root folder
        os.chdir('\\')
        drive = os.getcwd()
        pathlist = ['DFO-MPO', 'DEV', 'MTR', 'FSRS_data_2013_2014', 'LFA_27_14']
        top_folder = os.path.join(drive, *pathlist)
        os.chdir(top_folder)

        # mtr_file = 'Bin4255RonFraser14.csv'
        # mtr_file = 'Minilog-T_4239_2014JayMacDonald_1.csv'
        mtr_file = 'Minilog-T_4655_201JordanWadden_1.csv'
        mtr_path = os.path.join(top_folder, mtr_file)
        print(f'\nProcessing MTR file: {mtr_path}\n')

        mydict = mtr.read_mtr(mtr_path, 'minilog')
        df = mydict['df']
        inst_model = mydict['inst_model']
        gauge = mydict['gauge']
        print(df.head())

        metadata_file = 'LatLong LFA 27_14.txt'
        metadata_path = os.path.join(top_folder, metadata_file)
        print(f'\nProcessing metadata file: {metadata_path}\n')
        
        meta = mtr.read_metadata(metadata_path, 'fsrs')

        meta_subset = meta[meta['gauge'] == int(gauge)]

        print(meta_subset.head())
        print('\n')

        mtr.cruise_header.country_institute_code = 1899
        cruise_year = df['date'].to_string(index=False).split('-')[0]
        cruise_number = f'BCD{cruise_year}603'
        mtr.cruise_header.cruise_number = cruise_number
        start_date = f"{mtr.start_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
        mtr.cruise_header.start_date = start_date
        end_date = f"{mtr.end_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
        mtr.cruise_header.end_date = end_date
        mtr.cruise_header.organization = 'FSRS'
        mtr.cruise_header.chief_scientist = 'Shannon Scott-Tibbetts'
        mtr.cruise_header.cruise_description = 'Fishermen and Scientists Research Society'
        
        mtr.event_header.data_type = 'MTR'
        mtr.event_header.event_qualifier1 = gauge
        mtr.event_header.event_qualifier2 = str(mtr.sampling_interval(df))
        mtr.event_header.creation_date = get_current_date_time()
        mtr.event_header.orig_creation_date = get_current_date_time()
        mtr.event_header.start_date_time = mtr.start_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
        mtr.event_header.end_date_time = mtr.end_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
        lat = meta_subset['latitude'].iloc[0]
        long = meta_subset['longitude'].iloc[0]
        if lat < 0:
            lat = lat * -1
        if long > 0:
            long = long * -1
        mtr.event_header.initial_latitude = lat
        mtr.event_header.initial_longitude = long
        mtr.event_header.end_latitude = lat
        mtr.event_header.end_longitude = long
        depth = meta_subset['depth']
        mtr.event_header.min_depth = min(depth)
        mtr.event_header.max_depth = max(depth)
        mtr.event_header.event_number = str(meta_subset['vessel_code'].iloc[0])
        mtr.event_header.sampling_interval = float(mtr.sampling_interval(df))
        
        if 'minilog' in inst_model.lower():
            mtr.instrument_header.instrument_type = 'MINILOG'
        mtr.instrument_header.model = inst_model
        mtr.instrument_header.serial_number = gauge
        mtr.instrument_header.description = 'Temperature data logger'

        history_header = HistoryHeader()
        history_header.creation_date = get_current_date_time()
        history_header.set_process(f'Initial file creation by {operator}')
        mtr.history_headers.append(history_header)

        new_df = mtr.create_sytm(df)

        mtr = mtr.populate_parameter_headers(new_df)

        for x, column in enumerate(new_df.columns):
            code = mtr.parameter_headers[x].code
            new_df.rename(columns={column: code}, inplace=True)

    elif meta_source == 'bio':

        # Change to the drive's root folder
        os.chdir('\\')
        drive = os.getcwd()
        # pathlist = ['DFO-MPO', 'DEV', 'MTR', 'BCD2015999']
        pathlist = ['DFO-MPO', 'DEV', 'MTR', '999_test']
        top_folder = os.path.join(drive, *pathlist)
        os.chdir(top_folder)

        metadata_file = 'MetaData_BCD2015999_Reformatted.xlsx'
        metadata_path = os.path.join(top_folder, metadata_file)
        print(f'\nProcessing metadata file: {metadata_path}\n')        
        meta = mtr.read_metadata(metadata_path, 'bio')
        print(meta.head())
        print('\n')

        # mtr_file = 'Baddeck_10011598.csv'  # BCD2015999
        # mtr_file = 'Liscomb_12m_353372_20160415_1.csv'  # BCD2015999
        mtr_file = 'BCD2018999_Hobo-u20-001-01_10231582_1_SouthBar_xxx_nov17_may18.csv'  # 99_Test
        mtr_path = os.path.join(top_folder, mtr_file)
        print(f'\nProcessing MTR file: {mtr_path}\n')

        if ThermographHeader.is_minilog_file(mtr_path):
            instrument_type = 'minilog'
            print('Processing Minilog data file')

        else:
            instrument_type = 'hobo'
            print('Processing Hobo data file')

        mydict = mtr.read_mtr(mtr_path, instrument_type)
        df = mydict['df']
        print(df.head())

        if instrument_type == 'minilog':
            inst_model = mydict['inst_model']
            gauge = mydict['gauge']
        elif instrument_type == 'hobo':
            inst_id = mydict['inst_id']

        mtr.cruise_header.country_institute_code = 1810
        cruise_year = df['date_time'].to_string(index=False).split('-')[0]
        cruise_number = f'BCD{cruise_year}999'
        mtr.cruise_header.cruise_number = cruise_number
        # start_date = f"{mtr.start_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
        # mtr.cruise_header.start_date = start_date
        # end_date = f"{mtr.end_date_time(df).strftime(r'%d-%b-%Y')} 00:00:00.00"
        # mtr.cruise_header.end_date = end_date
        # mtr.cruise_header.organization = 'DFO BIO'
        # mtr.cruise_header.chief_scientist = 'unknown'
        # mtr.cruise_header.cruise_description = ''
        
        mtr.event_header.data_type = 'MTR'
        # mtr.event_header.event_qualifier1 = gauge
        # mtr.event_header.event_qualifier2 = str(mtr.sampling_interval(df))
        # mtr.event_header.creation_date = get_current_date_time()
        # mtr.event_header.orig_creation_date = get_current_date_time()
        # mtr.event_header.start_date_time = mtr.start_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
        # mtr.event_header.end_date_time = mtr.end_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
        # lat = meta_subset['latitude'].iloc[0]
        # long = meta_subset['longitude'].iloc[0]
        # if lat < 0:
        #     lat = lat * -1
        # if long > 0:
        #     long = long * -1
        # mtr.event_header.initial_latitude = lat
        # mtr.event_header.initial_longitude = long
        # mtr.event_header.end_latitude = lat
        # mtr.event_header.end_longitude = long
        # depth = meta_subset['depth']
        # mtr.event_header.min_depth = min(depth)
        # mtr.event_header.max_depth = max(depth)
        # mtr.event_header.event_number = str(meta_subset['vessel_code'].iloc[0])
        # mtr.event_header.sampling_interval = float(mtr.sampling_interval(df))
        
        # if 'minilog' in inst_model.lower():
        #     mtr.instrument_header.instrument_type = 'MINILOG'
        # mtr.instrument_header.model = inst_model
        # mtr.instrument_header.serial_number = gauge
        # mtr.instrument_header.description = 'Temperature data logger'

        # history_header = HistoryHeader()
        # history_header.creation_date = get_current_date_time()
        # history_header.set_process(f'Initial file creation by {operator}')
        # mtr.history_headers.append(history_header)

        # new_df = mtr.create_sytm(df)

        # mtr = mtr.populate_parameter_headers(new_df)

        # for x, column in enumerate(new_df.columns):
        #     code = mtr.parameter_headers[x].code
        #     new_df.rename(columns={column: code}, inplace=True)

    file_spec = mtr.generate_file_spec()
    mtr.file_specification = file_spec

    mtr.update_odf()

    odf_file_path = os.path.join(top_folder, file_spec + '.ODF')
    mtr.write_odf(odf_file_path, version = 2.0)
    

if __name__ == "__main__":
    main()
