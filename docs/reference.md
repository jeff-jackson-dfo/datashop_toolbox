# `datashop_toolbox` / `odf_oracle` — Reference

> **Status:** Draft, generated from the in-code docstrings.
> **Diátaxis quadrant:** [Reference](https://diataxis.fr/reference/) — this document is
> information-oriented and describes the toolbox's public interface as it exists in code.
> It is not a tutorial (see a future `doc/tutorials.md`) and not a how-to guide (see a
> future `doc/how-to.md`); it does not explain *why* the toolbox is built this way (see a
> future `doc/explanation.md`). Its only job is to be an accurate, complete, and
> consistently structured description of the API.

## About this document

This reference is organized around the codebase's own structure — one subsection per
Python module, in the order a reader would encounter them when browsing `src/`. Each
module entry lists:

- a one-line summary (from the module's own docstring, where one exists),
- its public classes, with their constructor and methods, and
- its public module-level functions.

Signatures and descriptions are pulled directly from the current source and docstrings,
so this document should be regenerated whenever the underlying code changes materially —
it is not meant to be hand-maintained prose. Private/internal helpers (names beginning
with a single underscore) are still listed where they materially affect how a class
behaves, since maintainers are a primary audience for this reference; genuinely
implementation-only helpers are omitted only where doing so doesn't lose information a
caller would need. Qt-Designer–generated `ui_*.py` files are excluded, since their
docstrings are regenerated automatically and are not hand-maintained.

## Packages covered

| Package | Location | Purpose |
|---|---|---|
| [`datashop_toolbox`](#datashop_toolbox) | `src/datashop_toolbox/` | ODF header data model, CTD/thermograph processing pipelines, interactive QC tooling, and supporting file-format utilities. |
| [`datashop_toolbox.gui`](#datashop_toolboxgui) | `src/datashop_toolbox/gui/` | PySide6 widgets and dialogs used by the toolbox's interactive tools (ODF metadata entry, RBR→ODF conversion). |
| [`odf_oracle`](#odf_oracle) | `src/odf_oracle/` | Loaders that write a populated `OdfHeader` object into the ODF_ARCHIVE Oracle database, plus the connection-pool and value-conversion helpers they depend on. |

---

## `datashop_toolbox`

### ODF Header Classes

#### `basehdr.py`

**class `LogLevel(enum.StrEnum)`**

Enumeration of the logging levels supported by :class:`LoggerConfig`.

**class `LoggerConfig(BaseModel)`**

Configuration model for logging settings.

| Method | Description |
|---|---|
| `configure_logger() -> logging.Logger` | Configure and return a root logger instance. |

**class `BaseHeader`**

Base class providing shared logging + constants for ODF headers.

| Method | Description |
|---|---|
| `__init__(config: LoggerConfig \| None = None)` | Initialize the header with a logger configuration. |
| `log(message: str, level: LogLevel = LogLevel.INFO) -> None` | Log a message with the specified level. |
| `log_message(message: str) -> None` | Log a message and store it in the shared log list. |
| `reset_logging() -> None` | Reconfigure logger using the stored config. |
| *(classmethod)* `reset_log_list(cls) -> None` | Clear the shared log list. |
| *(static)* `matches_sytm_format(date_str: str) -> bool` | Check whether a string matches the standard ODF SYTM format. |

#### `validated_base.py`

**class `ValidatedBase(BaseModel)`**

Base model providing validation/normalization similar to old check_* functions.

| Method | Description |
|---|---|
| *(field_validator('*', mode='before'))* `normalize_values(cls, v, info: ValidationInfo)` | Fill in null sentinels and strip quoted strings for any field. |
| *(field_validator('*', mode='before'))* `validate_datetime_format(cls, v, info: ValidationInfo)` | Special handling for fields named *_date (must match SYTM_FORMAT). |

| Function | Description |
|---|---|
| `list_to_dict(lst: list[Any]) -> dict[Any, Any]` | Convert alternating list elements into a dictionary. |
| `clean_strings(lst: list[str]) -> list[str]` | Strip trailing commas and whitespace from each list element. |
| `check_string(value: str) -> str` | Ensure value is a string. Convert Fortran-style exponents (D to E) only in numbers. |
| `check_datetime(value: str \| None) -> str` | Validate datetime string according to SYTM_FORMAT, or return NULL value. |
| `is_valid_datetime(date_str: str) -> bool` | Check whether a string can be parsed as a date/time. |
| `matches_datetime_format(date_str: str, fmt: str) -> bool` | Return True if date_str matches the datetime format fmt. |
| `coerce_datetime(date_str: str, output_fmt: str = '%d-%b-%Y %H:%M:%S.%f') -> str` | Reformat a date/time string to a target format, best-effort. |
| `split_string_with_quotes(input_string: str) -> list[str]` | Split a string into tokens, respecting quoted substrings. |
| `convert_to_float(item: Any) -> Any` | Convert value to float if possible, otherwise return unchanged. |
| `convert_dataframe(df: pd.DataFrame) -> pd.DataFrame` | Convert DataFrame values to floats where possible. |
| `add_commas(lines: str, skip_last: bool = False) -> str` | Add commas at end of each line, skip last if requested. |
| `get_current_date_time() -> str` | Return current date/time in SYTM_FORMAT (truncated). |
| `read_file_lines(file_with_path: str) -> list[str]` | Read all lines from a file and strip whitespace. Print errors to console, always return a list. |
| `find_lines_with_text(odf_file_lines: list[str], substrings: list[str]) -> list[tuple[int, str]]` | Find all lines containing any of the given substrings. |
| `split_lines_into_dict(lines: list) -> dict` | Convert alternating header lines into a dictionary. |

#### `odfhdr.py`

**class `HeaderFieldRangeSchema(TypedDict)`**

**class `OdfHeader(ValidatedBase, BaseHeader)`**

Store metadata, headers, and data associated with an ODF file.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the ODF header and its child header objects. |
| `log_odf_message(message: str, type: str = 'self')` | Log a message for the ODF header. |
| *(field_validator('file_specification'))* `validate_file_specification(cls, v: str) -> str` | Validate that the file specification is not empty. |
| *(field_validator('compass_cal_headers', 'history_headers', 'parameter_headers'))* `ensure_list_items_are_models(cls, v, field)` | Validate that list items provide an ODF serialization method. |
| *(field_validator('quality_header', 'meteo_header'))* `check_optional_headers(cls, v, field)` | Validate an optional header object. |
| `populate_object(odf_dict: dict)` | Populate ODF-level fields from a dictionary. |
| `print_object(file_version: float = 2.0) -> str` | Serialize the ODF header and data to ODF-formatted text. |
| `read_odf(odf_file_path: str)` | Read an ODF file and populate this object. |
| `update_odf() -> None` | Update derived ODF metadata from the current contents. |
| `write_odf(odf_file_path: str, version: float = 2.0) -> None` | Write the ODF object to a file. |
| *(static)* `generate_creation_date() -> str` | Generate the current timestamp in ODF history-header format. |
| `add_history() -> None` | Append a new processing history header. |
| `add_to_history(history_comment) -> None` | Add a processing comment to the most recent history entry. |
| `add_log_to_history() -> None` | Add pending shared log messages to processing history. |
| `add_to_log(message: str) -> None` | Append a message to the shared ODF log. |
| `get_parameter_codes() -> list` | Return the codes of all parameter headers. |
| `get_parameter_names() -> list` | Return the names of all parameter headers. |
| `generate_file_spec() -> str` | Generate a file specification from cruise and event metadata. |
| `generate_set_file_spec() -> str` | Generate a file specification for an event set. |
| `is_parameter_code(code: str) -> bool` | Check whether a parameter code is present. |
| *(static)* `null2empty(df: pd.DataFrame) -> pd.DataFrame` | Replace ODF null values with ``None`` in a DataFrame. |
| `add_quality_flags()` | Add quality-flag parameters and columns to the ODF data. |

#### `cruisehdr.py`

**class `CruiseHeader(ValidatedBase, BaseHeader)`**

A class to represent a Cruise Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the cruise header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('start_date', 'end_date', mode='before'))* `handle_empty_dates(cls, v)` | Replace an empty date string with the ODF SYTM null value. |
| *(field_validator('*', mode='before'))* `strip_strings(cls, v, info)` | Strip surrounding quotes and whitespace from string fields. |
| `log_cruise_message(field: str, old_value, new_value) -> None` | Log a change made to a cruise header field. |
| `populate_object(cruise_fields: list[str])` | Populate fields from parsed ODF cruise header lines. |
| `print_object(file_version: float = 2.0) -> str` | Serialize the cruise header to ODF-formatted text. |

#### `eventhdr.py`

**class `EventHeader(ValidatedBase, BaseHeader)`**

A class to represent an Event Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the event header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('*', mode='before'))* `strip_strings(cls, v)` | Strip surrounding quotes, asterisks, and whitespace from strings. |
| *(field_validator('initial_latitude', 'initial_longitude', 'end_latitude', 'end_longitude', 'min_depth', 'max_depth', 'sampling_interval', 'sounding', 'depth_off_bottom', mode='before'))* `validate_floats(cls, v, info: ValidationInfo)` | Coerce a numeric field to a native Python float. |
| `log_event_message(field: str, old_value, new_value) -> None` | Log a change made to an event header field. |
| `set_event_comment(event_comment: str, comment_number: int = 0) -> None` | Add or replace an entry in ``event_comments``. |
| `populate_object(event_fields: list)` | Populate fields from parsed ODF event header lines. |
| `print_object() -> str` | Serialize the event header to ODF-formatted text. |

#### `historyhdr.py`

**class `HistoryHeader(ValidatedBase, BaseHeader)`**

A class to represent a History Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the history header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('creation_date', mode='before'))* `validate_creation_date(cls, v)` | Normalize the creation date to a stripped, upper-case string. |
| *(field_validator('processes', mode='before'))* `validate_processes(cls, v)` | Normalize the ``processes`` field to a list of stripped strings. |
| `log_history_message(field: str, old_value: str, new_value: str) -> None` | Log a change made to a history header field. |
| `set_process(process: str, process_number: int = 0) -> None` | Add or replace an entry in ``processes``. |
| `add_process(process: str) -> None` | Append a processing step to ``processes``. |
| `find_process(search_string: str) -> list[int]` | Find the indices of processes containing a search string. |
| `populate_object(history_fields: list) -> 'HistoryHeader'` | Populate fields from parsed ODF history header lines. |
| `print_object() -> str` | Serialize the history header to ODF-formatted text. |

#### `qualityhdr.py`

**class `QualityHeader(ValidatedBase, BaseHeader)`**

A class to represent a Quality Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the quality header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('quality_date', mode='before'))* `validate_quality_date(cls, v)` | Normalize and validate the quality date. |
| *(field_validator('quality_tests', 'quality_comments', mode='before'))* `validate_lists(cls, v)` | Normalize ``quality_tests``/``quality_comments`` to a list of strings. |
| `log_quality_message(field: str, old_value: str, new_value: str) -> None` | Log a change made to a quality header field. |
| `set_quality_test(quality_test: str, test_number: int = 0) -> None` | Add or replace an entry in ``quality_tests``. |
| `add_quality_test(quality_test: str) -> None` | Append a quality-control test description to ``quality_tests``. |
| `set_quality_comment(quality_comment: str, comment_number: int = 0) -> None` | Add or replace an entry in ``quality_comments``. |
| `add_quality_comment(quality_comment: str) -> None` | Append a comment to ``quality_comments``. |
| `add_quality_codes() -> None` | Append the standard quality-code definitions and set the date. |
| `add_qcff_info() -> None` | Append the standard QCFF flag description and set the date. |
| `populate_object(quality_fields: list) -> 'QualityHeader'` | Populate fields from parsed ODF quality header lines. |
| `print_object() -> str` | Serialize the quality header to ODF-formatted text. |

#### `parameterhdr.py`

**class `ParameterHeader(ValidatedBase, BaseHeader)`**

A class to represent a Parameter Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the parameter header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('*', mode='before'))* `strip_strings(cls, v)` | Strip surrounding quotes and whitespace from string fields. |
| `log_parameter_message(field: str, old_value: str, new_value: str) -> None` | Log a change made to a parameter header field. |
| *(static)* `is_float_and_int(value) -> bool` | Check whether a value represents a whole-number float. |
| `populate_object(parameter_fields: list) -> 'ParameterHeader'` | Populate fields from parsed ODF parameter header lines. |
| `print_object(file_version: float = 2.0) -> str` | Serialize the parameter header to ODF-formatted text. |

