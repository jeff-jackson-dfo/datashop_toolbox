from datetime import datetime
import pandas as pd
import re

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.compasshdr import CompassCalHeader
from datashop_toolbox.cruisehdr import CruiseHeader
from datashop_toolbox.eventhdr import EventHeader
from datashop_toolbox.generalhdr import GeneralCalHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.instrumenthdr import InstrumentHeader
from datashop_toolbox.meteohdr import MeteoHeader
from datashop_toolbox.parameterhdr import ParameterHeader
from datashop_toolbox.polynomialhdr import PolynomialCalHeader
from datashop_toolbox.qualityhdr import QualityHeader
from datashop_toolbox.recordhdr import RecordHeader
# from datashop_toolbox.records import DataRecords
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict, add_commas, split_string_with_quotes, clean_strings, read_file_lines, find_lines_with_text, split_lines_into_dict, check_string
from typing import Self, Optional, List
from pydantic import Field, field_validator

class OdfHeader(ValidatedBase, BaseHeader):
    """
    Odf Header Class
    This class is responsible for storing the metadata associated with an ODF object (file).
    It contains a series of header subclasses that store metadata associated with various aspects of the ODF object.
    """
    file_specification: str = ''
    odf_specification_version: float = BaseHeader.NULL_VALUE

    cruise_header: CruiseHeader = Field(default_factory=CruiseHeader)
    event_header: EventHeader = Field(default_factory=EventHeader)
    meteo_header: Optional[MeteoHeader] = None
    instrument_header: InstrumentHeader = Field(default_factory=InstrumentHeader)
    quality_header: Optional[QualityHeader] = None
    
    general_cal_headers: List[GeneralCalHeader] = Field(default_factory=list)
    compass_cal_headers: List[CompassCalHeader] = Field(default_factory=list)
    polynomial_cal_headers: List[PolynomialCalHeader] = Field(default_factory=list)
    history_headers: List[HistoryHeader] = Field(default_factory=list)
    parameter_headers: List[ParameterHeader] = Field(default_factory=list)

    record_header: RecordHeader = Field(default_factory=RecordHeader)
    # data: DataRecords = Field(default_factory=DataRecords)

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__
        BaseHeader.__init__(self, config) # Ensures logger and config are set
        self.cruise_header.set_logger_and_config(self.logger, self.config)
        self.event_header.set_logger_and_config(self.logger, self.config)
        self.instrument_header.set_logger_and_config(self.logger, self.config)
        if self.quality_header is not None:
            self.quality_header.set_logger_and_config(self.logger, self.config)
        if self.meteo_header is not None:
            self.meteo_header.set_logger_and_config(self.logger, self.config)
        self.record_header.set_logger_and_config(self.logger, self.config)

    def log_odf_message(self, message: str, type: str = 'self'):
        assert isinstance(message, str), "Input argument 'message' must be a string."
        assert isinstance(type, str), "Input argument 'type' must be a string."
        if type == "self":
            self.logger.info(f"In ODF Header field {message}")
            self.shared_log_list.append(f"In ODF Header field {message}")
        elif type == "base":
            self.logger.info(message)
            self.shared_log_list.append(message)

    # -------------------
    # Validators
    # -------------------
    @field_validator("file_specification")
    def validate_file_specification(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("file_specification cannot be empty.")
        return v

    # @field_validator("general_cal_headers", "compass_cal_headers",
    #                  "polynomial_cal_headers", "history_headers", "parameter_headers")
    @field_validator("compass_cal_headers", "history_headers", "parameter_headers")
    def ensure_list_items_are_models(cls, v, field):
        if not all(hasattr(item, "print_object") for item in v):
            raise TypeError(
                f"All elements in {field.name} must be valid header objects "
                f"with a 'print_object' method."
            )
        return v

    @field_validator("quality_header", "meteo_header")
    def check_optional_headers(cls, v, field):
        if v is not None and not hasattr(v, "print_object"):
            raise TypeError(f"{field.name} must be None or a valid header object.")
        return v
    
    def populate_object(self, odf_dict: dict):
        assert isinstance(odf_dict, dict), "Input argument 'value' must be a dict."        
        for key, value in odf_dict.items():
            match key.strip():
                case 'FILE_SPECIFICATION':
                    self._file_specification = value.strip()
                case 'ODF_SPECIFICATION_VERSION':
                    self._odf_specification_version = value.strip()
        return self

    def print_object(self, file_version: float = 2.0) -> str:
        assert isinstance(file_version, float), "Input argument 'file_version' must be a float."

        # Add modifications to the OdfHeader instance before outputting it
        # self.add_log_to_history()

        odf_output = ""

        # List of optional headers
        optional_headers = [
            ("meteo_header", self.meteo_header),
            ("quality_header", self.quality_header)
        ]

        # Helper to add header outputs
        def add_header_output(header, use_commas=True):
            if use_commas:
                return add_commas(header.print_object())
            return header.print_object()

        if file_version == 2.0:
            self.odf_specification_version = 2.0
            odf_output = "ODF_HEADER,\n"
            odf_output += f"  FILE_SPECIFICATION = {self.file_specification},\n"
            odf_output += add_commas(self.cruise_header.print_object())
            odf_output += add_commas(self.event_header.print_object())

            for name, header in optional_headers:
                if header is not None:
                    odf_output += add_header_output(header)

            odf_output += add_commas(self.instrument_header.print_object())

            for cal in self.general_cal_headers + self.polynomial_cal_headers + self.compass_cal_headers:
                odf_output += add_commas(cal.print_object())

            for hist in self.history_headers:
                odf_output += add_commas(hist.print_object())

            for param in self.parameter_headers:
                odf_output += add_commas(param.print_object())

            odf_output += add_commas(self.record_header.print_object())
            # odf_output += "-- DATA --\n"
            # odf_output += self.data.print_object_old_style()

        elif file_version >= 3:
            self.odf_specification_version = 3.0
            odf_output = "ODF_HEADER\n"
            odf_output += f"  FILE_SPECIFICATION = {self.file_specification}\n"
            odf_output += f"  ODF_SPECIFICATION_VERSION = {self.odf_specification_version}\n"
            odf_output += self.cruise_header.print_object()
            odf_output += self.event_header.print_object()

            for name, header in optional_headers:
                if header is not None:
                    odf_output += add_header_output(header, use_commas=False)

            odf_output += self.instrument_header.print_object()

            for cal in self.general_cal_headers + self.polynomial_cal_headers + self.compass_cal_headers:
                odf_output += cal.print_object()

            for hist in self.history_headers:
                odf_output += hist.print_object()

            for param in self.parameter_headers:
                odf_output += param.print_object()

            odf_output += self.record_header.print_object()
            # odf_output += "-- DATA --\n"
            # odf_output += self.data.print_object()

        return odf_output

    # def read_header(odf: Type[newOdfHeader], lines: list) -> newOdfHeader:
    def read_odf(self, odf_file_path: str):
        assert isinstance(odf_file_path, str), "Input argument 'odf_file_path' must be a string."
        file_lines = read_file_lines(odf_file_path)

        text_to_find = "_HEADER"
        if isinstance(file_lines, list):
            header_lines_with_indices = find_lines_with_text(file_lines, text_to_find)
        header_starts_list = list()
        header_indices = list()
        header_names = list()
        for index, line in header_lines_with_indices:
            header_indices.append(index)
            header_names.append(line.strip(" ,"))
            header_starts_list.append([index, line.strip(" ,")])
        header_blocks_df = pd.DataFrame(header_starts_list, columns=["index", "name"])

        data_line = '-- DATA --'

        if isinstance(file_lines, list):
            data_lines_with_indices = find_lines_with_text(file_lines, data_line)
        else:
            print(file_lines)  # or handle the error string appropriately

        if isinstance(file_lines, list):
            data_lines_with_indices = find_lines_with_text(file_lines, data_line)
        data_lines = List[str]
        data_line_start = -1
        for index, line in data_lines_with_indices:
            data_line_start = index + 1

        # Separate the header and data lines
        header_lines = file_lines[:data_line_start - 1]
        data_lines = file_lines[data_line_start:]

        # Get the line range for the list of fields in each header block
        if isinstance(header_lines, list):
            header_lines = clean_strings(header_lines)
        ndf = len(header_blocks_df)
        header_field_range = pd.DataFrame(columns=["Name", "Start", "End"])
        for i in range(ndf):
            header_field_range.at[i, 'Name'] = header_blocks_df.at[i, 'name']
            header_field_range.at[i, 'Start'] = header_blocks_df.at[i, 'index'] + 1
        for i in range(ndf):
            if 0 < i < ndf - 1:
                header_field_range.at[i - 1, 'End'] = header_blocks_df.at[i, 'index'] - 1
            elif i == ndf - 1:
                header_field_range.at[i - 1, 'End'] = header_blocks_df.at[i, 'index'] - 1
                header_field_range.at[i, 'End'] = data_line_start - 1

        # Loop through the header lines, populating the OdfHeader object as it goes.
        for i in range(ndf):
            header_block = str(header_blocks_df.at[i, 'name'])
            x = header_field_range.at[i, 'Start']
            y = header_field_range.at[i, 'End']
            block_lines = list(header_lines[x:y + 1])
            match header_block:
                case "COMPASS_CAL_HEADER":
                    compass_cal_header = CompassCalHeader()
                    compass_cal_header.populate_object(block_lines)
                    self.compass_cal_headers.append(compass_cal_header)
                case "CRUISE_HEADER":
                    self.cruise_header = self.cruise_header.populate_object(block_lines)
                case "EVENT_HEADER":
                    self.event_header = self.event_header.populate_object(block_lines)
                case "GENERAL_CAL_HEADER":
                    general_cal_header = GeneralCalHeader()
                    general_cal_header.populate_object(block_lines)
                    self.general_cal_headers.append(general_cal_header)
                case "HISTORY_HEADER":
                    history_header = HistoryHeader()
                    history_header.populate_object(block_lines)
                    self.history_headers.append(history_header)
                case "INSTRUMENT_HEADER":
                    self.instrument_header = self.instrument_header.populate_object(block_lines)
                case "METEO_HEADER":
                    self.meteo_header = MeteoHeader()
                    self.meteo_header.populate_object(block_lines)
                case "ODF_HEADER":
                    for header_line in block_lines:
                        tokens = header_line.split('=', maxsplit=1)
                        header_fields = split_lines_into_dict(tokens)
                        self.populate_object(header_fields)
                case "PARAMETER_HEADER":
                    parameter_header = ParameterHeader()
                    parameter_header.populate_object(block_lines)
                    self.parameter_headers.append(parameter_header)
                case "POLYNOMIAL_CAL_HEADER":
                    polynomial_cal_header = PolynomialCalHeader()
                    polynomial_cal_header.populate_object(block_lines)
                    self.polynomial_cal_headers.append(polynomial_cal_header)
                case "QUALITY_HEADER":
                    self.quality_header = QualityHeader()
                    self.quality_header.populate_object(block_lines)
                case "RECORD_HEADER":
                    self.record_header = RecordHeader()
                    self.record_header.populate_object(block_lines)
        parameter_list = list()
        parameter_formats = dict()
        for parameter in self.parameter_headers:
            parameter_code = parameter.code.strip("'")
            parameter_list.append(parameter_code)
            if parameter_code[0:4] == 'SYTM':
                parameter_formats[parameter_code] = f"{parameter.print_field_width}"
            else:
                parameter_formats[parameter_code] = (f"{parameter.print_field_width}."
                                                     f"{parameter.print_decimal_places}")
        # self.data.populate_object(parameter_list, parameter_formats, data_lines)
        return self

    def update_odf(self) -> None:
        if self.record_header.num_calibration != len(self.general_cal_headers):
            self.record_header.num_calibration = len(self.general_cal_headers)
        if self.record_header.num_calibration != len(self.polynomial_cal_headers):
            self.record_header.num_calibration = len(self.polynomial_cal_headers)
        if self.record_header.num_history != len(self.history_headers):
            self.record_header.num_history = len(self.history_headers)
        if self.record_header.num_swing != len(self.compass_cal_headers):
            self.record_header.num_swing = len(self.compass_cal_headers)
        if self.record_header.num_param != len(self.parameter_headers):
            self.record_header.num_param = len(self.parameter_headers)
        # if self.record_header.num_cycle != len(self.data):
        #     self.record_header.num_cycle = len(self.data)

    def write_odf(self, odf_file_path: str, version: float = 2.0) -> None:
        assert isinstance(odf_file_path, str), "Input argument 'odf_file_path' must be a string."
        assert isinstance(version, float), "Input argument 'version' must be a float."

        """ Write the ODF file to disk. """
        odf_file_text = self.print_object(file_version = version)
        file1 = open(odf_file_path, "w")
        file1.write(odf_file_text)
        file1.close()
        print(f"ODF file written to {odf_file_path}\n")

    @staticmethod
    def generate_creation_date() -> str:
        dt = datetime.now().strftime("%d-%b-%Y %H:%M:%S.%f").upper()
        creation_date = dt[:-4]
        return creation_date

    # def add_history(self) -> None:
    #     nhh = HistoryHeader()
    #     nhh.creation_date = self.generate_creation_date()
    #     self.history_headers.append(nhh)

    # def add_to_history(self, history_comment) -> None:
    #     if history_comment is not None:
    #         if len(self.history_headers) > 0:
    #             self.history_headers[-1].add_process(history_comment)
    #         else:
    #             self.history_headers.append(history_comment)

    # def add_log_to_history(self) -> None:
    #     # Access the log records stored in the custom handler
    #     for log_entry in self.shared_log_list:
    #         self.add_to_history(log_entry)

    # def add_to_log(self, message: str) -> None:
    #     assert isinstance(message, str), "Input argumnet 'message' must be a string."
    #     # Access the log records stored in the custom handler
    #     self.shared_log_list.append(message)

    # def update_parameter(self, parameter_code: str, attribute: str, value) -> None:
    #     assert isinstance(parameter_code, str), "Input argumnet 'parameter_code' must be a string."
    #     assert isinstance(attribute, str), "Input argumnet 'attribute' must be a string."
    #     # codes = self.data.parameter_list
    #     if isinstance(value, str):
    #         eval(f"self.parameter_headers[codes.index(parameter_code)].set_{attribute}('{value}')")
    #     else:
    #         eval(f"self.parameter_headers[codes.index(parameter_code)].set_{attribute}({value})")

    # def get_parameter_codes(self) -> list:
    #     parameter_codes = list()
    #     for ph1 in self.parameter_headers:
    #         parameter_codes.append(ph1.code)
    #     return parameter_codes

    # def get_parameter_names(self) -> list:
    #     parameter_names = list()
    #     for ph2 in self.parameter_headers:
    #         parameter_names.append(ph2.name)
    #     return parameter_names

    # def generate_file_spec(self) -> str:
    #     dt = self.event_header.data_type.strip("'")
    #     cn = self.cruise_header.cruise_number.strip("'")
    #     en = self.event_header.event_number.strip("'")
    #     eq1 = self.event_header.event_qualifier1.strip("'")
    #     eq2 = self.event_header.event_qualifier2.strip("'")
    #     file_spec = f"{dt}_{cn}_{en}_{eq1}_{eq2}"
    #     file_spec = file_spec
    #     return file_spec

    # def fix_parameter_codes(self, new_codes: list = []) -> Self:
    #     assert isinstance(new_codes, list), "Input argument 'new_codes' must be a list."

    #     # Get the list of parameter names and the data frame in case names need to be fixed.
    #     df = self.data.data_frame
    #     if not new_codes:

    #         # Check if the parameter codes are in the correct format. If they are not then fix them.
    #         codes = self.data.parameter_list

    #         # Loop through the list of parameter codes and fix any that require it.
    #         for p, pcode in enumerate(codes):
    #             expected_format = '[A-Z]{4}[_]{1}[0-9]{2}'
    #             expected_match = re.compile(expected_format)
    #             if expected_match.findall(pcode) == []:
    #                 new_pcode = input(f"Please enter the correct code name (e.g. TEMP_01) for {pcode} : ")
    #                 new_codes.append(new_pcode)
    #                 df.rename(columns={pcode: new_pcode})
    #                 self.parameter_headers[p].code = new_pcode

    #         # Fix the Polynomial_Cal_Headers if required.
    #         if self.polynomial_cal_headers:
    #             self.fix_polynomial_codes(codes, new_codes)

    #         # Assign the revised data frame back to the odf object.
    #         self.data.data_frame = df
        
    #     else:

    #         old_codes = df.columns.to_list()
    #         df.columns = new_codes
    #         self.data.data_frame = df
    #         self.data.parameter_list = new_codes
    #         nparams = len(self.get_parameter_codes())
    #         for j in range(nparams):
    #             self.parameter_headers[j].code = new_codes[j]

    #         # Fix the Polynomial_Cal_Headers if required.
    #         if self.polynomial_cal_headers:
    #             self.fix_polynomial_codes(old_codes, new_codes)
        
    #     return self
    
    # def fix_polynomial_codes(self, old_codes: list, new_codes: list) -> Self:
    #     assert isinstance(old_codes, list), "Input argument 'old_codes' must be a list."
    #     assert isinstance(new_codes, list), "Input argument 'new_codes' must be a list."

    #     for i, pch in enumerate(self.polynomial_cal_headers):

    #         # Find the Polynomial_Cal_Header Code in old_codes and replace it with the corresponding code from new_codes.
    #         poly_code = pch.parameter_code
    #         try:
    #             # This poly_code may have actually been a parameter_name instead of a parameter_code.
    #             # Check the parameter names and if there is a match then assign the parameter code as the polynomial code.
    #             pnames = self.get_parameter_names()
    #             pnames = [x.replace('"', '') for x in pnames]
    #             if poly_code in pnames:
    #                 self.polynomial_cal_headers[i].parameter_code = new_codes[i]
    #         except Exception as e:
    #             print(e)
    #             print(f"Item {poly_code} not found in old_codes list.")
    #     return self

    # def is_parameter_code(self, code: str) -> bool:
    #     assert isinstance(code, str), "Input argument 'code' must be a string."
    #     codes = self.get_parameter_codes()
    #     return code in codes

    # @staticmethod
    # def null2empty(df: pd.DataFrame) -> pd.DataFrame:
    #     assert isinstance(df, pd.DataFrame), "Input argument 'df' must be a Pandas DataFrame."
    #     new_df = df.replace(BaseHeader.NULL_VALUE, None, inplace=False)
    #     return new_df
                

def main():

    BaseHeader.reset_logging
    odf = OdfHeader()
    odf.cruise_header.config = odf.config
    odf.cruise_header.logger = odf.logger
    odf.event_header.config = odf.config
    odf.event_header.logger = odf.logger

    my_path = 'C:\\DFO-MPO\\DEV\\GitHub\\datashop_toolbox\\'
    
    # Test file(s) to read in.
    # my_file = 'CTD_2000037_102_1_DN.ODF'
    # my_file = 'CTD_91001_1_1_DN.ODF'
    # my_file = 'CTD_BCD2024669_001_01_DN.ODF'
    # my_file = 'CTD_SCD2022277_002_01_DN.ODF'
    # my_file = 'file_with_leading_spaces.ODF'
    # my_file = 'file_with_null_data_values.ODF'
    my_file = 'D146a013.ODF'
    
    # odf.read_odf(my_path + "tests\\ODF\\" + my_file)

    # Add a new History Header to record the modifications that are made.
    # odf.add_history()
    user = 'Jeff Jackson'
    odf.log_odf_message(f'{user} made the following modifications to this file:', 'base')

    # Modify some of the odf metadata
    org = odf.cruise_header.organization
    odf.cruise_header.log_cruise_message("CHIEF_SCIENTIST", org, 'DFO BIO')
    odf.cruise_header.organization = 'DFO BIO'
    cs = odf.cruise_header.chief_scientist
    odf.cruise_header.log_cruise_message("CHIEF_SCIENTIST", cs, 'GLEN HARRISON')
    odf.cruise_header.chief_scientist = 'GLEN HARRISON'
    csdt = odf.cruise_header.start_date
    odf.cruise_header.start_date = '01-APR-2022 00:00:00.00'
    odf.cruise_header.log_cruise_message("START_DATE", csdt, '01-APR-2022 00:00:00.00')
    cedt = odf.cruise_header.end_date
    odf.cruise_header.end_date = '31-OCT-2022 00:00:00.00'
    odf.cruise_header.log_cruise_message("END_DATE", cedt, '31-OCT-2022 00:00:00.00')
    platform = odf.cruise_header.platform
    odf.cruise_header.platform = "LATALANTE"
    odf.cruise_header.log_cruise_message("PLATFORM", platform, "LATALANTE")
    
    station_name = odf.event_header.station_name
    odf.event_header.station_name = 'AR7W_15'
    odf.event_header.log_event_message("STATION_NAME", station_name, "AR7W_15")

    desc = odf.instrument_header.description
    odf.instrument_header.log_instrument_message("DESCRIPTION", desc, "RBR Concerto CTD")
    odf.instrument_header.description = "RBR Concerto CTD"

    odf.meteo_header = MeteoHeader()
    odf.meteo_header.set_logger_and_config(odf.logger, odf.config)
    odf.meteo_header.air_temperature = 10.0
    ap = odf.meteo_header.atmospheric_pressure
    odf.meteo_header.log_meteo_message("ATMOSPHERIC_PRESSURE", ap, 1063.1)
    odf.meteo_header.atmospheric_pressure = 1063.1
    odf.meteo_header.wind_speed = MeteoHeader.wind_speed_knots_to_ms(50.0)
    odf.meteo_header.wind_direction = 180.0
    odf.meteo_header.sea_state = MeteoHeader.wave_height_meters_to_wmo_code(3.0)
    odf.meteo_header.cloud_cover = MeteoHeader.cloud_cover_percentage_to_wmo_code(0.5)
    odf.meteo_header.ice_thickness = 0.5
    odf.meteo_header.set_meteo_comment('This is a test comment')
    odf.meteo_header.set_meteo_comment('This is another test comment')

    odf.quality_header = QualityHeader()
    odf.quality_header.set_logger_and_config(odf.logger, odf.config)
    qd = odf.quality_header.quality_date
    odf.quality_header.log_quality_message("QUALITY_DATE", qd, '01-JUL-2017 10:45:19.00')
    odf.quality_header.quality_date = '01-JUL-2017 10:45:19.00'
    odf.quality_header.set_quality_test('Test 1')
    odf.quality_header.set_quality_test('Test 2')
    odf.quality_header.quality_comments = ['Comment 1', 'Comment 2']

    compass_cal_header = CompassCalHeader()
    compass_cal_fields = [
        "PARAMETER_NAME = PARAMETER_CODE",
        "PARAMETER_CODE = SOG_01",
        "CALIBRATION_DATE = 25-mar-2021 00:00:00.00",
        "APPLICATION_DATE = 31-jan-2022 00:00:00.00",
        "DIRECTIONS = 0.0 90.0 180.0 270.0",
        "CORRECTIONS = 70.0 0.0 0.0 0.0"
    ]
    compass_cal_header.populate_object(compass_cal_fields)
    odf.compass_cal_headers.append(compass_cal_header)

    general_cal_header = GeneralCalHeader()
    general_cal_header.config = BaseHeader._default_config
    general_cal_header.logger = BaseHeader._default_logger
    general_cal_header.parameter_code = 'PSAR_01'
    general_cal_header.calibration_type = 'Linear'
    general_cal_header.calibration_date = '28-May-2020 00:00:00.00'
    general_cal_header.application_date = '14-Oct-2020 23:59:59.99'
    general_cal_header.number_coefficients = 2
    general_cal_header.coefficients = [0.75, 1.05834]
    general_cal_header.calibration_equation = 'y = mx + b'
    general_cal_header.set_calibration_comment('This is a comment')
    general_cal_header.log_general_message('calibration_equation', general_cal_header.calibration_equation, 'Y = X^2 + MX + B')
    general_cal_header.set_coefficient(3.5, 1)
    odf.general_cal_headers.append(general_cal_header)

    poly1 = PolynomialCalHeader()
    poly1.config = BaseHeader._default_config
    poly1.logger = BaseHeader._default_logger
    poly1.parameter_code = 'PRES_01'
    poly1.calibration_date = '11-JUN-1995 05:35:46.82'
    poly1.application_date = '11-JUN-1995 05:35:46.82'
    poly1.number_coefficients = 2
    poly1.coefficients = [0.60000000e+01, 0.15000001e+00]

    poly2 = PolynomialCalHeader()
    poly2.config = BaseHeader._default_config
    poly2.logger = BaseHeader._default_logger
    poly2.parameter_code = 'TEMP_01'
    poly2.calibration_date = '11-JUN-1995 05:35:46.83'
    poly2.application_date = '11-JUN-1995 05:35:46.83'
    poly2.number_coefficients = 4
    poly2.coefficients = [0.0, 80.0, 0.60000000e+01, 0.15000001e+00]
    poly2.log_poly_message('coefficient 2', poly2.coefficients[1], 9.750)
    poly2.set_coefficient(9.750, 2)

    odf.polynomial_cal_headers.append(poly1)
    odf.polynomial_cal_headers.append(poly2)

    history_header = HistoryHeader()
    history_header.set_logger_and_config(odf.logger, odf.config)
    history_fields = ["CREATION_DATE = '01-JUN-2021 05:30:12.00'",
                    "PROCESS = First process",
                    "PROCESS = Second process",
                    "PROCESS = Blank process",
                    "PROCESS = Fourth process",
                    "PROCESS = Last process"]
    history_header.populate_object(history_fields)
    history_header.log_history_message('process', history_header.processes[1], 'Bad Cast')
    history_header.set_process('Bad Cast', 2)
    odf.history_headers.append(history_header)

    param1 = ParameterHeader(
        type='DOUB',
        name='Pressure',
        units='decibars',
        code='PRES_01',
        wmo_code='PRES',
        null_string=f'{BaseHeader.NULL_VALUE}',
        print_field_width=10,
        print_decimal_places=3,
        angle_of_section=0.0,
        magnetic_variation=0.0,
        depth=float(check_string('0.00000000D+00')),
        # depth=0.50000000e+02,
        minimum_value=2.177,
        maximum_value=176.5,
        number_valid=1064,
        number_null=643
    )

    odf.parameter_headers.append(param1)

    record_fields = [
        "NUM_CALIBRATION = 0",
        "NUM_HISTORY = 0",
        "NUM_SWING = 0",
        "NUM_PARAM = 1",
        "NUM_CYCLE = 0"
    ]
    odf.record_header.populate_object(record_fields)

    # Prior to loading data into an Oracle database, the null values need to be replaced with None values.
    # new_df = odf.null2empty(odf.data.data_frame)
    # odf.data.data_frame = new_df

    # Remove the CRAT_01 parameter.
    # from datashop_toolbox.remove_parameter import remove_parameter
    # odf = remove_parameter(odf, 'CRAT_01')
    # odf = remove_parameter(odf, 'UNKN_01')

    # for meteo_comment in odf.meteo_header.get_meteo_comments():
    #     ic(meteo_comment)

    # Retrieve the data from the input ODF structure.
    # data = odf.data.data_frame

    # Get the number of data rows and columns.
    # nrows, ncols = data.shape

    # Retrieve the Parameter Headers from the input ODF structure.
    # parameter_headers = odf.parameter_headers
    # parameter_codes = odf.get_parameter_codes()

    # sytm_index = [i for i,pcode in enumerate(parameter_codes) if pcode[0:4] == 'SYTM']
    # if sytm_index != []:
    #     sytm_index = sytm_index[0]

    # for j, parameter_header in enumerate(parameter_headers):

    #     parameter_code = parameter_header.code.strip("'")
    #     try:
    #         _, sensor_number = parameter_code.split("_")
    #     except ValueError:
    #         sensor_number = 1
    #         continue
    #     sensor_number = float(sensor_number)          

    #     if data.loc[:, parameter_code].isnull().all():

    #         # Suggest removing parameter columns that only contain null values.
    #         print(f'Should the data for {parameter_code} be deleted from '
    #                 'the ODF structure since it only contains NULL values?')

    # odf.update_odf()

    # Write the ODF file to disk.
    # spec = odf.generate_file_spec()
    # out_file = f"{spec}.ODF"
    # odf.write_odf(my_path + 'tests_output\\' + out_file, version = 2.0)

    odf.update_odf()

    print(odf.print_object())

    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)


if __name__ == '__main__':
    main()
