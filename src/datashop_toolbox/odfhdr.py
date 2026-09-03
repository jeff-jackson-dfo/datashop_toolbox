from datetime import datetime
from pathlib import Path
from typing import TypedDict

import numpy as np
import pandas as pd
from pydantic import ConfigDict, Field, field_validator
from termcolor import colored

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
from datashop_toolbox.records import DataRecords
from datashop_toolbox.validated_base import (
    ValidatedBase,
    add_commas,
    check_string,
    clean_strings,
    find_lines_with_text,
    read_file_lines,
    split_lines_into_dict,
)


class HeaderFieldRangeSchema(TypedDict):
    Start: int
    End: int


class OdfHeader(ValidatedBase, BaseHeader):
    """Store metadata, headers, and data associated with an ODF file.

    The class aggregates the standard ODF header sections and the data
    records associated with the file. It also provides methods for reading,
    writing, updating, and inspecting ODF files.

    Attributes:
        file_specification: ODF file specification identifier.
        odf_specification_version: ODF specification version.
        cruise_header: Cruise metadata.
        event_header: Event metadata.
        meteo_header: Optional meteorological metadata.
        instrument_header: Instrument metadata.
        quality_header: Optional quality-control metadata.
        general_cal_headers: General calibration headers.
        compass_cal_headers: Compass calibration headers.
        polynomial_cal_headers: Polynomial calibration headers.
        history_headers: Processing history headers.
        parameter_headers: Parameter definitions associated with the data.
        record_header: Record-level metadata and counts.
        data: Data records contained in the ODF file.
    """

    model_config = ConfigDict(validate_assignment=True)

    file_specification: str = ""
    odf_specification_version: float = BaseHeader.NULL_VALUE

    cruise_header: CruiseHeader = Field(default_factory=CruiseHeader)
    event_header: EventHeader = Field(default_factory=EventHeader)
    meteo_header: MeteoHeader | None = None
    instrument_header: InstrumentHeader = Field(default_factory=InstrumentHeader)
    quality_header: QualityHeader | None = None

    general_cal_headers: list[GeneralCalHeader] = Field(default_factory=list)
    compass_cal_headers: list[CompassCalHeader] = Field(default_factory=list)
    polynomial_cal_headers: list[PolynomialCalHeader] = Field(default_factory=list)
    history_headers: list[HistoryHeader] = Field(default_factory=list)
    parameter_headers: list[ParameterHeader] = Field(default_factory=list)

    record_header: RecordHeader = Field(default_factory=RecordHeader)
    data: DataRecords = Field(default_factory=DataRecords)

    def __init__(self, config=None, **data):
        """Initialize the ODF header and its child header objects.

        Args:
            config: Optional configuration passed to :class:`BaseHeader`.
            **data: Field values used to initialize the Pydantic model.
        """
        super().__init__(**data)  # Calls Pydantic's __init__
        BaseHeader.__init__(self, config)  # Ensures logger and config are set
        self.cruise_header.set_logger_and_config(self.logger, self.config)
        self.event_header.set_logger_and_config(self.logger, self.config)
        self.instrument_header.set_logger_and_config(self.logger, self.config)
        if self.quality_header is not None:
            self.quality_header.set_logger_and_config(self.logger, self.config)
        if self.meteo_header is not None:
            self.meteo_header.set_logger_and_config(self.logger, self.config)
        self.record_header.set_logger_and_config(self.logger, self.config)

    def log_odf_message(self, message: str, type: str = "self"):
        """Log a message for the ODF header.

        Args:
            message: Message to log.
            type: Logging destination. ``"self"`` adds the message to the
                ODF header log; ``"base"`` delegates to the base-header log.

        Raises:
            AssertionError: If ``message`` or ``type`` is not a string.
        """
        assert isinstance(message, str), "Input argument 'message' must be a string."
        assert isinstance(type, str), "Input argument 'type' must be a string."
        if type == "self":
            self.logger.info(f"In ODF Header field {message}")
            self.shared_log_list.append(f"In ODF Header field {message}")
        elif type == "base":
            self.log_message(message)

    # -------------------
    # Validators
    # -------------------
    @field_validator("file_specification")
    @classmethod
    def validate_file_specification(cls, v: str) -> str:
        """Validate that the file specification is not empty.

        Args:
            v: File specification to validate.

        Returns:
            The validated file specification.

        Raises:
            ValueError: If the value is empty or contains only whitespace.
        """
        if not v.strip():
            raise ValueError("file_specification cannot be empty.")
        return v

    # @field_validator("general_cal_headers", "compass_cal_headers",
    #                  "polynomial_cal_headers", "history_headers", "parameter_headers")
    @field_validator("compass_cal_headers", "history_headers", "parameter_headers")
    @classmethod
    def ensure_list_items_are_models(cls, v, field):
        """Validate that list items provide an ODF serialization method.

        Args:
            v: Header objects to validate.
            field: Pydantic field being validated.

        Returns:
            The validated list.

        Raises:
            TypeError: If an item does not provide a ``print_object`` method.
        """
        if not all(hasattr(item, "print_object") for item in v):
            raise TypeError(
                f"All elements in {field.name} must be valid header objects "
                f"with a 'print_object' method."
            )
        return v

    @field_validator("quality_header", "meteo_header")
    @classmethod
    def check_optional_headers(cls, v, field):
        """Validate an optional header object.

        Args:
            v: Header object or ``None``.
            field: Pydantic field being validated.

        Returns:
            The validated header or ``None``.

        Raises:
            TypeError: If ``v`` is neither ``None`` nor an object providing a
                ``print_object`` method.
        """
        if v is not None and not hasattr(v, "print_object"):
            raise TypeError(f"{field.name} must be None or a valid header object.")
        return v

    def populate_object(self, odf_dict: dict):
        """Populate ODF-level fields from a dictionary.

        Args:
            odf_dict: Dictionary containing ODF header fields such as
                ``FILE_SPECIFICATION`` and ``ODF_SPECIFICATION_VERSION``.

        Returns:
            This :class:`OdfHeader` instance.

        Raises:
            AssertionError: If ``odf_dict`` is not a dictionary.
        """
        assert isinstance(odf_dict, dict), "Input argument 'value' must be a dict."
        for key, value in odf_dict.items():
            match key.strip():
                case "FILE_SPECIFICATION":
                    self._file_specification = value.strip()
                case "ODF_SPECIFICATION_VERSION":
                    self._odf_specification_version = value.strip()
        return self

    def print_object(self, file_version: float = 2.0) -> str:
        """Serialize the ODF header and data to ODF-formatted text.

        Args:
            file_version: ODF output format version. Version ``2.0`` uses the
                comma-delimited format; versions ``3.0`` and later use the
                non-comma-delimited format.

        Returns:
            The complete ODF header followed by the data records.

        Raises:
            AssertionError: If ``file_version`` is not a float.
        """
        assert isinstance(file_version, float), "Input argument 'file_version' must be a float."

        # Add modifications to the OdfHeader instance before outputting it
        self.add_log_to_history()

        odf_output = ""

        # List of optional headers
        optional_headers = [
            ("meteo_header", self.meteo_header),
            ("quality_header", self.quality_header),
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
            odf_output += add_commas(self.instrument_header.print_object())

            for _name, header in optional_headers:
                if header is not None:
                    odf_output += add_header_output(header)

            for cal in (
                self.general_cal_headers + self.polynomial_cal_headers + self.compass_cal_headers
            ):
                odf_output += add_commas(cal.print_object())

            for hist in self.history_headers:
                odf_output += add_commas(hist.print_object())

            for param in self.parameter_headers:
                odf_output += add_commas(param.print_object())

            odf_output += add_commas(self.record_header.print_object())
            odf_output += "-- DATA --\n"
            odf_output += self.data.print_object_old_style()

        elif file_version >= 3:
            self.odf_specification_version = 3.0
            odf_output = "ODF_HEADER\n"
            odf_output += f"  FILE_SPECIFICATION = {self.file_specification}\n"
            odf_output += f"  ODF_SPECIFICATION_VERSION = {self.odf_specification_version}\n"
            odf_output += self.cruise_header.print_object() + "\n"
            odf_output += self.event_header.print_object() + "\n"

            for _name, header in optional_headers:
                if header is not None:
                    odf_output += add_header_output(header, use_commas=False)

            odf_output += self.instrument_header.print_object() + "\n"

            for cal in (
                self.general_cal_headers + self.polynomial_cal_headers + self.compass_cal_headers
            ):
                odf_output += cal.print_object() + "\n"

            for hist in self.history_headers:
                odf_output += hist.print_object() + "\n"

            for param in self.parameter_headers:
                odf_output += param.print_object() + "\n"

            odf_output += self.record_header.print_object() + "\n"
            odf_output += "-- DATA --" + "\n"
            odf_output += self.data.print_object()

        return odf_output

    @staticmethod
    def repair_text(text: str) -> str:
        result = text

        for _ in range(5):
            if not any(x in result for x in ("Ã", "Â", "Æ", "â")):
                break

            try:
                repaired = result.encode("cp1252").decode("utf-8")

                if repaired == result:
                    break

                result = repaired

            except (UnicodeEncodeError, UnicodeDecodeError):
                break

        return result

    def read_odf(self, odf_file_path: Path):
        """Read an ODF file and populate this object.

        The method parses the ODF header blocks, populates their corresponding
        header objects, and uses the parameter definitions to parse the data
        records.

        Args:
            odf_file_path: Path to the ODF file to read.

        Returns:
            This :class:`OdfHeader` instance.

        Raises:
            AssertionError: If ``odf_file_path`` is not a string.
        """
        assert isinstance(odf_file_path, Path), "Input argument 'odf_file_path' must be a string."
        all_lines = read_file_lines(odf_file_path)
        file_lines = [self.repair_text(line) for line in all_lines]
        substrings_to_find = ["_HEADER"]
        header_lines_with_indices = []
        if isinstance(file_lines, list):
            header_lines_with_indices = find_lines_with_text(file_lines, substrings_to_find)
        header_starts_list = list()
        header_indices = list()
        header_names = list()
        for index, line in header_lines_with_indices:
            header_indices.append(index)
            header_names.append(line.strip(" ,"))
            header_starts_list.append([index, line.strip(" ,")])
        header_blocks_df = pd.DataFrame(header_starts_list, columns=["index", "name"])
        header_blocks_df["index"] = header_blocks_df["index"].astype(int)

        data_line = "-- DATA --"
        substrings_to_find = [data_line]
        data_lines_with_indices = []
        if isinstance(file_lines, list):
            data_lines_with_indices = find_lines_with_text(file_lines, substrings_to_find)
        else:
            print(file_lines)  # or handle the error string appropriately

        if isinstance(file_lines, list):
            data_lines_with_indices = find_lines_with_text(file_lines, substrings_to_find)
        # data_lines = List[str]
        data_line_start = -1
        for index, _line in data_lines_with_indices:
            data_line_start = index + 1

        # Separate the header and data lines
        header_lines = file_lines[: data_line_start - 1]
        data_lines = file_lines[data_line_start:]

        # Get the line range for the list of fields in each header block
        if isinstance(header_lines, list):
            header_lines = clean_strings(header_lines)

        # Prepare the header_field_range DataFrame
        header_field_range = pd.DataFrame(columns=["Name", "Start", "End"])

        ndf = len(header_blocks_df)

        header_field_range = pd.DataFrame(
            {
                "Name": header_blocks_df["name"],
                "Start": header_blocks_df["index"] + 1,
                "End": header_blocks_df["index"].shift(-1, fill_value=data_line_start) - 1,
            }
        )

        # Loop through the header lines, populating the OdfHeader object as it goes.
        for i in range(ndf):
            header_block = str(header_blocks_df.at[i, "name"])
            x = int(header_field_range.at[i, "Start"]) # pyright: ignore[reportArgumentType]
            y = int(header_field_range.at[i, "End"]) # pyright: ignore[reportArgumentType]
            block_lines = header_lines[x:y + 1]
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
                    history_header.print_object()
                    self.history_headers.append(history_header)
                case "INSTRUMENT_HEADER":
                    self.instrument_header = self.instrument_header.populate_object(block_lines)
                case "METEO_HEADER":
                    self.meteo_header = MeteoHeader()
                    self.meteo_header.populate_object(block_lines)
                case "ODF_HEADER":
                    for header_line in block_lines:
                        tokens = header_line.split("=", maxsplit=1)
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
            if parameter_code[0:4] == "SYTM":
                parameter_formats[parameter_code] = f"{parameter.print_field_width}"
            else:
                parameter_formats[parameter_code] = (
                    f"{parameter.print_field_width}.{parameter.print_decimal_places}"
                )
        if isinstance(data_lines, list):
            self.data.populate_object(parameter_list, parameter_formats, data_lines)
        return self


    def update_odf(self) -> None:
        """Update derived ODF metadata from the current contents.

        Record-header counts, event depth information, depth off bottom, and
        parameter minimum and maximum values are updated from the current
        calibration headers, history, parameters, and data.
        """

        # Update the record header counts if required.
        number_of_calibrations = len(self.polynomial_cal_headers) + len(self.general_cal_headers)
        if self.record_header.num_calibration != number_of_calibrations:
            self.record_header.num_calibration = number_of_calibrations
        if self.record_header.num_history != len(self.history_headers):
            self.record_header.num_history = len(self.history_headers)
        if self.record_header.num_swing != len(self.compass_cal_headers):
            self.record_header.num_swing = len(self.compass_cal_headers)
        if self.record_header.num_param != len(self.parameter_headers):
            self.record_header.num_param = len(self.parameter_headers)
        if self.record_header.num_cycle != len(self.data):
            self.record_header.num_cycle = len(self.data)

        # Update event header information if required.
        if self.event_header.min_depth is BaseHeader.NULL_VALUE and "DEPH_01" in self.data.parameter_list:
            self.event_header.min_depth = self.data.data_frame["DEPH_01"].min()
            self.event_header.max_depth = self.data.data_frame["DEPH_01"].max()
        elif self.event_header.min_depth is BaseHeader.NULL_VALUE and "PRES_01" in self.data.parameter_list:
            self.event_header.min_depth = self.data.data_frame["PRES_01"].min()
            self.event_header.max_depth = self.data.data_frame["PRES_01"].max()
        if self.event_header.depth_off_bottom is BaseHeader.NULL_VALUE:
            if self.event_header.sounding is not BaseHeader.NULL_VALUE:
                self.event_header.depth_off_bottom = self.event_header.sounding - self.event_header.max_depth

        # Update the parameter headers if required.
        for ph in self.parameter_headers:
            param_data = self.data.data_frame[ph.code]
            if ph.type == "SYTM":
                ph.minimum_value = param_data.iloc[0]
                ph.maximum_value = param_data.iloc[-1]
            else:
                ph.minimum_value = min(param_data)
                ph.maximum_value = max(param_data)


    def write_odf(self, odf_file_path: Path, version: float = 2.0) -> None:
        """Write the ODF object to a file.

        Args:
            odf_file_path: Path where the ODF file will be written.
            version: ODF output format version passed to :meth:`print_object`.

        Raises:
            AssertionError: If ``odf_file_path`` is not a string or ``version``
                is not a float.
        """
        assert isinstance(odf_file_path, Path), "Input argument 'odf_file_path' must be a string."
        assert isinstance(version, float), "Input argument 'version' must be a float."

        odf_file_text = self.print_object(file_version=version)
        with open(odf_file_path, "w", encoding="iso-8859-1") as file1:
            file1.write(odf_file_text)
        msg1 = colored("ODF file written to: ", "yellow")
        msg2 = colored(f"{odf_file_path}", "cyan")
        msg = msg1 + msg2
        print(msg)

    @staticmethod
    def generate_creation_date() -> str:
        """Generate the current timestamp in ODF history-header format.

        Returns:
            A timestamp formatted as ``DD-MON-YYYY HH:MM:SS.xx``.
        """
        dt = datetime.now().strftime("%d-%b-%Y %H:%M:%S.%f").upper()
        creation_date = dt[:-4]
        return creation_date

    def add_history(self) -> None:
        """Append a new processing history header.

        The new history header is initialized with the current creation date.
        """
        nhh = HistoryHeader()
        nhh.creation_date = self.generate_creation_date()
        self.history_headers.append(nhh)

    def add_to_history(self, history_comment) -> None:
        """Add a processing comment to the most recent history entry.

        Args:
            history_comment: Comment or history entry to add. ``None`` is
                ignored.
        """
        if history_comment is not None:
            if len(self.history_headers) > 0:
                self.history_headers[-1].add_process(history_comment)
            else:
                self.history_headers.append(history_comment)

    def add_log_to_history(self) -> None:
        """Add pending shared log messages to processing history.

        After the messages are added, the shared log list is cleared.
        """
        # Access the log records stored in the custom handler
        for log_entry in self.shared_log_list:
            self.add_to_history(log_entry)
        self.shared_log_list.clear()

    def add_to_log(self, message: str) -> None:
        """Append a message to the shared ODF log.

        Args:
            message: Message to append to the shared log.

        Raises:
            AssertionError: If ``message`` is not a string.
        """
        assert isinstance(message, str), "Input argumnet 'message' must be a string."
        # Access the log records stored in the custom handler
        self.shared_log_list.append(message)

    # def update_parameter(self, parameter_code: str, attribute: str, value) -> None:
    #     assert isinstance(parameter_code, str), "Input argumnet 'parameter_code' must be a string."
    #     assert isinstance(attribute, str), "Input argumnet 'attribute' must be a string."
    #     # codes = self.data.parameter_list
    #     if isinstance(value, str):
    #         eval(f"self.parameter_headers[codes.index(parameter_code)].set_{attribute}('{value}')")
    #     else:
    #         eval(f"self.parameter_headers[codes.index(parameter_code)].set_{attribute}({value})")

    def get_parameter_codes(self) -> list:
        """Return the codes of all parameter headers.

        Returns:
            Parameter codes in parameter-header order.
        """
        parameter_codes = list()
        for ph1 in self.parameter_headers:
            parameter_codes.append(ph1.code)
        return parameter_codes

    def get_parameter_names(self) -> list:
        """Return the names of all parameter headers.

        Returns:
            Parameter names in parameter-header order.
        """
        parameter_names = list()
        for ph2 in self.parameter_headers:
            parameter_names.append(ph2.name)
        return parameter_names

    def generate_file_spec(self) -> str:
        """Generate a file specification from cruise and event metadata.

        Returns:
            A file specification composed of data type, cruise number, event
            number, and the two event qualifiers.
        """
        dt = self.event_header.data_type.strip("'")
        cn = self.cruise_header.cruise_number.strip("'")
        en = self.event_header.event_number.strip("'")
        eq1 = self.event_header.event_qualifier1.strip("'")
        eq2 = self.event_header.event_qualifier2.strip("'")
        file_spec = f"{dt}_{cn}_{en}_{eq1}_{eq2}"
        return file_spec

    def generate_set_file_spec(self) -> str:
        """Generate a file specification for an event set.

        Returns:
            A set file specification composed of data type, cruise number,
            set number, and the two event qualifiers.
        """
        dt = self.event_header.data_type.strip("'")
        cn = self.cruise_header.cruise_number.strip("'")
        sn = self.event_header.set_number.strip("'")
        eq1 = self.event_header.event_qualifier1.strip("'")
        eq2 = self.event_header.event_qualifier2.strip("'")
        set_file_spec = f"{dt}_{cn}_{sn}_{eq1}_{eq2}"
        return set_file_spec

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

    #         # Find the Polynomial_Cal_Header Code in old_codes and replace it with the corresponding code from new_codes.  # noqa: E501
    #         poly_code = pch.parameter_code
    #         try:
    #             # This poly_code may have actually been a parameter_name instead of a parameter_code.
    #             # Check the parameter names and if there is a match then assign the parameter code as the polynomial code.  # noqa: E501
    #             pnames = self.get_parameter_names()
    #             pnames = [x.replace('"', '') for x in pnames]
    #             if poly_code in pnames:
    #                 self.polynomial_cal_headers[i].parameter_code = new_codes[i]
    #         except Exception as e:
    #             print(e)
    #             print(f"Item {poly_code} not found in old_codes list.")
    #     return self

    def is_parameter_code(self, code: str) -> bool:
        """Check whether a parameter code is present.

        Args:
            code: Parameter code to search for.

        Returns:
            ``True`` if the code exists; otherwise ``False``.

        Raises:
            AssertionError: If ``code`` is not a string.
        """
        assert isinstance(code, str), "Input argument 'code' must be a string."
        codes = self.get_parameter_codes()
        return code in codes

    @staticmethod
    def null2empty(df: pd.DataFrame) -> pd.DataFrame:
        """Replace ODF null values with ``None`` in a DataFrame.

        Args:
            df: DataFrame containing ODF null values.

        Returns:
            A copy of ``df`` with :attr:`BaseHeader.NULL_VALUE` replaced by
            ``None``.

        Raises:
            AssertionError: If ``df`` is not a pandas DataFrame.
        """
        assert isinstance(df, pd.DataFrame), "Input argument 'df' must be a Pandas DataFrame."
        new_df = df.replace(BaseHeader.NULL_VALUE, None, inplace=False)
        return new_df

    def add_quality_flags(self):
        """Add quality-flag parameters and columns to the ODF data.

        Quality flags are added for each parameter except parameters whose
        codes begin with ``SYTM``, ``CNTR``, or ``SNCNTR``. A corresponding
        :class:`QualityHeader` is also created.

        Returns:
            This :class:`OdfHeader` instance.

        Raises:
            ValueError: If the data frame is missing or empty.
        """

        excluded_cols = ["SYTM", "CNTR", "SNCNTR"]
        qf_params = []
        new_df = pd.DataFrame()

        df = self.data.data_frame
        if df is None or df.empty:
            raise ValueError("Data frame is empty. Cannot add quality flags.")

        default_qf_col = np.zeros(len(df), dtype=int)

        # Add quality flags
        for param_header in self.parameter_headers:
            code = param_header.code

            if any(code.startswith(excluded) for excluded in excluded_cols):
                continue

            qf_col = f"Q{code}"

            param = ParameterHeader()
            param.type = "SING"
            param.name = f"Quality Flag for Parameter: {code}"
            param.units = "none"
            param.code = qf_col
            param.null_string = f"{BaseHeader.NULL_VALUE}"
            param.print_field_width = 1
            param.print_decimal_places = 0
            param.minimum_value = 0
            param.maximum_value = 0
            number_null = np.isnan(default_qf_col).sum()
            param.number_valid = len(default_qf_col) - number_null
            param.number_null = number_null

            # Insert the new quality flag parameter header after the current parameter header
            qf_params.append(param)

        new_param_list = []
        new_print_formats = {}

        pcodes = self.get_parameter_codes()
        index_sytm = pcodes.index("SYTM_01")
        if index_sytm != -1:
            new_param_list.append(self.parameter_headers[index_sytm])
            new_df["SYTM_01"] = df["SYTM_01"]
            new_print_formats["SYTM_01"] = f"{self.parameter_headers[index_sytm].print_field_width}"
            # Remove SYTM_01 from further processing
            del self.parameter_headers[index_sytm]

        # Continue to rebuild the parameter header list with quality flags inserted
        for existing_param in self.parameter_headers:
            new_param_list.append(existing_param)
            new_df[existing_param.code] = df[existing_param.code]
            # Look for a matching Quality Flag field (Qparam)
            match = next((q for q in qf_params if q.code[1:] == existing_param.code), None)
            if match:
                new_param_list.append(match)
                new_df[match.code] = default_qf_col
            new_print_formats[existing_param.code] = (
                f"{existing_param.print_field_width}.{existing_param.print_decimal_places}"
            )

        self.parameter_headers = new_param_list
        self.data.data_frame = new_df
        self.data.parameter_list = self.get_parameter_codes()
        self.data.print_formats = new_print_formats

        self.quality_header = QualityHeader()
        self.quality_header.add_quality_codes()

        return self


def main():

    test_creation = False

    if test_creation:

        odf = OdfHeader()
        odf.reset_log_list()
        print(odf.shared_log_list)

        # Add a new History Header to record the modifications that are made.
        # odf.add_history()
        user = "Jeff Jackson"
        odf.log_odf_message(f"{user} made the following modifications to this file:", "base")

        # Modify some of the odf metadata
        odf.cruise_header.set_logger_and_config(odf.logger, odf.config)
        org = odf.cruise_header.organization
        odf.cruise_header.log_cruise_message("CHIEF_SCIENTIST", org, "DFO BIO")
        odf.cruise_header.organization = "DFO BIO"
        cs = odf.cruise_header.chief_scientist
        odf.cruise_header.log_cruise_message("CHIEF_SCIENTIST", cs, "GLEN HARRISON")
        odf.cruise_header.chief_scientist = "GLEN HARRISON"
        csdt = odf.cruise_header.start_date
        odf.cruise_header.start_date = "01-APR-2022 00:00:00.00"
        odf.cruise_header.log_cruise_message("START_DATE", csdt, "01-APR-2022 00:00:00.00")
        cedt = odf.cruise_header.end_date
        odf.cruise_header.end_date = "31-OCT-2022 00:00:00.00"
        odf.cruise_header.log_cruise_message("END_DATE", cedt, "31-OCT-2022 00:00:00.00")
        platform = odf.cruise_header.platform
        odf.cruise_header.platform = "LATALANTE"
        odf.cruise_header.log_cruise_message("PLATFORM", platform, "LATALANTE")

        station_name = odf.event_header.station_name
        odf.event_header.set_logger_and_config(odf.logger, odf.config)
        odf.event_header.station_name = "AR7W_15"
        odf.event_header.log_event_message("STATION_NAME", station_name, "AR7W_15")

        desc = odf.instrument_header.description
        odf.instrument_header.set_logger_and_config(odf.logger, odf.config)
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
        odf.meteo_header.set_meteo_comment("This is a test comment")
        odf.meteo_header.set_meteo_comment("This is another test comment")

        odf.quality_header = QualityHeader()
        odf.quality_header.set_logger_and_config(odf.logger, odf.config)
        qd = odf.quality_header.quality_date
        odf.quality_header.log_quality_message("QUALITY_DATE", qd, "01-JUL-2017 10:45:19.00")
        odf.quality_header.quality_date = "01-JUL-2017 10:45:19.00"
        odf.quality_header.set_quality_test("Test 1")
        odf.quality_header.set_quality_test("Test 2")
        odf.quality_header.quality_comments = ["Comment 1", "Comment 2"]

        compass_cal_header = CompassCalHeader()
        compass_cal_header.set_logger_and_config(odf.logger, odf.config)
        compass_cal_fields = [
            "PARAMETER_NAME = PARAMETER_CODE",
            "PARAMETER_CODE = SOG_01",
            "CALIBRATION_DATE = 25-mar-2021 00:00:00.00",
            "APPLICATION_DATE = 31-jan-2022 00:00:00.00",
            "DIRECTIONS = 0.0 90.0 180.0 270.0",
            "CORRECTIONS = 70.0 0.0 0.0 0.0",
        ]
        compass_cal_header.populate_object(compass_cal_fields)
        odf.compass_cal_headers.append(compass_cal_header)

        general_cal_header = GeneralCalHeader()
        general_cal_header.set_logger_and_config(odf.logger, odf.config)
        general_cal_header.logger = BaseHeader._default_logger
        general_cal_header.parameter_code = "PSAR_01"
        general_cal_header.calibration_type = "Linear"
        general_cal_header.calibration_date = "28-May-2020 00:00:00.00"
        general_cal_header.application_date = "14-Oct-2020 23:59:59.99"
        general_cal_header.number_coefficients = 2
        general_cal_header.coefficients = [0.75, 1.05834]
        general_cal_header.calibration_equation = "y = mx + b"
        general_cal_header.set_calibration_comment("This is a comment")
        general_cal_header.log_general_message(
            "calibration_equation", general_cal_header.calibration_equation, "Y = X^2 + MX + B"
        )
        general_cal_header.set_coefficient(3.5, 1)
        odf.general_cal_headers.append(general_cal_header)

        poly1 = PolynomialCalHeader()
        poly1.set_logger_and_config(odf.logger, odf.config)
        poly1.parameter_code = "PRES_01"
        poly1.calibration_date = "11-JUN-1995 05:35:46.82"
        poly1.application_date = "11-JUN-1995 05:35:46.82"
        poly1.number_coefficients = 2
        poly1.coefficients = [0.60000000e01, 0.15000001e00]
        poly2 = PolynomialCalHeader()
        poly2.set_logger_and_config(odf.logger, odf.config)
        poly2.parameter_code = "TEMP_01"
        poly2.calibration_date = "11-JUN-1995 05:35:46.83"
        poly2.application_date = "11-JUN-1995 05:35:46.83"
        poly2.number_coefficients = 4
        poly2.coefficients = [0.0, 80.0, 0.60000000e01, 0.15000001e00]
        poly2.log_poly_message("coefficient 2", poly2.coefficients[1], 9.750)
        poly2.set_coefficient(9.750, 2)
        odf.polynomial_cal_headers.append(poly1)
        odf.polynomial_cal_headers.append(poly2)

        history_header = HistoryHeader()
        history_header.set_logger_and_config(odf.logger, odf.config)
        history_fields = [
            "CREATION_DATE = '01-JUN-2021 05:30:12.00'",
            "PROCESS = First process",
            "PROCESS = Second process",
            "PROCESS = Blank process",
            "PROCESS = Fourth process",
            "PROCESS = Last process",
        ]
        history_header.populate_object(history_fields)
        history_header.log_history_message("process", history_header.processes[1], "Bad Cast")
        history_header.set_process("Bad Cast", 2)
        odf.history_headers.append(history_header)

        param1 = ParameterHeader(
            type="DOUB",
            name="Pressure",
            units="decibars",
            code="PRES_01",
            wmo_code="PRES",
            null_string=f"{BaseHeader.NULL_VALUE}",
            print_field_width=10,
            print_decimal_places=3,
            angle_of_section=0.0,
            magnetic_variation=0.0,
            depth=float(check_string("0.00000000D+00")),
            # depth=0.50000000e+02,
            minimum_value=2.177,
            maximum_value=176.5,
            number_valid=1064,
            number_null=643,
        )
        param1.set_logger_and_config(odf.logger, odf.config)
        odf.parameter_headers.append(param1)

        records = DataRecords()
        records.set_logger_and_config(odf.logger, odf.config)
        df = pd.DataFrame(
            {
                "PRES_01": [1.0, 4.0, 7.0],
                "TEMP_01": [8.2, 5.6, 2.45],
                "PSAL_01": [31.5, 32.0, 32.88],
            }
        )
        records.data_frame = df
        records.parameter_list = ["PRES_01", "TEMP_01", "PSAL_01"]
        records.print_formats = {"PRES_01": "10.1", "TEMP_01": "10.4", "PSAL_01": "10.4"}
        odf.data = records

        record_fields = [
            "NUM_CALIBRATION = 0",
            "NUM_HISTORY = 0",
            "NUM_SWING = 0",
            "NUM_PARAM = 0",
            "NUM_CYCLE = 0",
        ]
        odf.record_header.populate_object(record_fields)
        odf.record_header.set_logger_and_config(odf.logger, odf.config)

        # Prior to loading data into an Oracle database, the null values need to be replaced with None values.
        new_df = odf.null2empty(odf.data.data_frame)
        odf.data.data_frame = new_df.copy()
        
        print(odf.data.data_frame.head())

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

        odf.update_odf()

        odf.file_specification = odf.generate_file_spec()

        print(odf.print_object())

        print(BaseHeader.shared_log_list)

        for log_entry in odf.shared_log_list:
            print(log_entry)

    # Reading an actual ODF file and performing some manipulations on it.
    else:

        # Test file(s) to read in.
        # my_file = 'CTD_91001_1_1_DN.ODF'
        # my_file = 'CTD_BCD2024669_001_01_DN.ODF'
        # my_file = 'CTD_SCD2022277_002_01_DN.ODF'
        # my_file = 'file_with_leading_spaces.ODF'
        # my_file = 'file_with_null_data_values.ODF'
        # my_file = 'D146a013.ODF'
        # my_file = 'MADCP_HUD2016027_1999_3469-31_3600.ODF'  # Fails because of incorrect date format
        # my_file = 'MCM_HUD2010014_1771_1039_3600.ODF'
        # my_file = 'MCTD_GRP2019001_2104_11689_1800.ODF'  # Fails due to incorrect date value in parameter header
        # my_file = 'CTD_88N112_006_1_DN.ODF'
        # my_file = 'D24010004.ODF'  # Remove all occurences of * in EVENT_QUALIFIER1
        # my_file = 'MTR_BCD2014999_2_352816_300.ODF'
        # my_file = 'MTR_98600_RATB1_1215_1800.ODF'
        # my_file = 'mcm_82917_20555a_20555_1200.odf'
        # my_file = 'mcm_95007_1197_4430830_900.odf'
        # my_file = 'mtr_79999_46_61036_14400.odf'
        # my_file = 'MADCPS_BCD2004909_1544_1269-60_3600.ODF' # Fails due to bad null_value in SYTM parameter header and bad data in SYTM channel.  # noqa: E501
        # my_file = "MCTD_CAR2023648_2264_11689_1800.ODF"
        my_file = "CTD_AT4802_008_1_DN.ODF"
        my_path = "C:/DFO-MPO/DEV/GitHub/datashop_toolbox/"

        odf = OdfHeader()
        odf.reset_log_list()
        # print(odf.shared_log_list)

        input_file_path = Path(my_path, "sampledata/ctd/" + my_file)
        odf.read_odf(input_file_path)

        # Add a new History Header to record the modifications that are made.
        odf.add_history()
        user = "Jeff Jackson"
        odf.log_odf_message(f"{user} made the following modifications to this file:", "base")
        odf.add_to_history("")

        odf.event_header.set_event_comment("We had a successful trip!", 1)

        print(odf.shared_log_list)

        odf.update_odf()

        # Write the ODF file to disk.
        file_spec = odf.generate_file_spec()
        odf.file_specification = file_spec
        out_file = f"{file_spec}.ODF"
        out_file_path = Path("c:/dfo-mpo/test/output/", out_file)
        odf.write_odf(out_file_path, version=2.0)

        if not odf.quality_header:
            odf.quality_header = QualityHeader()
            odf.quality_header.set_logger_and_config(odf.logger, odf.config)
            qd = odf.quality_header.quality_date
            odf.quality_header.log_quality_message("QUALITY_DATE", qd, "01-JUL-2017 10:45:19.00")
            odf.quality_header.quality_date = "01-JUL-2017 10:45:19.00"
            odf.quality_header.set_quality_test("Test 1")
            odf.quality_header.set_quality_test("Test 2")
            odf.quality_header.quality_comments = ["Comment 1", "Comment 2"]
            odf.add_quality_flags()
            odf.quality_header.add_quality_codes()
            odf.quality_header.add_qcff_info()
            qfs_out_file = f"{file_spec}_QFs.ODF"
            qfs_out_file_path = Path("c:/dfo-mpo/test/output/", qfs_out_file)
            odf.write_odf(qfs_out_file_path, version=3.0)


if __name__ == "__main__":
    main()
