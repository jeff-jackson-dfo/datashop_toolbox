# How to create a new ODF file from scratch

This guide shows how to build an ODF (Ocean Data Format) file in Python with `datashop_toolbox`, starting from an empty `OdfHeader` object and ending with a file on disk.

It follows the creation branch of `main()` in `odfhdr.py` (the branch that runs when `test_creation = True`). That branch builds an ODF in memory and prints it. The guide adds the final write-to-disk step, which `main()` only demonstrates in its other branch (the one that reads an existing file).

## Before you start

- `datashop_toolbox` is installed in your Python environment.
- You know the values you want to record: cruise, event, instrument, and at least one parameter with data.
- You know which output version you need. `2.0` writes the comma-delimited format; `3.0` and later write the non-comma-delimited format.

## Steps

### 1. Create the ODF object and reset the log

```python
from datashop_toolbox.odfhdr import OdfHeader

odf = OdfHeader()
odf.reset_log_list()
```

`OdfHeader()` creates the object with empty Cruise, Event, Instrument, and Record headers. `meteo_header` and `quality_header` start as `None`. `reset_log_list()` clears the log shared by all headers so that only messages from this session are kept.

### 2. Log who is making the file

```python
odf.log_odf_message("Jane Doe made the following modifications to this file:", "base")
```

Passing `"base"` writes the message to the shared log, which `print_object()` later adds to the History header.

### 3. Fill in the Cruise header

Attach the shared logger and config to the header first, then set its fields.

```python
odf.cruise_header.set_logger_and_config(odf.logger, odf.config)
odf.cruise_header.cruise_number = "HUD2022001"
odf.cruise_header.organization = "DFO BIO"
odf.cruise_header.chief_scientist = "GLEN HARRISON"
odf.cruise_header.start_date = "01-APR-2022 00:00:00.00"
odf.cruise_header.end_date = "31-OCT-2022 00:00:00.00"
odf.cruise_header.platform = "LATALANTE"
```

Dates use the ODF format `DD-MON-YYYY HH:MM:SS.ss`.

To record the change in the log, call the header's log method before assigning. This is the pattern `main()` uses:

```python
org = odf.cruise_header.organization
odf.cruise_header.log_cruise_message("ORGANIZATION", org, "DFO BIO")
odf.cruise_header.organization = "DFO BIO"
```

### 4. Fill in the Event header

```python
odf.event_header.set_logger_and_config(odf.logger, odf.config)
odf.event_header.data_type = "CTD"
odf.event_header.event_number = "001"
odf.event_header.event_qualifier1 = "1"
odf.event_header.event_qualifier2 = "DN"
odf.event_header.station_name = "AR7W_15"
```

`data_type`, `event_number`, and the two event qualifiers, together with the cruise number, are what `generate_file_spec()` uses to build the file name in step 10. If you leave them empty, the file name will be mostly underscores.

### 5. Fill in the Instrument header

```python
odf.instrument_header.set_logger_and_config(odf.logger, odf.config)
odf.instrument_header.description = "RBR Concerto CTD"
```

### 6. (Optional) Add a Meteo header

The Meteo header is optional. Create it and attach the logger and config before setting values.

```python
from datashop_toolbox.meteohdr import MeteoHeader

odf.meteo_header = MeteoHeader()
odf.meteo_header.set_logger_and_config(odf.logger, odf.config)
odf.meteo_header.air_temperature = 10.0
odf.meteo_header.atmospheric_pressure = 1063.1
odf.meteo_header.wind_speed = MeteoHeader.wind_speed_knots_to_ms(50.0)
odf.meteo_header.wind_direction = 180.0
odf.meteo_header.sea_state = MeteoHeader.wave_height_meters_to_wmo_code(3.0)
odf.meteo_header.cloud_cover = MeteoHeader.cloud_cover_percentage_to_wmo_code(0.5)
odf.meteo_header.ice_thickness = 0.5
odf.meteo_header.set_meteo_comment("A comment about the conditions")
```

The static helpers convert knots to m/s, wave height in metres to a WMO sea-state code, and cloud cover to a WMO code.

### 6b. (Optional) Add a Quality header

```python
from datashop_toolbox.qualityhdr import QualityHeader

odf.quality_header = QualityHeader()
odf.quality_header.set_logger_and_config(odf.logger, odf.config)
odf.quality_header.quality_date = "01-JUL-2017 10:45:19.00"
odf.quality_header.set_quality_test("Test 1")
odf.quality_header.quality_comments = ["Comment 1"]
```

### 7. (Optional) Add calibration and history headers

Each of these is a list on the ODF object. Build the header, attach the logger and config, and append it.

**Polynomial calibration**

```python
from datashop_toolbox.polynomialhdr import PolynomialCalHeader

poly = PolynomialCalHeader()
poly.set_logger_and_config(odf.logger, odf.config)
poly.parameter_code = "PRES_01"
poly.calibration_date = "11-JUN-1995 05:35:46.82"
poly.application_date = "11-JUN-1995 05:35:46.82"
poly.number_coefficients = 2
poly.coefficients = [0.6, 0.15]
odf.polynomial_cal_headers.append(poly)
```

**General calibration** (`GeneralCalHeader`, appended to `odf.general_cal_headers`) uses `parameter_code`, `calibration_type`, `calibration_date`, `application_date`, `number_coefficients`, `coefficients`, and `calibration_equation`.

**Compass calibration** (`CompassCalHeader`, appended to `odf.compass_cal_headers`) is populated from a list of `KEY = value` strings with `populate_object()`.

**History** (`HistoryHeader`, appended to `odf.history_headers`) can be populated the same way, from `CREATION_DATE` and `PROCESS` lines.

### 8. Define each parameter

Create one `ParameterHeader` for every data column.