#### `instrumenthdr.py`

**class `InstrumentHeader(ValidatedBase, BaseHeader)`**

A class to represent an Instrument Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the instrument header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('*', mode='before'))* `strip_strings(cls, v)` | Strip surrounding quotes and whitespace from string fields. |
| `log_instrument_message(field: str, old_value: str, new_value: str) -> None` | Log a change made to an instrument header field. |
| `populate_object(instrument_fields: list)` | Populate fields from parsed ODF instrument header lines. |
| `print_object() -> str` | Serialize the instrument header to ODF-formatted text. |

#### `recordhdr.py`

**class `RecordHeader(ValidatedBase, BaseHeader)`**

A class to represent a Record Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the record header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('num_calibration', 'num_swing', 'num_history', 'num_cycle', 'num_param', mode='before'))* `validate_ints(cls, v)` | Coerce a count field to a native Python int. |
| `log_record_message(field: str, old_value: Any, new_value: Any) -> None` | Log a change made to a record header field. |
| `populate_object(record_fields: list) -> 'RecordHeader'` | Populate fields from parsed ODF record header lines. |
| `print_object() -> str` | Serialize the record header to ODF-formatted text. |

#### `records.py`

**class `DataRecords(ValidatedBase, BaseHeader)`**

Represents the data records stored within an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the data records container. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this object. |
| *(field_validator('data_frame'))* `validate_dataframe(cls, v: pd.DataFrame) -> pd.DataFrame` | Validate that ``data_frame`` is a pandas DataFrame. |
| *(field_validator('parameter_list', mode='before'))* `validate_parameters(cls, v: list[str]) -> list[str]` | Normalize each parameter code in ``parameter_list``. |
| *(field_validator('print_formats', mode='before'))* `validate_print_formats(cls, v: dict[str, str]) -> dict[str, str]` | Validate and normalize the ``print_formats`` mapping. |
| `log_data_message(field: str, old_value, new_value) -> None` | Log a change made to a data field. |
| `populate_object(parameter_list: list[str], data_formats: dict[str, str], data_lines_list: list[str]) -> Self` | Populate the data frame from parsed ODF data lines. |
| `print_object() -> str` | Return V3 style CSV representation of the data. |
| `print_object_old_style() -> str` | Return V2 style fixed-width string representation of the data. |

