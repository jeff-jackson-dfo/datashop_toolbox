# How to edit a set of ODF files

This guide shows how to apply the same metadata corrections to every ODF file in a folder and write the revised files to a new folder, leaving the originals untouched. The worked example is the script used to update the CTD files from cruise JC291 (`update_JC291.py`): it corrects the Cruise header, pads the event numbers, repairs a default start date, and records calibration changes in the History header.

## What you will get

A folder of revised ODF files in which:

- the header fields you changed carry their new values;
- a new History header lists who made the changes and exactly what changed (old value and new value);
- the Record header counts and the parameter minimum and maximum values are refreshed;
- each file is named from its own header values (`generate_file_spec()`), so a corrected event number is reflected in the file name.

## Before you start

You need:

- `datashop_toolbox` installed in the active environment;
- a folder containing the ODF files to edit (here called the *original* folder);
- an empty or new folder for the revised files (the *revised* folder);
- the list of corrections you intend to make, with their old and new values.

## Steps

### 1. Set the folders and your name

```python
from pathlib import Path

top_path = Path("C:/DFO-MPO/DEV/AtSea/JC291/CTD/DATASHOP_PROCESSING")
path_to_orig = top_path / "Step_2_Apply_Calibrations/ODF"
path_to_revised = top_path / "Step_3_Update_Metadata"
path_to_revised.mkdir(parents=True, exist_ok=True)

user = "Jeff Jackson"
```

`user` is written into the History header as the person responsible for the changes.

### 2. Loop over the files

```python
for file_path in sorted(path_to_orig.glob("*.ODF")):
    print(f"Processing {file_path.name}")
    ...
```

Everything in steps 3 to 9 goes inside this loop. `glob("*.ODF")` selects both the downcast (`DN`) and upcast (`UP`) files. To edit only one kind, narrow the pattern, for example `glob("*_DN.ODF")`.

### 3. Read the file and reset the log

```python
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.odfhdr import OdfHeader

odf = OdfHeader()
BaseHeader.reset_log_list()
odf.read_odf(file_path)
```

Create a new `OdfHeader` for every file and reset the shared log, so that messages logged for one file are not written into the next. `read_odf()` needs a `Path` object, not a string.

### 4. Add a new History header

```python
odf.add_history()
odf.log_odf_message(f"{user} made the following modifications to this file:", "base")
```

`add_history()` appends a new History header stamped with the current date. The message becomes its first line. Every change you log in the following steps is added to this header when the file is written.

### 5. Change header fields and log each change

Log the change first, then assign the new value, so that the log records the old value:

```python
odf.cruise_header.log_cruise_message("organization", odf.cruise_header.organization, "DFO BIO")
odf.cruise_header.organization = "DFO BIO"

odf.cruise_header.log_cruise_message("platform", odf.cruise_header.platform, "JAMES COOK")
odf.cruise_header.platform = "JAMES COOK"

odf.cruise_header.log_cruise_message("start_date", odf.cruise_header.start_date, "21-MAY-2026 16:00:00.00")
odf.cruise_header.start_date = "21-MAY-2026 16:00:00.00"

odf.cruise_header.log_cruise_message("end_date", odf.cruise_header.end_date, "07-JUN-2026 17:00:00.00")
odf.cruise_header.end_date = "07-JUN-2026 17:00:00.00"
```

The Event, Instrument, and other headers have matching methods, for example `log_event_message()` and `log_instrument_message()`. Dates use the ODF format `DD-MON-YYYY HH:MM:SS.ss`.

### 6. Make the event number a three-digit string

```python
event_str = odf.event_header.event_number
if len(event_str) < 3:
    revised_event_number = f"{int(event_str):03}"
    odf.event_header.event_number = revised_event_number
    odf.event_header.log_event_message("event_number", event_str, revised_event_number)
```

The event number is part of the file name, so padding it changes the name of the revised file (for example `..._1_...` becomes `..._001_...`).

