from datetime import datetime
import pandas as pd
import os
from typing import NoReturn, ClassVar

from odf_toolbox.lookup_parameter import lookup_parameter
from odf_toolbox.basehdr import BaseHeader
from odf_toolbox.odfhdr import OdfHeader
from odf_toolbox.parameterhdr import ParameterHeader
from odf_toolbox.historyhdr import HistoryHeader
from odf_toolbox import odfutils

class ThermographHeader(OdfHeader):
    """
    Mtr Class: subclass of OdfHeader.
    This class is responsible for storing the metadata and data associated with a moored thermograph (MTR).
    """
    date_format: ClassVar[str] = r'%Y-%m-%d'
    time_format: ClassVar[str] = r'%H:%M:%S'

    def __init__(self) -> NoReturn:
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
        df['dates'] = df['date'].apply(lambda x: datetime.strptime(x, ThermographHeader.date_format).date())
        df['dates'] = df['dates'].astype("string")
        df['times'] = df['time'].apply(lambda x: datetime.strptime(x, ThermographHeader.time_format).time())
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
            if ThermographHeader.check_datetime_format(df['date'][i], r"%d/%m/%Y"):
                meta_date_format = r"%d/%m/%Y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%m-%Y"):
                meta_date_format = "%d-%m-%Y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%b-%d-%y"):
                meta_date_format = "%b-%d-%y"
            elif ThermographHeader.check_datetime_format(df['date'][i], "%d-%b-%y"):
                meta_date_format = "%d-%b-%y"

            datetime_str = date_str + ' ' + time_str
            datetimes.append(datetime.strptime(datetime_str, ThermographHeader.date_format))

        df['datetime'] = datetimes

        # Check if the date and time columns are in the correct format.
        if not self.check_datetime_format(df['date'].iloc[0], ThermographHeader.date_format):
            raise ValueError(f"Date format is incorrect. Expected format: {ThermographHeader.date_format}")
        if not self.check_datetime_format(df['time'].iloc[0], ThermographHeader.time_format):
            raise ValueError(f"Time format is incorrect. Expected format: {ThermographHeader.time_format}")

        # Convert the date and time columns to datetime objects.
        df['date'] = pd.to_datetime(df['date'], format=ThermographHeader.date_format)
        df['time'] = pd.to_datetime(df['time'], format=ThermographHeader.time_format).dt.time
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
    def read_mtr(mtrfile: str) -> dict:
        """ Read an MTR data file and return a pandas DataFrame. """
        
        mtr_dict = dict()

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

        return mtr_dict

    @staticmethod
    def read_metadata(metafile: str) -> pd.DataFrame:
        """
        Read a Metadata file and return a pandas DataFrame.
        """
        # read the file
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
        dfmeta = ThermographHeader.fix_datetime(dfmeta)

        return dfmeta

def main():

    # Generate an empty MTR object.
    mtr = ThermographHeader()

    # operator = input('Enter the name of the operator: ')
    operator = 'Jeff Jackson'

    # Change to the drive's root folder
    os.chdir('\\')
    drive = os.getcwd()
    pathlist = ['DEV', 'MTR', 'FSRS_data_2013_2014', 'LFA_27_14']
    top_folder = os.path.join(drive, *pathlist)
    os.chdir(top_folder)

    mtr_file = 'Bin4255RonFraser14.csv'
    # mtr_file = 'Minilog-T_4239_2014JayMacDonald_1.csv'
    mtr_path = os.path.join(top_folder, mtr_file)
    print(f'\nProcessing MTR file: {mtr_path}\n')

    mydict = mtr.read_mtr(mtr_path)
    df = mydict['df']
    inst_model = mydict['inst_model']
    gauge = mydict['gauge']
    print(df.head())

    metadata_file = 'LatLong LFA 27_14.txt'
    metadata_path = os.path.join(top_folder, metadata_file)
    print(f'\nProcessing metadata file: {metadata_path}\n')
    
    meta = mtr.read_metadata(metadata_path)

    print(meta.head())
    print('\n')

    mtr.cruise_header.country_institute_code = 1899
    cruise_year = df['date'].to_string(index=False).split('-')[0]
    cruise_number = f'BCD{cruise_year}603'
    mtr.cruise_header.cruise_number = cruise_number
    start_date = mtr.start_date_time(df).strftime(r'%d-%b-%Y') + ' 00:00:00'
    mtr.cruise_header.start_date = start_date
    end_date = mtr.end_date_time(df).strftime(r'%d-%b-%Y') + ' 00:00:00'
    mtr.cruise_header.end_date = end_date
    mtr.cruise_header.organization = 'FSRS'
    mtr.cruise_header.chief_scientist = 'Shannon Scott-Tibbetts'
    mtr.cruise_header.cruise_description = 'Fishermen and Scientists Research Society'
    
    mtr.event_header.data_type = 'MTR'
    mtr.event_header.event_qualifier1 = gauge
    mtr.event_header.event_qualifier2 = str(mtr.sampling_interval(df))
    mtr.event_header.creation_date = odfutils.get_current_date_time()
    mtr.event_header.orig_creation_date = odfutils.get_current_date_time()
    mtr.event_header.start_date_time = mtr.start_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
    mtr.event_header.end_date_time = mtr.end_date_time(df).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
    mtr.event_header.initial_latitude = meta['latitude'].iloc[0]
    mtr.event_header.initial_longitude = meta['longitude'].iloc[0]
    mtr.event_header.end_latitude = meta['latitude'].iloc[0]
    mtr.event_header.end_longitude = meta['longitude'].iloc[0]
    mtr.event_header.min_depth = meta['depth'].iloc[0]
    mtr.event_header.max_depth = meta['depth'].iloc[0]
    mtr.event_header.event_number = str(meta['vessel_code'].iloc[0])
    mtr.event_header.sampling_interval = float(mtr.sampling_interval(df))
    
    if 'minilog' in inst_model.lower():
        mtr.instrument_header.instrument_type = 'MINILOG'
    mtr.instrument_header.model = inst_model
    mtr.instrument_header.serial_number = gauge
    mtr.instrument_header.description = 'Temperature data logger'

    history_header = HistoryHeader()
    history_header.creation_date = odfutils.get_current_date_time()
    history_header.set_process(f'Initial file creation by {operator}')
    mtr.history_headers.append(history_header)

    new_df = mtr.create_sytm(df)

    mtr = mtr.populate_parameter_headers(new_df)

    for x, column in enumerate(new_df.columns):
        code = mtr.parameter_headers[x].code
        new_df.rename(columns={column: code}, inplace=True)

    mtr.update_odf()

    file_spec = mtr.generate_file_spec()
    odf_file_path = os.path.join(top_folder, file_spec + '.ODF')
    mtr.write_odf(odf_file_path, version = 2.0)
    

if __name__ == "__main__":
    main()