#### `polynomialhdr.py`

**class `PolynomialCalHeader(ValidatedBase, BaseHeader)`**

A class to represent a Polynomial Calibration Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the polynomial calibration header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('parameter_code', mode='before'))* `strip_param_code(cls, v)` | Strip surrounding quotes and whitespace from the parameter code. |
| *(field_validator('calibration_date', 'application_date', mode='before'))* `validate_dates(cls, v)` | Validate and normalize a calibration or application date. |
| *(field_validator('number_coefficients', mode='before'))* `validate_num_coeffs(cls, v)` | Coerce ``number_coefficients`` to a native Python int. |
| *(field_validator('coefficients', mode='before'))* `validate_coefficients(cls, v)` | Normalize ``coefficients`` to a list of floats. |
| `log_poly_message(field: str, old_value, new_value) -> None` | Log a change made to a polynomial calibration header field. |
| `set_coefficient(coefficient: float, coefficient_number: int = 0) -> None` | Add or replace a coefficient and update ``number_coefficients``. |
| `populate_object(polynomial_cal_fields: list) -> 'PolynomialCalHeader'` | Populate fields from parsed ODF polynomial calibration header lines. |
| `print_object() -> str` | Serialize the polynomial calibration header to ODF-formatted text. |

#### `generalhdr.py`

**class `GeneralCalHeader(ValidatedBase, BaseHeader)`**

A class to represent a General Cal Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the general calibration header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('parameter_code', mode='before'))* `strip_param_code(cls, v)` | Normalize the parameter code to a stripped, upper-case string. |
| *(field_validator('calibration_type', mode='before'))* `strip_cal_type(cls, v)` | Strip surrounding quotes and whitespace from the calibration type. |
| *(field_validator('calibration_date', 'application_date', mode='before'))* `validate_dates(cls, v)` | Validate and normalize a calibration or application date. |
| *(field_validator('number_coefficients', mode='before'))* `validate_num_coeffs(cls, v)` | Coerce ``number_coefficients`` to a native Python int. |
| *(field_validator('coefficients', mode='before'))* `validate_coefficients(cls, v)` | Normalize ``coefficients`` to a list of floats. |
| *(field_validator('calibration_equation', mode='before'))* `strip_cal_eqn(cls, v)` | Strip surrounding quotes and whitespace from the calibration equation. |
| *(field_validator('calibration_comments', mode='before'))* `validate_comments(cls, v)` | Normalize ``calibration_comments`` to a list of stripped strings. |
| `log_general_message(field: str, old_value, new_value) -> None` | Log a change made to a general calibration header field. |
| `set_coefficient(general_coefficient: float, general_coefficient_number: int = 0) -> None` | Add or replace a coefficient and update ``number_coefficients``. |
| `set_calibration_comment(calibration_comment: str, comment_number: int = 0) -> None` | Add or replace an entry in ``calibration_comments``. |
| `add_calibration_comment(calibration_comment: str) -> None` | Append a comment to ``calibration_comments``. |
| `populate_object(general_cal_fields: list) -> 'GeneralCalHeader'` | Populate fields from parsed ODF general calibration header lines. |
| `print_object() -> str` | Serialize the general calibration header to ODF-formatted text. |

#### `compasshdr.py`

**class `CompassCalHeader(ValidatedBase, BaseHeader)`**

A class to represent a Compass Cal Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the compass calibration header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('parameter_code', mode='before'))* `strip_param_code(cls, v)` | Strip surrounding quotes and whitespace from the parameter code. |
| *(field_validator('calibration_date', 'application_date', mode='before'))* `validate_dates(cls, v)` | Validate and normalize a calibration or application date. |
| *(field_validator('directions', 'corrections', mode='before'))* `validate_float_lists(cls, v)` | Normalize ``directions``/``corrections`` to a list of floats. |
| `log_compass_message(field: str, old_value, new_value) -> None` | Log a change made to a compass calibration header field. |
| `set_direction(direction: float, direction_number: int = 0) -> None` | Add or replace an entry in ``directions``. |
| `set_correction(correction: float, correction_number: int = 0) -> None` | Add or replace an entry in ``corrections``. |
| `populate_object(compass_cal_fields: list) -> 'CompassCalHeader'` | Populate fields from parsed ODF compass calibration header lines. |
| `print_object() -> str` | Serialize the compass calibration header to ODF-formatted text. |

#### `meteohdr.py`

**class `MeteoHeader(ValidatedBase, BaseHeader)`**

A class to represent a Meteo Header in an ODF object.

| Method | Description |
|---|---|
| `__init__(config = None, **data)` | Initialize the meteo header. |
| `set_logger_and_config(logger, config)` | Attach a shared logger and config to this header. |
| *(field_validator('meteo_comments', mode='before'))* `validate_comments(cls, v)` | Normalize ``meteo_comments`` to a list of stripped strings. |
| `log_meteo_message(field: str, old_value, new_value) -> None` | Log a change made to a meteo header field. |
| `set_meteo_comment(meteo_comment: str, comment_number: int = 0) -> None` | Add or replace an entry in ``meteo_comments``. |
| `add_meteo_comment(meteo_comment: str) -> None` | Append a comment to ``meteo_comments``. |
| `populate_object(meteo_fields: list) -> 'MeteoHeader'` | Populate fields from parsed ODF meteo header lines. |
| `print_object() -> str` | Serialize the meteo header to ODF-formatted text. |
| *(static)* `wind_speed_knots_to_ms(wind_speed_knots: float) -> float` | Convert wind speed from knots to metres per second. |
| *(static)* `cloud_cover_percentage_to_wmo_code(cloud_cover_percentage: float) -> int` | Convert a cloud-cover fraction to its WMO cloud-cover code. |
| *(static)* `wave_height_meters_to_wmo_code(wave_height_meters: float) -> int` | Convert a wave height to its WMO wave-height (sea-state) code. |

### Instrument & File-Format Utilities

#### `compare_seabird_xmlcons.py`

| Function | Description |
|---|---|
| `parse_xmlcon(filename: str) -> pd.DataFrame` | Parse a Sea-Bird .xmlcon file into a sensor DataFrame. |
| `compare_xmlcons(df: pd.DataFrame) -> pd.DataFrame` | Find rows where a sensor's serial number changes between events. |
| `transform_to_wide_format(df: pd.DataFrame) -> pd.DataFrame` | Pivot a long-format sensor-change table to wide format. |

#### `concatenate_qat_files.py`

| Function | Description |
|---|---|
| `concatenate_qat_files(mission_number: str, qat_folder_path: str)` | Concatenate all .qat files in a folder into one CSV file. |

#### `fix_btl_header.py`

fix_btl_header.py

| Function | Description |
|---|---|
| `fix_header(header: str) -> str` | Return the header with the proper spacing between column names. |

#### `lookup_parameter.py`

**class `ParamInfo(TypedDict)`**

Metadata describing an ODF parameter code.

| Function | Description |
|---|---|
| `lookup_parameter(database: str, parameter: str) -> ParamInfo` | Get the parameter information from the a database. |

#### `netcdfhdr.py`

**class `NetCdfHeader(OdfHeader)`**

NetCdfHeader Class: subclass of OdfHeader.