### 7. Repair a default start date (only if your files need it)

Some files have `01-JAN-2000` as the date in both the Event header start time and the `SYTM_01` time column, because the instrument clock was not set. In the JC291 files the correct date was recovered from the NMEA UTC time recorded in the first History header, for example `* NMEA UTC (Time) = May 03 2025 07:09:00`.

```python
from datetime import UTC, datetime

import pandas as pd

sdt = odf.event_header.start_date_time
if sdt[0:11] == "01-JAN-2000":
    # Find the NMEA time in the first History header.
    hh = odf.history_headers[0]
    idx = hh.find_process("NMEA UTC (Time)")
    if len(idx) == 1:
        pline = hh.processes[idx[0]]
        nmea_sdt = pline.split("=")[1].strip(" ")
        nsdt = datetime.strptime(nmea_sdt, "%B %d %Y %H:%M:%S").replace(tzinfo=UTC)
        new_sdt = datetime.strftime(nsdt, BaseHeader.SYTM_FORMAT)
        new_sdt = new_sdt[:-4]
        odf.event_header.start_date_time = new_sdt.upper()
        odf.event_header.log_event_message("start_date_time", sdt, new_sdt)

    # Replace the dates in the SYTM_01 column; the times are kept.
    data = odf.data.data_frame
    sytms = data["SYTM_01"].str.replace("'", "")
    datetimes = pd.to_datetime(sytms, utc=True, format="%d-%b-%Y %H:%M:%S.%f", errors="coerce")
    dates = pd.to_datetime(datetimes.dt.date)
    times = datetimes.dt.time
    df = pd.DataFrame({"date": dates, "time": times})
    day_changes = dates - dates[0]
    new_dates = pd.to_datetime([new_sdt[:11]] * len(day_changes))
    df["date"] = [new_dates[i] + day_change for i, day_change in enumerate(day_changes)]
    df["new_sytms"] = df.apply(lambda row: datetime.combine(row["date"], row["time"]), axis=1)
    new_sytms = [dt.strftime("%d-%b-%Y %H:%M:%S.%f") for dt in df["new_sytms"]]

    # Update the minimum and maximum in the SYTM_01 parameter header.
    x = odf.get_parameter_codes().index("SYTM_01")
    odf.parameter_headers[x].minimum_value = new_sytms[0]
    odf.parameter_headers[x].maximum_value = new_sytms[-1]

    # Put the corrected, quoted values back into the data frame.
    new_sytms = [s.upper()[:-4] for s in new_sytms]
    data["SYTM_01"] = pd.Series(new_sytms).apply(lambda v: f"'{v}'")
    odf.data.data_frame = data
```

The day offsets are preserved, so a cast that runs past midnight keeps its second day. Skip this step if your files do not have the default date.

### 8. Record changes made outside the files

If you changed calibration coefficients before reprocessing the data, document them in the History header with `add_to_log()`:

```python
odf.add_to_log(
    'The primary conductivity [3567] calibration coefficient "Offset" was changed '
    "from its original value [0.0] to [-0.0003624]."
)
odf.add_to_log(
    'The primary conductivity [3567] calibration coefficient "Slope" was changed '
    "from its original value [1.0] to [0.9999723]."
)
```

The JC291 script adds one line for each coefficient that changed: Offset and Slope for the primary and secondary conductivity sensors, and Soc for the primary and secondary oxygen sensors. Include the sensor serial number in square brackets, and both the old and new value.

### 9. Refresh the derived values and write the file

```python
odf.update_odf()

out_file = odf.generate_file_spec() + ".ODF"
odf.write_odf(path_to_revised / out_file, version=2.0)
```

`update_odf()` recalculates the Record header counts, fills in the event depth range if it is missing, and refreshes the minimum and maximum of every parameter. `write_odf()` adds the logged messages to the new History header, then writes the file in ISO-8859-1 encoding. `version` must be a float: `2.0` writes the comma-delimited format and `3.0` the non-comma-delimited format.

