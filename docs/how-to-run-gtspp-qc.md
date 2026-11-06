# How-To: Run the GTSPP Quality Control on a Folder of ODF Files

> **Status:** Draft.
> **Diátaxis quadrant:** [How-to guide](https://diataxis.fr/how-to-guides/) — this document is
> goal-oriented and assumes you already know what the GTSPP tests are. It lists the steps to get
> a folder of ODF files quality controlled, and the common variations. For the interface of the
> modules, see the [reference](gtspp_reference.md).

## What you will get

Quality-controlled copies of your ODF files in a new folder. In each copy:

- the per-value flags are in the `Q<code>` columns (for example `QTEMP_01`);
- a `QCFF_01` column shows, for every data row, which Stage 2 tests flagged it;
- the `QUALITY_HEADER` lists the Stage 1 and Stage 2 tests that were run and the result of each;
- your original files are not touched.

## Before you start

You need:

- `datashop_toolbox` installed in the active environment (Python 3.13 or later);
- the three scripts `gtspp_stage1.py`, `gtspp_stage2.py` and `gtspp_odf_output.py`, kept
  **together in one folder** — either `src/datashop_toolbox/` or any other folder;
- the **original** ODF files, in one folder;
- to be in the repository root when you run the scripts, so the platform lookup table is found (or use `--platforms`).

> Run the QC on original files. Running it again on already quality-controlled files is not
> supported: the existing flags are kept and values already flagged doubtful are not re-tested,
> so the results differ from a first run. The script logs a warning if it sees this.

## 1. Install the extra packages

The toolbox installs none of these.

=== "Windows"

    ```powershell
    (venv) PS C:\Dev\GitHub\datashop_toolbox> uv pip install gsw xarray netCDF4
    ```

=== "Linux / macOS"

    ```bash
    (venv) $ uv pip install gsw xarray netCDF4
    ```

- `gsw` is needed for test 2.10 (Density Inversion) and for converting pressure to depth. Without
  it, test 2.10 is skipped and left out of the quality header.
- `xarray` and a netCDF engine for it (`netCDF4` here, or `h5netcdf`) are only needed if you use a bathymetry file
  (step 3).

## 2. Check the platform table

Two tests use the toolbox lookup table `src/datashop_toolbox/lookups/platforms.csv`, which has the columns
`platform_name`, `call_sign` and `max_velocity`. The path is relative to the current folder, so **run the scripts from
the repository root**.

- **Test 1.1 (Platform Identification)** checks each platform against `platform_name`. Case and repeated spaces are
  ignored.
- **Test 1.5 (Impossible Speed)** uses `max_velocity`, in knots, as the speed limit of each platform. If a name
  appears twice (vessels with the same name and different call signs), the larger limit is used.

Check that every platform in your ODF files (`PLATFORM` in the `CRUISE_HEADER`) is in the table.

To use a different platform list for one run, pass `--platforms FILE`, a text file with one platform name per line. It
replaces the names used by test 1.1 only; the speed limits still come from the table.

```text
HUDSON
```

If the table cannot be found, the scripts log a warning (`Known platforms not loaded`) and start with empty lists. Test
1.1 then flags any platform that appears in only one file as doubtful (3), and test 1.5 runs only if you give
`--max-speed-knots`.

## 3. Run the QC

=== "Windows"

    ```powershell
    (venv) PS C:\Dev\GitHub\datashop_toolbox> python src\datashop_toolbox\gtspp_odf_output.py `
        C:\Data\HUD2008004\ODF `
        --out-dir C:\Data\HUD2008004\QC
    ```

=== "Linux / macOS"

    ```bash
    (venv) $ python src/datashop_toolbox/gtspp_odf_output.py \
        /data/HUD2008004/ODF \
        --out-dir /data/HUD2008004/QC
    ```

If the scripts are inside the `datashop_toolbox` package you can also run
`python -m datashop_toolbox.gtspp_odf_output` with the same arguments.

| Argument | Meaning |
|---|---|
| `FOLDER` | Folder with the original ODF files. |
| `--out-dir DIR` | **Required.** Folder for the QC'd files, which keep their original names. The script refuses to write into the folder the file came from. |
| `--platforms FILE` | Known platforms, one per line. Default: the lookup table `lookups/platforms.csv` (step 2). |
| `--max-speed-knots N` | Speed limit, in knots, for platforms that are **not** in the lookup table. Platforms in the table always use their own limit (step 2). |
| `--bathy FILE` | GEBCO or ETOPO netCDF grid. Turns on tests 1.4, 1.6 and 2.11. |
| `--pattern GLOB` | Which files to read. Default `*.ODF`. |
| `--no-history` | Do not add a `HISTORY_HEADER` entry. |

Tests that need an input you did not give are not run, and are not listed in the quality header:

| If you omit | These tests are not run |
|---|---|
| `--max-speed-knots` | Nothing is lost: test 1.5 still runs for every platform in the lookup table. Platforms that are not in it are not speed-tested. |
| `--bathy` | 1.4 Position on Land, 1.6 Impossible Sounding, 2.11 Bottom |
| (no command-line option) | 2.12 Temperature Inversion — see [below](#turn-on-the-temperature-inversion-test) |

## 4. Read the console summary

For each test, the summary shows how many stations or profiles failed out of how many were run,
and names the failures:

```text
Stage 1 (location and identification), 10 stations:
  Test 1.1 Platform Identification: 0 failed of 10 run
  Test 1.2 Impossible Date/Time: 0 failed of 10 run
  Test 1.3 Impossible Location: 0 failed of 10 run
  Test 1.5 Impossible Speed: 0 failed of 10 run

Stage 2 (profile), 10 profiles:
  Test 2.1 Global Impossible Parameter Values: 0 failed of 10 run
  ...
  Test 2.7 Spike: 1 failed of 10 run  -> CTD_HUD2008004_001
  ...
  Test 2.10 Density Inversion: 2 failed of 10 run  -> CTD_HUD2008004_001, CTD_HUD2008004_034
10 ODF files written to C:\Data\HUD2008004\QC
```

When fewer stations or profiles had data to examine than were run, the line adds `(N had data)`: for example,
`Test 1.4 Position on Land: 0 failed of 10 run (6 had data)` when four stations lie outside the bathymetry grid.

The toolbox also prints one `ODF file written to:` line per file. Two other lines are worth
watching for:

- `NOT WRITTEN (toolbox could not read the file; Stage 1 only): ...` — see
  [Troubleshooting](#troubleshooting).
- `verification failed` — each file is read back and compared with the results. This should
  never appear; if it does, keep the message and report it.

## 5. Check the quality-controlled files

Open a file from the output folder. Three things have changed.

**The quality header** lists the tests run and the result of each:

```text
QUALITY_HEADER,
  QUALITY_DATE='05-NOV-2026 12:12:17.73',
  QUALITY_TESTS='QUALITY CONTROL TESTS RUN',
  QUALITY_TESTS='Test 1.1: GTSPP Platform Identification (1)',
  ...
  QUALITY_TESTS='Test 2.10: GTSPP Density Inversion (32768)',
  QUALITY_COMMENTS='QUALITY CODES',
  ...
  QUALITY_COMMENTS='Test 2.7 Spike -> failed (PSAL_02: 1 value(s) flagged)',
  QUALITY_COMMENTS='Test 2.10 Density Inversion -> Density inversion found (SIGP_01, SIGP_02)'
```

The number in parentheses is the GTSPP test index. A test that found nothing to examine reads
`not applicable (...)`; for example, test 1.5 on the earliest station of a platform has no earlier
station to compare with.

**The flag columns.** Each parameter has a `Q<code>` column: 1 for values that passed, 3 for
doubtful, 4 for erroneous, 9 for missing. Derived parameters (`PSAL`, `POTM`, `SIGP`, `DOXY`, ...)
take the worse flag of the parameters they are computed from.

**The `QCFF_01` column.** For each data row it holds the sum of the GTSPP test indices of the
Stage 2 tests that flagged any value in that row. `0` means no test flagged the row.

### Find out which tests flagged a row

> The Python snippets in this guide import from `datashop_toolbox.gtspp_*`, which works when the scripts are in
> `src/datashop_toolbox/`. If they are in a plain folder, drop the `datashop_toolbox.` prefix
> (`from gtspp_odf_output import SCHEME`).

Subtract the indices, or let Python do it:

```python
from datashop_toolbox.gtspp_odf_output import SCHEME

qcff = 36864
print([f"{s.number} {s.name}" for s in SCHEME if qcff & s.bit])
# ['2.7 Spike', '2.10 Density Inversion']
```

To list the flagged rows of a written file:

```python
from pathlib import Path
from datashop_toolbox.odfhdr import OdfHeader

odf = OdfHeader()
odf.read_odf(Path(r"C:\Data\HUD2008004\QC\CTD_HUD2008004_001_1_DN.ODF"))
df = odf.data.data_frame
print(df[df["QCFF_01"] > 0][["PRES_01", "TEMP_01", "QTEMP_01", "PSAL_01", "QPSAL_01", "QCFF_01"]])
```

## Common variations

### Turn on the land, sounding and bottom tests

These tests (1.4, 1.6 and 2.11) need water depth from a GEBCO (or ETOPO) grid. To get a GEBCO_2026 grid in the
format the scripts read directly:

1. Open the [GEBCO download application](https://download.gebco.net).
2. Select the area: a box that covers every station of the cruise, with a margin of at least one degree.
3. Choose **GEBCO_2026 Grid (sub-ice topo/bathy)** and the **netCDF** format. You do not need the TID grid.
4. Pass the downloaded file with `--bathy`:

```powershell
python src\datashop_toolbox\gtspp_odf_output.py C:\Data\HUD2008004\ODF --out-dir C:\Data\HUD2008004\QC `
    --bathy C:\Data\GEBCO_2026_cruise_area.nc
```

The scripts read the file with `xarray` (step 1 of this guide). They look for latitude, longitude and elevation variables
(elevation negative at sea) and find them by name. If a file does not match, the error message lists the variables it
contains; for a different elevation variable name, pass `NetCDFBathymetry(path, var="<name>")` from Python.

- **A position outside the downloaded area** has no depth. The tests skip it, report `not applicable` in the quality
  header, and leave its sounding flag at 0. If you see this for stations that should be covered, download a larger
  area.
- **The global file** (about 4 GB, 7 GB unpacked) also works, but a cruise-area subset is faster to download and
  easier to keep with the data.
- A position on land, and a sounding that differs from the bathymetry by more than 10%, are flagged doubtful. As in
  the manual, a bad sounding fails both test 1.4 and test 1.6.

### Change a speed limit

Speed limits come from the `max_velocity` column of `platforms.csv`; edit the table to change one for good. To change
one for a single run, use Python (see [Run it from Python](#run-it-from-python)). Passing `max_speed_knots` replaces the
whole table, so start from the table's values:

```python
from datashop_toolbox.gtspp_stage1 import Stage1Config, get_platform_speeds

cfg1 = Stage1Config(max_speed_knots={**get_platform_speeds(), "HUDSON": 14.0})
```

### Run it from Python

This is how to change thresholds, the flags assigned on failure, or the derived-parameter rules:

```python
from datashop_toolbox.gtspp_stage1 import (
    QF, NetCDFBathymetry, Stage1Config, get_platform_speeds, load_stations, run_stage1,
)
from datashop_toolbox.gtspp_stage2 import Stage2Config, flagged_values, load_profiles, run_stage2
from datashop_toolbox.gtspp_odf_output import print_summary, save_stage2_to_odf

bathy = NetCDFBathymetry(r"C:\Data\GEBCO_2024.nc")

cfg1 = Stage1Config(
    max_speed_knots={**get_platform_speeds(), "HUDSON": 14.0},
    bathymetry=bathy,
    land_flag=QF.ERRONEOUS,          # flag a position on land 4 instead of 3
)
cfg2 = Stage2Config(
    bathymetry=bathy,
    spike_thresholds={"temperature": 1.0, "salinity": 0.2},
)

stations = load_stations(r"C:\Data\HUD2008004\ODF")
run_stage1(stations, cfg1)
profiles = load_profiles(stations)
run_stage2(profiles, cfg2)

print_summary(stations, profiles)
save_stage2_to_odf(profiles, r"C:\Data\HUD2008004\QC")
```

The available settings, and the flag each test assigns by default, are listed in
`Stage1Config` and `Stage2Config` in the [reference](gtspp_reference.md).

### Turn on the temperature inversion test

Test 2.12 is off until you set the smallest temperature difference to count as an inversion.
Choose it for your data and pass it in Python:

```python
cfg2 = Stage2Config(inversion_amplitude_c=0.5)   # example value: pick your own
```

### Get CSV reports without writing ODF files

```powershell
python src\datashop_toolbox\gtspp_stage2.py C:\Data\HUD2008004\ODF `
    --out-prefix HUD2008004
```

This writes `HUD2008004_stage1.csv` (one row per station), `HUD2008004_stage2.csv` (one row per
profile) and `HUD2008004_stage2_flagged_values.csv` (one row per doubtful or erroneous value, with
the tests responsible and, for derived parameters, the source column the flag came from).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `NameError: name 'Test1' is not defined` (or a similar `ImportError`) when starting | The three scripts are from different versions, or an import line was edited. | Replace all three scripts with the current versions and do not edit their `import` lines. They work in a plain folder and inside the package. |
| `ModuleNotFoundError: No module named 'datashop_toolbox'` | The toolbox is not installed in the active environment. | Activate the environment, or run `uv pip install -e .` in the toolbox folder. |
| `NetCDFBathymetry needs the 'xarray' package and a netCDF engine` | You passed `--bathy` without `xarray`. | `uv pip install xarray netCDF4` |
| `ValueError: found the following matches with the input file in xarray's IO backends: ['netcdf4', 'h5netcdf']. But their dependencies may not be installed` | `xarray` is installed but no netCDF engine is. | `uv pip install netCDF4` (or `h5netcdf`). |
| Test 2.10 is missing from the console summary and the quality header | `gsw` is not installed. | `uv pip install gsw` and run again. |
| `NOT WRITTEN (toolbox could not read the file; Stage 1 only)` | The toolbox rejects the file, for example an impossible `START_DATE_TIME` such as `31-FEB-2008`. Stage 1 still tested it. | The console shows a `Toolbox could not read <file> (...)` warning with the reason. Correct the header value in the original file and run again. |
| A platform is flagged `unknown, single-occurrence platform` | Its name is not in the known-platform list. | Add it to `lookups/platforms.csv`, or pass a list with `--platforms`. |
| `Known platforms not loaded (...)` warning | `lookups/platforms.csv` was not found from the current folder. | Run from the repository root, or pass `--platforms FILE`. |
| `Test 1.5 ... not applicable` on one station | It is the earliest station of its platform in this run, so there is no earlier station to compare with. | None needed. |
| `refusing to overwrite the input file` | `--out-dir` is the folder the file was read from. | Choose a different `--out-dir`. |
| `Partial set of quality-flag columns` | The file has `Q` columns for some parameters but not all. | Remove the partial `Q` columns from a copy of the file, or complete them, and run again. |
| `already has a QCFF_01 column from an earlier QC run` | The input is itself a QC'd file. | Run the QC on the original files instead. |

## See also

- [Reference for the GTSPP modules](gtspp_reference.md)
- The GTSPP Real-Time Quality Control Manual (IOC Manuals and Guides 22, first revised edition, 2010)