| Method | Description |
|---|---|
| `__init__()` | Method that initializes an NetCdf class object. |
| `generate_creation_date() -> str` | Generate a creation date in SYTM format. |
| `populate_parameter_headers(df: pd.DataFrame, seabird_names: list, long_names: list, units: list) -> NoReturn` | Populate the parameter headers and the data object. |
| `main()` |  |

#### `odf_to_exchange_format.py`

| Function | Description |
|---|---|
| `odf2exchange(odf_folder: Path, wildcard: str) -> None` | Generate CCHDO Exchange Formatted files from ODF files. |

#### `read_seaodf_ini.py`

| Function | Description |
|---|---|
| `read_seaodf_ini()` | Parse the shared ``seaodf.ini`` parameter mapping file. |

#### `read_seaodf_parameters.py`

| Function | Description |
|---|---|
| `read_seaodf_parameters() -> pd.DataFrame` | Read the packaged SeaODF parameters lookup table. |

#### `rbr_to_odf.py`

| Function | Description |
|---|---|
| `convert_rbr_to_odf(rsk_file_path: str, station_latitude: float = 0.0, station_longitude: float = 0.0)` | Read an RBR .rsk file, derive sigma-t, and plot selected profiles. |

#### `remove_parameter.py`

| Function | Description |
|---|---|
| `remove_parameter(odfobj: OdfHeader, code: str) -> OdfHeader` | Removes a parameter from the input OdfHeader object. |

### MTR / Thermograph Processing

#### `thermograph.py`

**class `ThermographHeader(OdfHeader)`**

Mtr Class: subclass of OdfHeader.

| Method | Description |
|---|---|
| `__init__() -> None` | Initialize the thermograph header. |
| `get_date_format() -> str` | Return the ``strptime`` format used for the ``date`` column. |
| `get_time_format() -> str` | Return the ``strptime`` format used for the ``time`` column. |
| *(static)* `clean_lfa(value)` | Coerce an LFA value to an int where possible. |
| *(static)* `clean_soakday(value)` | Coerce a soak-days value to an int where possible. |
| *(static)* `load_meta_file(metafile)` | Load a metadata file into a DataFrame, dispatching by extension. |
| `start_date_time(df: pd.DataFrame) -> datetime` | Retrieve the first date-time value from the data frame. |
| `end_date_time(df: pd.DataFrame) -> datetime` | Retrieve the last date-time value from the data frame. |
| `get_sampling_interval(df: pd.Series) -> float` | Compute the time interval between the first two date-time values. |
| `create_sytm(df: pd.DataFrame) -> pd.DataFrame` | Updated the data frame with the proper SYTM column. |
| *(static)* `check_datetime_format(date_string, format)` | Check whether a string matches a given date/time format. |
| *(static)* `fix_datetime(df: pd.DataFrame, date_times: bool) -> pd.DataFrame` | Fix the date and time columns in the data frame. |
| *(static)* `convert_to_decimal_degrees(pos: str) -> float` | Convert a degrees/decimal-minutes position string to decimal degrees. |
| *(static)* `extract_number(s: str) -> float \| None` | Extract a numeric value from a string, ignoring non-numeric characters. |
| `populate_parameter_headers(df: pd.DataFrame)` | Populate the parameter headers and the data object. |
| *(static)* `is_minilog_file(file_path: str) -> bool` | Check whether a file looks like a Minilog MTR file. |
| *(static)* `read_mtr(mtrfile: str, instrument_type: str = 'minilog') -> dict` | Read an MTR data file and return a pandas DataFrame. |
| *(static)* `read_metadata(metafile: str, institution: str) -> pd.DataFrame` | Read a Metadata file and return a pandas DataFrame. |
| `process_thermograph(institution_name: str, instrument_type: str, metadata_file_path: str, data_file_path: str, user_input_metadata: dict) -> None` | Populate this ODF object from raw MTR data and metadata. |

#### `multinet.py`

**class `MultinetHeader(OdfHeader)`**

Multinet Class: subclass of OdfHeader.

| Method | Description |
|---|---|
| `__init__(calibrations = None) -> NoReturn` | Initialize the multinet header. |
| *(property)* `calibrations()` | dict: Calibration coefficients, keyed by channel name. |
| `calibrations(cals: dict) -> NoReturn` |  |
| `get_date_format() -> str` | Return the ``strptime`` format used for the ``date`` column. |
| `get_time_format() -> str` | Return the ``strptime`` format used for the ``time`` column. |
| `start_date_time(df: pd.Series) -> datetime` | Retrieve the first date-time value from the data frame. |
| `end_date_time(df: pd.Series) -> datetime` | Retrieve the last date-time value from the data frame. |
| `sampling_interval(df: pd.Series) -> int` | Compute the time interval between the first two date-time values. |
| `create_sytm(df: pd.DataFrame) -> pd.DataFrame` | Updated the data frame with the proper SYTM column. |
| *(static)* `check_datetime_format(date_string, format)` | Check whether a string matches a given date/time format. |
| `fix_datetime(df: pd.DataFrame) -> pd.DataFrame` | Fix the date and time columns in the data frame. |
| *(static)* `read_tab_delimited_file(file_path)` | Reads a text file with header lines and tab-delimited data, |
| *(static)* `fix_column_names(names: list) -> list` | Normalize raw column-name strings into snake_case identifiers. |
| *(static)* `split_calibration(cal_string: str) -> list` | Splits a calibration string into a list of floats. |
| `extract_calibrations(header_lines) -> NoReturn` | Parse temperature/conductivity/pressure/volume calibrations. |
| *(static)* `compute_conductivity(conductivity_raw: pd.Series, ccal: list) -> float` | Computes the conductivity in mS/cm by applying a calibration equation to the raw conductivity values. |
| *(static)* `compute_temperature(temp_raw: pd.Series, tcal: list) -> float` | Computes the temperature in Celsius by applying a calibration equation to the raw temperature voltavaluesge. |
| *(static)* `compute_pressure(pressure_raw: pd.Series, pressure_temp_raw: pd.Series, pcal: list) -> float` | Computes the pressure in dbar by applying a calibration equation to the raw pressure values. |
| *(static)* `compute_volume(volume_raw: pd.Series, vcal: float) -> float` | Computes the volume in m**3 by applying a calibration equation to the raw volume values. |
| *(static)* `compute_flow(flow_raw: pd.Series) -> float` | Computes the flow rate by applying a calibration to the raw flow rate. |
| *(static)* `compute_flow_ratio(flow_in: pd.Series, flow_out: pd.Series) -> pd.Series` | Computes the flow rate by applying a calibration to the raw flow rate. |
| `populate_odf_headers(df: pd.DataFrame)` | Populate the ODF headers and the data object. |
| `populate_parameter_headers(df: pd.DataFrame)` | Populate the parameter headers and the data object. |
| `read_multinet_files(file_type: str, file_path: str) -> pd.DataFrame` | Main function to read a tab-delimited file and print the header and data lines. |

#### `process_mtr_files.py`

**class `MTRProcessingThread(QThread)`**

Worker thread to process MTR data without blocking the GUI.

| Method | Description |
|---|---|
| `__init__(metadata_file_path, input_path, output_path, operator, institution, instrument, user_metadata, batch_id)` | Initialize the processing thread. |
| `run()` | Run :func:`run_process_thermograph_data` and emit :attr:`finished`. |