### 10. Check the results

- Compare the number of files in the revised folder with the number in the original folder.
- Open one revised file in a text editor. The last `HISTORY_HEADER` should name you, and list every change you logged, each with its old and new value.
- Check the corrected fields, for example `PLATFORM`, `START_DATE` and `EVENT_NUMBER`, and that the file name matches the header values.

## Complete script

```python
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.odfhdr import OdfHeader

top_path = Path("C:/DFO-MPO/DEV/AtSea/JC291/CTD/DATASHOP_PROCESSING")
path_to_orig = top_path / "Step_2_Apply_Calibrations/ODF"
path_to_revised = top_path / "Step_3_Update_Metadata"
path_to_revised.mkdir(parents=True, exist_ok=True)

user = "Jeff Jackson"

for file_path in sorted(path_to_orig.glob("*.ODF")):

    print()
    print("#" * 71)
    print("Processing " + file_path.name)
    print("#" * 71)
    print()

    odf = OdfHeader()
    BaseHeader.reset_log_list()
    odf.read_odf(file_path)

    # Add a new History Header to record the modifications that are made.
    odf.add_history()
    odf.log_odf_message(f"{user} made the following modifications to this file:", "base")

    # Update the Cruise Header.
    odf.cruise_header.log_cruise_message("organization", odf.cruise_header.organization, "DFO BIO")
    odf.cruise_header.organization = "DFO BIO"
    odf.cruise_header.log_cruise_message("platform", odf.cruise_header.platform, "JAMES COOK")
    odf.cruise_header.platform = "JAMES COOK"
    odf.cruise_header.log_cruise_message("start_date", odf.cruise_header.start_date, "21-MAY-2026 16:00:00.00")
    odf.cruise_header.start_date = "21-MAY-2026 16:00:00.00"
    odf.cruise_header.log_cruise_message("end_date", odf.cruise_header.end_date, "07-JUN-2026 17:00:00.00")
    odf.cruise_header.end_date = "07-JUN-2026 17:00:00.00"

    # Make sure that the event numbers are 3-digit strings.
    event_str = odf.event_header.event_number
    if len(event_str) < 3:
        revised_event_number = f"{int(event_str):03}"
        odf.event_header.event_number = revised_event_number
        odf.event_header.log_event_message("event_number", event_str, revised_event_number)

    # Replace a default 01-JAN-2000 start date using the NMEA UTC time in the first History header.
    sdt = odf.event_header.start_date_time
    if sdt[0:11] == "01-JAN-2000":
        hh = odf.history_headers[0]
        idx = hh.find_process("NMEA UTC (Time)")
        if len(idx) == 1:
            pline = hh.processes[idx[0]]
            nmea_sdt = pline.split("=")[1].strip(" ")
            nsdt = datetime.strptime(nmea_sdt, "%B %d %Y %H:%M:%S").replace(tzinfo=UTC)
            new_sdt = datetime.strftime(nsdt, BaseHeader.SYTM_FORMAT)
            new_sdt = new_sdt[:-4]
            odf.event_header.start_date_time = new_sdt.upper()
            odf.event_header.log_event_message("start_date_time", sdt, new_sdt)

        # Correct the dates in the SYTM_01 column, which also have 01-JAN-2000.
        data = odf.data.data_frame
        sytms = data["SYTM_01"].str.replace("'", "")
        datetimes = pd.to_datetime(sytms, utc=True, format="%d-%b-%Y %H:%M:%S.%f", errors="coerce")
        dates = pd.to_datetime(datetimes.dt.date)
        times = datetimes.dt.time
        df = pd.DataFrame({"date": dates, "time": times})
        day_changes = dates - dates[0]
        new_dates = pd.to_datetime([new_sdt[:11]] * len(day_changes))
        df["date"] = [new_dates[i] + day_change for i, day_change in enumerate(day_changes)]
        df["new_sytms"] = df.apply(lambda row: datetime.combine(row["date"], row["time"]), axis=1)
        new_sytms = [dt.strftime("%d-%b-%Y %H:%M:%S.%f") for dt in df["new_sytms"]]

        x = odf.get_parameter_codes().index("SYTM_01")
        odf.parameter_headers[x].minimum_value = new_sytms[0]
        odf.parameter_headers[x].maximum_value = new_sytms[-1]

        new_sytms = [s.upper()[:-4] for s in new_sytms]
        data["SYTM_01"] = pd.Series(new_sytms).apply(lambda v: f"'{v}'")
        odf.data.data_frame = data

    # Document the conductivity calibration changes made before reprocessing.
    odf.add_to_log(
        'The primary conductivity [3567] calibration coefficient "Offset" was changed from its original '
        "value [0.0] to [-0.0003624]."
    )
    odf.add_to_log(
        'The primary conductivity [3567] calibration coefficient "Slope" was changed from its original '
        "value [1.0] to [0.9999723]."
    )
    odf.add_to_log(
        'The secondary conductivity [3054] calibration coefficient "Offset" was changed from its original '
        "value [0.0] to [0.0006250]."
    )
    odf.add_to_log(
        'The secondary conductivity [3054] calibration coefficient "Slope" was changed from its original '
        "value [1.0] to [0.9996911]."
    )

    # Document the oxygen calibration changes made before reprocessing.
    odf.add_to_log(
        'The primary oxygen [4570] calibration coefficient "Soc" was changed from its original value '
        "of [0.47197] to [0.5115]."
    )
    odf.add_to_log(
        'The secondary oxygen [4571] calibration coefficient "Soc" was changed from its original value '
        "of [0.4771] to [0.4900]."
    )

    # Refresh the derived metadata, then write the revised file.
    odf.update_odf()
    out_file = odf.generate_file_spec() + ".ODF"
    odf.write_odf(path_to_revised / out_file, version=2.0)
```