```python
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.parameterhdr import ParameterHeader

param = ParameterHeader(
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
    depth=0.0,
    minimum_value=1.0,
    maximum_value=7.0,
    number_valid=3,
    number_null=0,
)
param.set_logger_and_config(odf.logger, odf.config)
odf.parameter_headers.append(param)
```

The `code` must match the column name in your data frame (step 9). Codes follow the pattern four capital letters, an underscore, and two digits, such as `PRES_01`.

### 9. Attach the data

Put the data in a pandas DataFrame, wrap it in a `DataRecords` object, and assign it to `odf.data`.

```python
import pandas as pd
from datashop_toolbox.records import DataRecords

records = DataRecords()
records.set_logger_and_config(odf.logger, odf.config)
records.data_frame = pd.DataFrame(
    {
        "PRES_01": [1.0, 4.0, 7.0],
        "TEMP_01": [8.2, 5.6, 2.45],
        "PSAL_01": [31.5, 32.0, 32.88],
    }
)
records.parameter_list = ["PRES_01", "TEMP_01", "PSAL_01"]
records.print_formats = {"PRES_01": "10.1", "TEMP_01": "10.4", "PSAL_01": "10.4"}
odf.data = records
```

If you have three data columns, you need three `ParameterHeader` objects from step 8 (one each for `PRES_01`, `TEMP_01`, and `PSAL_01`).

### 10. Update derived values, set the file name, and write

```python
from pathlib import Path

odf.update_odf()

odf.file_specification = odf.generate_file_spec()
out_path = Path("output") / f"{odf.file_specification}.ODF"
odf.write_odf(out_path, version=2.0)
```

`update_odf()` fills in values that are derived from what you added:

- the Record header counts (calibrations, history, swing, parameters, cycles);
- the Event header minimum and maximum depth, taken from `DEPH_01` or, if that is absent, `PRES_01`, when they have not been set;
- `depth_off_bottom`, when `sounding` is set;
- the minimum and maximum value in each Parameter header.

`generate_file_spec()` builds the name as `DATATYPE_CRUISENUMBER_EVENTNUMBER_QUALIFIER1_QUALIFIER2`, for example `CTD_HUD2022001_001_1_DN`. `write_odf()` creates the file in ISO-8859-1 encoding and prints the path. The output directory must already exist, and `version` must be a float (`2.0`, not `2`).

### 11. Check the result

To preview the file without writing it, print the serialized text:

```python
print(odf.print_object())
```

To review what was logged during the session:

```python
for entry in odf.shared_log_list:
    print(entry)
```

## Complete example

This is a minimal end-to-end script: one parameter, no optional headers.

```python
from pathlib import Path

import pandas as pd

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.parameterhdr import ParameterHeader
from datashop_toolbox.records import DataRecords

odf = OdfHeader()
odf.reset_log_list()
odf.log_odf_message("Jane Doe made the following modifications to this file:", "base")

odf.cruise_header.set_logger_and_config(odf.logger, odf.config)
odf.cruise_header.cruise_number = "HUD2022001"
odf.cruise_header.organization = "DFO BIO"
odf.cruise_header.chief_scientist = "GLEN HARRISON"
odf.cruise_header.start_date = "01-APR-2022 00:00:00.00"
odf.cruise_header.end_date = "31-OCT-2022 00:00:00.00"
odf.cruise_header.platform = "LATALANTE"

odf.event_header.set_logger_and_config(odf.logger, odf.config)
odf.event_header.data_type = "CTD"
odf.event_header.event_number = "001"
odf.event_header.event_qualifier1 = "1"
odf.event_header.event_qualifier2 = "DN"
odf.event_header.station_name = "AR7W_15"

odf.instrument_header.set_logger_and_config(odf.logger, odf.config)
odf.instrument_header.description = "RBR Concerto CTD"

param = ParameterHeader(
    type="DOUB", name="Pressure", units="decibars", code="PRES_01", wmo_code="PRES",
    null_string=f"{BaseHeader.NULL_VALUE}", print_field_width=10, print_decimal_places=3,
    angle_of_section=0.0, magnetic_variation=0.0, depth=0.0,
    minimum_value=1.0, maximum_value=7.0, number_valid=3, number_null=0,
)
param.set_logger_and_config(odf.logger, odf.config)
odf.parameter_headers.append(param)

records = DataRecords()
records.set_logger_and_config(odf.logger, odf.config)
records.data_frame = pd.DataFrame({"PRES_01": [1.0, 4.0, 7.0]})
records.parameter_list = ["PRES_01"]
records.print_formats = {"PRES_01": "10.1"}
odf.data = records

odf.update_odf()
odf.file_specification = odf.generate_file_spec()

out_dir = Path("output")
out_dir.mkdir(exist_ok=True)
odf.write_odf(out_dir / f"{odf.file_specification}.ODF", version=2.0)
```

## Troubleshooting

**`KeyError` from `update_odf()`.** Every `ParameterHeader.code` must be a column in `odf.data.data_frame`. Check the spelling, or add the missing header or column.

**`file_specification cannot be empty`.** Assign `odf.file_specification` before writing, as in step 10, and make sure the event and cruise fields it is built from are set.

**`AssertionError` in `write_odf()`.** The first argument must be a `Path`, not a string, and `version` must be a float.

**The file name is mostly underscores.** `data_type`, `cruise_number`, `event_number`, and the qualifiers were left empty (steps 3 and 4).

## See also

- `docs/ODF_File_Specification.md` for the header blocks and field definitions.
- `OdfHeader.read_odf()` to start from an existing ODF file instead of an empty object.
- `OdfHeader.add_quality_flags()` and `write_odf(..., version=3.0)` for writing quality-flagged files, as shown in the read-and-modify branch of `main()`.