| Function | Description |
|---|---|
| `process_mtr_files_for_worker(log, metadata_file_path, input_data_folder_path, output_data_folder_path, operator, institution, instrument, batch_id, user_input_metadata)` | Process a batch of raw MTR ``.csv`` files into ODF files (worker entry point). |
| `run_automated_start_qc()` | Run the automated (multi-batch, background-worker) MTR processing UI. |
| `process_thermograph_data(metadata_file_path, input_data_folder_path, output_data_folder_path, operator, institution, instrument, user_input_metadata, batch_id)` | Process a batch of raw MTR ``.csv`` files into ODF files (synchronous). |
| `run_process_thermograph_data(metadata_file_path, input_data_folder_path, output_data_folder_path, operator, institution, instrument, user_input_metadata, batch_id)` | Run :func:`process_thermograph_data` and log the outcome. |
| `main_select_inputs()` | Show the input selection dialog and block until it closes. |
| `initialize_mtr_process(log_ui: LogWindowProcessMTR, logger)` | Collect processing inputs and start the MTR processing thread. |
| `exit_program(app, log_ui)` | Stop any running MTR processing thread and quit the application. |
| `run_manual_start_qc()` | Run the manual (single-batch, button-driven) MTR processing UI. |
| `logger_setup()` | Create (or return the existing) MTR-processing logger. |
| `attach_gui_logger(logger, gui_handler)` | Attach a GUI log handler to a logger via a background queue listener. |
| `on_mtr_processing_finished(log_ui, success)` | Handle completion of an :class:`MTRProcessingThread`. |

#### `ai_thermograph_data.py`

| Function | Description |
|---|---|
| `regional_meta_bioregions()` | Load the DFO marine bioregions GeoJSON lookup file. |
| `regional_meta_temp_climatology()` | Load the seasonal surface-temperature climatology lookup file. |
| `point_in_polygon(lon, lat, polygon)` | Check whether a point lies inside a polygon (ray-casting test). |
| `get_bioregion(lat, lon)` | Determine which DFO marine bioregion contains a point. |
| `get_surface_temp_profile(lat, lon)` | Look up the seasonal surface-temperature profile for a location. |
| `get_season(dt)` | Return climatological season name for a datetime. |
| `prepare_output_folder(in_folder_path: str, out_folder_path: str, qc_operator: str) -> str` | Create (or clear and recreate) the ``Step_2_Assign_QFlag`` output folder. |
| `qc_ai_thermograph_data(in_folder_path: str, wildcard: str, out_folder_path: str, qc_operator: str)` | Automatically quality-flag a batch of thermograph ODF files. |
| `main_select_inputs()` | Show the input/output folder selection dialog and block until closed. |

### Quality Control & Reporting

#### `qc_odf_data.py`

qc_odf_data.py

**class `LassoItem(pg.GraphicsObject)`**

Freehand lasso selector.

| Method | Description |
|---|---|
| `__init__(plot_item: pg.PlotItem, xs: np.ndarray, ys: np.ndarray)` | Initialize the lasso selector. |
| `set_point_sets(point_sets)` | Replace the data the lasso hit-tests against. |
| `pause()` | Disable the lasso and discard any in-progress selection. |
| `resume()` | Re-enable the lasso for left-button drawing. |
| `boundingRect()` | Return the current view's bounding rectangle. |
| `paint(p, *args)` | Paint the in-progress lasso outline. |
| `_scene_to_data(scene_pos)` | Convert a scene position to data coordinates. |
| `mousePressEvent(ev)` | Start a new lasso outline on a left-button press. |
| `mouseMoveEvent(ev)` | Extend the in-progress lasso outline as the mouse moves. |
| `mouseReleaseEvent(ev)` | Close the lasso outline and finalize the selection on release. |
| `_finish()` | Hit-test the closed lasso polygon and emit :attr:`sigSelected`. |

**class `QCWindow(QWidget)`**

Unified interactive QC window.

| Method | Description |
|---|---|
| `__init__(mode: str, df: pd.DataFrame \| None, state: dict, xnums: np.ndarray \| None = None, qc_start_ts: float \| None = None, qc_end_ts: float \| None = None, start_datetime_qc = None, end_datetime_qc = None, batch_name: str = '', pres_col: str \| None = None, x_col_default: str \| None = None, station: str = '—', event_num: str = '—', ctd_profiles: list[dict] \| None = None, colors_initial: list \| None = None, instrument: str = '', organization: str = '', qc_mode_: str = '', qc_mode_code_: int = 0, block_next_: int = 0, idx: int = 1, file_list: list \| None = None, current_file = None, param_map: dict \| None = None)` | Initialise the QC window and build all UI components. |
| *(static)* `_compute_margins(xs: np.ndarray, ys: np.ndarray)` | Compute 5% plot-range margins for a pair of coordinate arrays. |
| `_current_active_col() -> str` | Return the name of the column currently plotted on the selectable axis. |
| `_current_xs() -> np.ndarray` | X-values for the current scatter (thermograph: timestamps; CTD: param). |
| `_current_ys() -> np.ndarray` | Y-values for the current scatter (thermograph: param; CTD: pressure). |
| `_profile_xs(prof: dict) -> np.ndarray` | X-values (current axis param) for one CTD profile in self._profiles. |
| `_set_button_active(active_btn)` | Highlight the active interaction-mode button. |
| `_click_lasso()` | Switch to lasso selection mode. |
| `_click_zoom_box()` | Switch to rectangular zoom-box mode. |
| `_click_pan()` | Switch to pan mode. |
| `_switch_axis(col_name: str)` | Handle Y-axis switch (thermograph) or X-axis switch (CTD). |
| `_on_flag_selected(flag_id: int)` | Store the newly selected QC flag as the "current" flag to apply. |
| `_apply_flags_to_points(indices: np.ndarray)` | Apply the current flag to points at the given indices and recolor them. |
| `_apply_flags_to_profile(profile_idx: int, indices: np.ndarray)` | CTD-only: apply the current flag to one overlaid profile's points. |
| `_record_selection(profile_idx: int, indices: np.ndarray)` | CTD-only: track a selection group against a specific profile for undo/export. |
| `_on_lasso_select(selections)` | Apply the current flag to points selected by the lasso. |
| `_on_points_clicked(_plot, points, profile_idx: int = 0)` | Apply the current flag to individually clicked scatter points. |
| `_click_reset_view()` | Redraw the scatter(s) with current flag colors and reset the axis ranges. |
| `_click_deselect_all()` | Restore all quality flags to their pre-session snapshot values. |
| `_click_continue()` | Mark the QC session as applied and close the window. |
| `_click_exit()` | Mark the QC session as user-exited and close the window. |
| `_toggle_profile_visibility(profile_idx: int, cb_state)` | CTD-only: show/hide one overlaid profile without affecting its flags. |
| `_export_dataframe(current_file)` | Export the QC'd DataFrame(s) to CSV. |
| `closeEvent(ev)` | Emit :attr:`closed` before handling the standard close event. |

**class `InputDialog(QMainWindow)`**

Unified input dialog.