## Common variations

**Change an Event comment or an Instrument field.** Use the same log-then-assign pattern:

```python
odf.event_header.set_event_comment("We had a successful trip!", 1)

desc = odf.instrument_header.description
odf.instrument_header.log_instrument_message("DESCRIPTION", desc, "RBR Concerto CTD")
odf.instrument_header.description = "RBR Concerto CTD"
```

**Add a free-text note to the History header.**

```python
odf.add_to_history("Station names were checked against the cruise log.")
```

**Write ODF version 3.0 instead of 2.0.** Change `version=2.0` to `version=3.0` in the `write_odf()` call.

## Troubleshooting

**`AssertionError` from `read_odf()` or `write_odf()`.** Both need a `Path` object, and `write_odf()` also needs `version` as a float (`2.0`, not `2`).

**`NameError: name 'new_sdt' is not defined`.** The start date is `01-JAN-2000`, but the first History header does not contain exactly one line with `NMEA UTC (Time)`, so `new_sdt` was never set and the SYTM correction cannot run. Check the History header of that file. If the line is missing, the correct date must come from another source.

**`KeyError: 'SYTM_01'`.** The file has no `SYTM_01` column, so step 7 does not apply to it. Remove that step, or guard it with `if "SYTM_01" in odf.data.data_frame.columns`.

**`ValueError` from `strptime`.** The NMEA line is not in the form `Month DD YYYY HH:MM:SS` (for example `May 03 2025 07:09:00`). Adjust the format string to match.

**Files are overwritten or missing.** The output name comes from the header values, not the input name. If the event number, qualifiers, cruise number or data type change, the file gets a different name, and two inputs that end up with the same header values write to the same file.

## See also

- [Create a new ODF file from scratch](how-to-create-an-odf-file.md)
- See [ODF_File_Specification.md](ODF_File_Specification.md) for the header blocks and field definitions.