| Method | Description |
|---|---|
| `__init__(mode: str, review_mode: bool)` | Build the dialog's widgets and layout. |
| `_choose_input()` | Prompt for and store the ODF input folder. |
| `_choose_output()` | Prompt for and store the QC output folder. |
| `_choose_metadata()` | Prompt for and store the metadata file (thermograph mode). |
| `_on_accept()` | Validate required fields, optionally persist the name, and close. |
| `_on_reject()` | Set :attr:`result` to ``"reject"`` and close the window. |
| `_save_name()` | Persist the operator/reviewer name to :attr:`_meta_store` as JSON. |
| `_clear_saved()` | Delete the persisted name file, if one exists. |
| `_load_saved()` | Load and apply a previously persisted operator/reviewer name, if any. |

**class `LogWindow(QWidget)`**

Unified log window with data-type selector, QC mode radio, Start and

| Method | Description |
|---|---|
| `__init__()` | Build the window's widgets and layout. |
| *(property)* `selected_data_type() -> str` | str: ``"thermograph"`` or ``"ctd"``, per the selected radio button. |

**class `_FilenameMismatchError(Exception)`**

Raised by _load_ctd_profile when the ODF's generated file spec doesn't

| Function | Description |
|---|---|
| `prepare_output_folder(in_folder_path: str, out_folder_path: str, qc_operator: str) -> str` | Create the appropriate QC output folder for initial or review mode. |
| `_parse_datetime(date_str, time_str)` | Parse separate date/time strings into a combined datetime string. |
| `_parse_to_utc(dt_str, tz_mode)` | Parse a datetime string and convert it to UTC. |
| `_validate_bio_metadata(meta: pd.DataFrame) -> bool` | Check that a BIO metadata DataFrame has the required columns. |
| `_null_to_na(df: pd.DataFrame) -> pd.DataFrame` | Replace ODF's numeric null sentinel with NaN. |
| `qc_thermograph_data(in_folder_path: str, wildcard: str, out_folder_path: str, qc_operator: str, metadata_file_path: str, review_mode: bool, batch_name: str) -> dict` | Run the interactive visual QC loop over a batch of thermograph ODF files. |
| `_cast_label_from_filename(ctd_file_name: str) -> str` | Infer a human-readable cast label from an ODF filename suffix. |
| `_load_ctd_profile(ctd_file: Path, in_folder_path: str, qc_mode_user: int) -> dict \| None` | Read one ODF file and prepare everything QCWindow needs to plot it. |
| `_group_ctd_profiles(profiles: list[dict]) -> list[list[dict]]` | Group loaded CTD profiles by (station, event) so that associated |
| `qc_ctd_data(in_folder_path: str, wildcard: str, out_folder_path: str, qc_operator: str, review_mode: bool) -> dict` | Run the interactive visual QC loop over a batch of CTD ODF files. |
| `main_select_inputs(mode: str, review_mode: bool)` | Open the input dialog and return collected values. |
| `run_qc_thermograph_data(input_path: str, output_path: str, qc_operator: str, metadata_file_path: str, review_mode: bool, batch_name: str, wildcard: str) -> dict` | Run :func:`qc_thermograph_data` and log the outcome. |
| `run_qc_ctd_data(input_path: str, output_path: str, qc_operator: str, review_mode: bool, wildcard: str) -> dict` | Run :func:`qc_ctd_data` and log the outcome. |
| `start_qc_process(log_ui: LogWindow)` | Handle the log window's "Start" button: collect inputs and run QC. |
| `exit_program(app_inst)` | Signal the running QC loop to stop and quit the application. |

#### `metadata_report.py`

| Function | Description |
|---|---|
| `generate_report(file_path: str, wildcard: str, outfile: str) -> None` | Generates a report based on the metadata from ODF files as an Excel file. |

### GUI Support Widgets

#### `log_window.py`

**class `LogEmitter(QObject)`**

Qt object that emits a signal carrying a line of log text.

**class `LogWindow(QWidget)`**

Standalone window that displays streamed log/print output.

| Method | Description |
|---|---|
| `__init__(parent = None)` | Build the log window's widgets and layout. |
| `_append_text(text: str)` | Append a line of text to the log box and scroll to it. |
| `write(text: str)` | Directly append text (convenience). |
| `redirect_prints_to_log()` | Call this to redirect sys.stdout to the log window (optional). |
| `export_log()` | Export the current log content to a text file. |
| `_exit_app()` | Emit exit request to Main Application. |
| `_bring_to_front_and_maximize()` | Brings the window to the front and maximizes it. |

**class `Worker(QThread)`**

Background thread that runs a callable and reports its outcome.

| Method | Description |
|---|---|
| `__init__(func, *args, **kwargs)` | Initialize the worker. |
| `run()` | Run ``func`` on this thread and emit the resulting signal. |

**class `SafeConsoleFilter(logging.Filter)`**

Ensures console output is cp1252-safe by stripping unsupported characters.

| Method | Description |
|---|---|
| `filter(record)` | Strip characters that cp1252 cannot encode from a log record. |

**class `QTextEditLogger(logging.Handler)`**

A logging.Handler that appends logs to a QTextEdit widget in the GUI.

| Method | Description |
|---|---|
| `__init__(text_edit: QTextEdit)` | Initialize the handler. |
| `emit(record)` | Format a log record and append it to the text widget. |

**class `LogWindowThermographQC(QWidget)`**

Log window for the interactive thermograph QC workflow.

| Method | Description |
|---|---|
| `__init__()` | Build the window's widgets and layout. |

**class `LogWindowProcessMTR(QWidget)`**

Log window for processing raw MTR (thermograph) files to ODF.

| Method | Description |
|---|---|
| `__init__()` | Build the window's widgets and layout. |

**class `LogWindowCTDQC(QWidget)`**

Log window for the interactive CTD QC workflow.

| Method | Description |
|---|---|
| `__init__()` | Build the window's widgets and layout. |

**class `LogWindowProcessCTD(QWidget)`**

Log window for the CTD ODF-file processing/inspection workflow.

| Method | Description |
|---|---|
| `__init__()` | Build the window's widgets and layout. |

#### `select_metadata_file_and_data_folder.py`

**class `MainWindow(QMainWindow)`**

Dialog for collecting MTR/thermograph processing inputs.

| Method | Description |
|---|---|
| `__init__()` | Build the window's widgets and layout. |
| `editing_finished()` | Store and log the processor name once editing of the field ends. |
| `institution_text_changed(s)` | Update the instrument options for the newly selected institution. |
| `instrument_text_changed(s)` | Store the newly selected instrument. |
| `find_raw_data_folder(base_dir)` | Search for a folder containing 'raw' in its name (case-insensitive) |
| `choose_metadata_file()` | Prompt for the metadata file and auto-fill the folder fields. |
| `choose_input_data_folder()` | Prompt for and store the input data folder. |
| `choose_output_data_folder()` | Prompt for and store the output data folder. |
| `on_accept()` | Collect all field values, optionally persist them, and close. |
| `on_reject()` | Set :attr:`result` to ``"reject"`` and close the window. |
| `save_last_user_metadata()` | Persist :attr:`remember_input_dict` to :attr:`meta_store_path` as JSON. |
| `clear_last_user_metadata()` | Delete the persisted metadata file, if one exists. |
| `populate_defaults(institution)` | Populate 4 fields based on institution selection. |
| `load_last_user_metadata()` | Load and apply any previously persisted metadata, or defaults. |

**class `SubWindowOne(QMainWindow)`**

Dialog for collecting QC-flagging run inputs.

| Method | Description |
|---|---|
| `__init__(review_mode: bool)` | Build the window's widgets and layout. |
| `editing_finished()` | Store and log the reviewer/operator name once editing ends. |
| `find_raw_data_folder(base_dir)` | Search for a folder containing 'raw' in its name (case-insensitive) |
| `build_batch_name(meta_path: str) -> str` | Derive a batch name (e.g. ``"LFA-34-2024"``) from a metadata filename. |
| `choose_metadata_file()` | Prompt for the metadata file and auto-fill folder/batch fields. |
| `choose_input_data_folder()` | Prompt for and store the input ODF folder. |
| `choose_output_data_folder()` | Prompt for and store the QC output folder. |
| `on_accept()` | Validate required fields, optionally persist them, and close. |
| `on_reject()` | Set :attr:`result` to ``"reject"`` and close the window. |
| `save_last_user_metadata()` | Persist :attr:`remember_input_dict` to :attr:`meta_store_path` as JSON. |
| `clear_last_user_metadata()` | Delete the persisted metadata file, if one exists. |
| `load_last_user_metadata()` | Load and apply any previously persisted reviewer name, or defaults. |
| `populate_defaults()` | Set the reviewer-name field's placeholder text. |

### Package Setup / Entry Scripts

#### `__init__.py`

datashop_toolbox package initialization.

Re-exports the package's public API:

`BaseHeader`, `CompassCalHeader`, `CruiseHeader`, `EventHeader`, `GeneralCalHeader`, `HistoryHeader`, `InstrumentHeader`, `MeteoHeader`, `OdfHeader`, `ParameterHeader`, `PolynomialCalHeader`, `QualityHeader`, `RecordHeader`, `DataRecords`, `ValidatedBase`, `ThermographHeader`, `generate_report`, `MainWindow`, `SubWindowOne`

#### `create_parameters_database.py`

_No public classes or functions (script / entry point)._

#### `demo_validated_base.py`

**class `SampleHeader(ValidatedBase)`**

| Function | Description |
|---|---|
| `demo_validated_base()` |  |

#### `generate_metadata_report.py`

_No public classes or functions (script / entry point)._

## `odf_oracle`

### Connection Management

#### `__init__.py`

Re-exports the package's public API:

`compass_cal_to_oracle`, `cruise_event_to_oracle`, `data_to_oracle`, `event_comments_to_oracle`, `fix_null`, `general_cal_comments_to_oracle`, `general_cal_equation_to_oracle`, `general_cal_to_oracle`, `history_to_oracle`, `instrument_to_oracle`, `meteo_comments_to_oracle`, `meteo_to_oracle`, `odf_to_oracle`, `polynomial_cal_to_oracle`, `quality_to_oracle`, `quality_comments_to_oracle`, `quality_tests_to_oracle`, `sytm_to_timestamp`

#### `database_connection_pool.py`

| Function | Description |
|---|---|
| `init_session(connection, requested_tag)` | Modify some settings of the Oracle connection. |
| `get_database_pool()` | Create an Oracle connection pool for the ODF_ARCHIVE database. |

### Value Conversion Helpers

#### `fix_null.py`

| Function | Description |
|---|---|
| `fix_null(x)` | Convert all null values in the input matrix to NaNs. |

#### `sytm_to_timestamp.py`

| Function | Description |
|---|---|
| `sytm_to_timestamp(sytm: str, strid: str) -> datetime` | Convert SYTM strings to Oracle timestamps. |

### ODF-to-Oracle Loaders

#### `odf_to_oracle.py`

| Function | Description |
|---|---|
| `odf_to_oracle(wildcard: str, user: str, password: str, oracle_host: str, oracle_service_name: str, mypath: str) -> None` | Read ODF files and load them into the ODF_ARCHIVE Oracle database. |

#### `cruise_event_to_oracle.py`

| Function | Description |
|---|---|
| `cruise_event_to_oracle(odfobj: OdfHeader, connection, infile: str) -> str` | Load the ODF object's cruise header and event header metadata into Oracle. |

#### `event_comments_to_oracle.py`

| Function | Description |
|---|---|
| `event_comments_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None` | Load the ODF object's event header comments into Oracle. |

#### `instrument_to_oracle.py`

| Function | Description |
|---|---|
| `instrument_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None` | Load the ODF object's instrument header metadata into Oracle. |

#### `history_to_oracle.py`

| Function | Description |
|---|---|
| `history_to_oracle(odfobj: OdfHeader, connection, infile: str)` | Load the ODF object's history header metadata into Oracle. |

#### `data_to_oracle.py`

| Function | Description |
|---|---|
| `data_to_oracle(odfobj: OdfHeader, connection, infile: str)` | Load the data records from an OdfHeader object into Oracle. |

#### `meteo_to_oracle.py`

| Function | Description |
|---|---|
| `meteo_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None` | Load the meteo header metadata from the ODF object into Oracle. |

#### `meteo_comments_to_oracle.py`

| Function | Description |
|---|---|
| `meteo_comments_to_oracle(odfobj: OdfHeader, connection, infile)` | Load the meteo header comments into Oracle. |

#### `quality_to_oracle.py`

| Function | Description |
|---|---|
| `quality_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None` | Load the ODF object's quality header information into Oracle. |

#### `quality_tests_to_oracle.py`

| Function | Description |
|---|---|
| `quality_tests_to_oracle(odfobj: OdfHeader, connection, infile: str)` | Load the ODF object's quality header tests into Oracle. |

#### `quality_comments_to_oracle.py`

| Function | Description |
|---|---|
| `quality_comments_to_oracle(odfobj: OdfHeader, connection, infile: str)` | Load the ODF object's quality header comments into Oracle. |

#### `compass_cal_to_oracle.py`

| Function | Description |
|---|---|
| `compass_cal_to_oracle(odfobj: OdfHeader, connection, infile: str) -> None` | Load the compass cal header metadata from the ODF object into Oracle. |

#### `polynomial_cal_to_oracle.py`

| Function | Description |
|---|---|
| `polynomial_cal_to_oracle(odfobj: OdfHeader, connection, infile: str)` | Load the polynomial cal header metadata from the ODF object into Oracle. |

#### `general_cal_to_oracle.py`

| Function | Description |
|---|---|
| `general_cal_to_oracle(odfobj: OdfHeader, connection, infile: str)` | Load the general cal header metadata from the ODF object into Oracle. |

#### `general_cal_equation_to_oracle.py`

| Function | Description |
|---|---|
| `general_cal_equation_to_oracle(general_cal_header: GeneralCalHeader, connection, gg: int, filename: str) -> None` | Load a GENERAL_CAL_Header equation into Oracle. |

#### `general_cal_comments_to_oracle.py`

| Function | Description |
|---|---|
| `general_cal_comments_to_oracle(general_cal_header: GeneralCalHeader, connection, gg: int, filename: str) -> None` | Load comments from a GENERAL_CAL_Header into Oracle. |

### Entry Scripts

#### `load_files_to_odf_archive_db.py`

_No public classes or functions (script / entry point)._

## `datashop_toolbox.gui`

### Package Setup

#### `__init__.py`

UI subpackage for datashop_toolbox.

Re-exports the package's public API:

`OdfMetadataDialog`, `OdfMetadataForm`, `Ui_main_window`, `Ui_odf_metadata_form`, `Ui_plot_dialog`, `Ui_thermograph_main_window`

### ODF Metadata Entry

#### `odf_metadata_dialog.py`

**class `OdfMetadataDialog(QDialog)`**

Modal dialog that wraps :class:`OdfMetadataForm` for editing ODF metadata.

| Method | Description |
|---|---|
| `__init__(parent = None)` | Build the dialog and wire up the embedded form's signals. |
| `_on_submitted(odf)` | Store the submitted ODF object and accept the dialog. |
| `odf()` | Return the ODF object captured on OK (or None if cancelled). |

#### `odf_metadata_form.py`

**class `OdfMetadataForm(QWidget)`**

Reusable content widget that hosts the controls from Ui_ODF_Metadata_Window.

| Method | Description |
|---|---|
| `__init__(parent = None, mission_templates_path: Path \| None = None)` | Build the form, load mission templates, and wire up its widgets. |
| `_setup_validators()` | Set placeholder text and numeric validators on the input fields. |
| `_populate_mission_templates()` | Load top-level keys from mission_header_templates.json into the combo. |
| `_populate_year()` | Populate the year field with the current year. |
| `_show_warning_dialog()` | Show (after the current event loop tick) a warning about the auto-filled year. |
| `showEvent(event) -> None` | Overrides the show event to run code after the dialog is visible. |
| `_on_dialog_visible()` | Function that runs when the dialog appears. |
| `_connect_signals()` | Wire the template selector and OK/Cancel buttons to their handlers. |
| `_clear_cruise_header_fields()` | Clear all CRUISE_HEADER input fields. |
| `_clear_event_header_fields()` | Clear all EVENT_HEADER input fields. |
| `_on_template_changed(name: str) -> None` | Load CRUISE_HEADER + default EVENT_HEADER from selected template. |
| `_parse_datetime(widget, label: str)` | Parse a date/time from a Q_line_edit using check_datetime. |
| `_parse_float(widget, label: str)` | Parse a float from a Q_line_edit. Uses Python float() for semantic validation. |
| `collect_metadata() -> OdfHeader` | Create and fill an OdfHeader from current UI values. |
| `export_to_odf() -> None` | Example action: build and print the header (replace with real writer). |
| `_on_ok_clicked()` | Collect and validate form input, then emit :attr:`submitted` or show an error. |
| `_on_cancel_clicked()` | Emit :attr:`cancelled`. |

### RBR / RSK Processing

#### `rbr_to_odf_mainwindow.py`

**class `BtlHeader`**

Bottle header information to export BTL file.

**class `MainWindow(QMainWindow)`**

Main window for converting RBR ``.rsk`` CTD files to ODF and BTL files.

| Method | Description |
|---|---|
| `__init__(parent = None)` | Build the window, restore saved state, and connect signals. |
| `_setup_validators()` | Set placeholder text and numeric validators on the lat/lon fields. |
| `_connect_signals()` | Wire the window's buttons and list widget to their handlers. |
| *(property)* `rsk_file_path() -> str` | str: Full path to the currently selected ``.rsk`` file, or ``""``. |
| `_on_rsk_selected(current, previous)` | Update the channel list when the selected RSK file changes. |
| `_save_settings()` | Persist the folder, lat/lon, selections, and window geometry to disk. |
| `_load_settings()` | Restore the folder, lat/lon, selections, and window geometry from disk. |
| `close_event(event)` | Persist settings before closing. |
| `_choose_rsk_folder()` | Prompt for the RSK folder and populate the RSK file list. |
| `_update_channel_list()` | Read the selected RSK file's channels and restore prior selections. |
| `_profile_plots()` | Build and show a profile-plot dialog for the selected RSK file. |
| `_clear_settings()` | Clear the folder, RSK/channel lists, and lat/lon fields. |
| `_edit_metadata()` | Open the ODF metadata dialog and store the resulting ODF object. |
| *(static)* `_split_string_get_end_number(s)` | Split a string into its non-numeric prefix and trailing digits. |
| `_populate_parameter_headers(df: pd.DataFrame) -> dict` | Populate the parameter headers and the data object. |
| `_choose_export_odf_folder() -> str` | Prompt for the ODF export folder. |
| *(static)* `round_to_nearest_half(number)` | Round a number to the nearest half (e.g. ``1.3`` -> ``1.5``). |
| `_export_odf()` | Process the selected RSK file and write down-cast/up-cast ODF files. |
| `_format_positional_value(position: float, position_type: str) -> str` | Format a decimal-degree position as a degrees/minutes BTL string. |
| `_export_btl()` | Export a fixed-width BTL (bottle) file for the selected RSK cast. |

#### `rbr_profile_plot.py`

**class `PlotDialog(QDialog)`**

Dialog that displays RSK profile figures one at a time with Next/Prev navigation

| Method | Description |
|---|---|
| `__init__(fig_handles: list \| None = None, parent = None, title: str = 'RSK Profiles')` | Build the dialog and display the first profile, if any. |
| `_add_navigation_actions()` | Add only Prev/Next actions (no jump, no up/down arrows). |
| `_update_nav_enabled()` | Enable/disable the prev/next actions based on the current index. |
| `_clear_plot_area()` | Remove and delete the current toolbar/canvas widgets from the layout. |
| `display_current_profile()` | Display the current profile figure in the dialog. |
| `_connect_key_navigation(figure)` | Wire left/right arrow key presses on a figure to prev/next navigation. |
| `on_prev_profile()` | Display the previous profile, if not already at the first. |
| `on_next_profile()` | Display the next profile, if not already at the last. |
| `on_save_checkbox_changed(state)` | Add or remove the current profile from :attr:`saved_profiles`. |
| `on_accept()` | Accept the dialog. |
| `on_reject()` | Reject the dialog. |
| `get_saved_profiles()` | Return the indices of profiles the user marked as saved. |

| Function | Description |
|---|---|
| `_create_sample_profiles(num_profiles = 5)` |  |

### Thermograph Processing

#### `thermograph_gui_loader.py`

**class `ThermographMainWindow(QMainWindow)`**

Main window for collecting thermograph processing inputs.

| Method | Description |
|---|---|
| `__init__()` | Build the window from the generated UI and connect its signals. |
| `on_name_entered()` | Store and log the processor name once editing of the field ends. |
| `on_institution_changed(text: str)` | Store the newly selected institution. |
| `on_instrument_changed(text: str)` | Store the newly selected instrument. |
| `choose_metadata_file()` | Prompt for and store the metadata file. |
| `choose_data_folder()` | Prompt for and store the data folder. |
| `accept_clicked()` | Set :attr:`result` to ``"accept"`` and close the window. |
| `reject_clicked()` | Set :attr:`result` to ``"reject"`` and close the window. |

### Examples

#### `example_btl_generation.py`

**class `columns(Enum)`**

Bottle data to export BTL file (header labels / order).

| Function | Description |
|---|---|
| `_fmt_value(val: Any) -> str` | Format values similarly to the example: integers as-is, floats right-aligned, |
| `_pad_left(text: str, width: int) -> str` | Left-align text within a fixed-width field. |
| `_pad_right(text: str, width: int) -> str` | Right-align text within a fixed-width field. |
| `print_btl_table(rows: Iterable[Mapping[str, Any]], param_enum: Iterable[columns] = (columns.oxygen, columns.salinity, columns.potential_temperature, columns.sigma_theta, columns.scan, columns.pressure, columns.conductivity, columns.par, columns.turbidity, columns.fluorescence, columns.cdom), widths: Mapping[str, int] = print_widths) -> None` | Print a BTL-style table with: |

