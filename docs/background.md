# Background

> **Diátaxis quadrant:** [Explanation](https://diataxis.fr/explanation/) — this document is
> understanding-oriented. It explains *why* the toolbox exists, what problem the ODF
> format solves, and how the pieces of the codebase fit together conceptually. For the
> file format's field-by-field rules, see [`ODF_File_Specification.md`](ODF_File_Specification.md).
> For the toolbox's API surface, see [`reference.md`](reference.md).

## Why this toolbox exists

The **Ocean Data Information Section (ODIS)** at the **Bedford Institute of Oceanography
(BIO)**, Fisheries and Oceans Canada (DFO), is responsible for turning raw instrument
output, such as CTD casts from Sea-Bird and RBR instruments, and long-term moored temperature
records (MTRs, sometimes called thermographs), into processed datasets. These finalized
datasets get archived locally, nationally and sometimes internationally; they are also
used for research and analysis. The data processing steps invvole:

- parsing several incompatible raw/vendor formats into a common in-memory representation,
- attaching the metadata (cruise, event, instrument, calibration, quality) needed to make
  provide the necessary context for the dataset,
- running quality-control checks and recording exactly what was flagged and why, and
- writing the result out in a single, DFO-standard file format (ODF) that downstream
  systems and scientists can reliably use.

`datashop_toolbox` is the Python implementation of that pipeline. It replaced an in-house
MATLAB® toolbox which was preceeded by the original Fortran and VAX/VMS era toolbox.

## What ODF is

The **Ocean Data Format (ODF)** is a plain ASCII text format, developed at BIO and used
across DFO facilities, for archiving a single oceanographic data series, such as a single
profile (e.g. CTD cast) or a time-series (e.g. a thermograph deployment).

An ODF file has two parts:

1. A **header section**, made up of a fixed sequence of named blocks (`CRUISE_HEADER`,
   `EVENT_HEADER`, `INSTRUMENT_HEADER`, and so on) that carry all of the file's metadata.
2. A **data section**, introduced by a `-- DATA --` marker. Version 2.0 of the ODF format
   displays each data row as a white-space delimited columns of numbers. Version 3.0 of
   the ODF format, has a column header row that immediately follows the marker and
   each data row is stored as a comma-delimited set of numbers (scan, sample, or reading).

The toolbox targets **ODF specification version 3.0**, the version described in
[`ODF_File_Specification.md`](ODF_File_Specification.md). That revision — coinciding with
this Python toolbox's development — cleaned up a number of legacy quirks: trailing
commas on header lines were dropped, data rows became comma-delimited instead of
whitespace-delimited, a `-- DATA --` column-header line was introduced so parameter order
in the header no longer has to match column order in the data, and the `GENERAL_CAL_HEADER`,
`QUALITY_HEADER`, and `METEO_HEADER` blocks were added.

### The header blocks

Every ODF file is built from the same set of block types, each covering one aspect of
provenance or metadata:

| Block | Mandatory? | Purpose |
| --- | --- | --- |
| `ODF_HEADER` | Yes | File specification string and the ODF spec version the file conforms to. |
| `CRUISE_HEADER` | Yes | The mission the data came from — cruise number, platform, chief scientist, dates. |
| `EVENT_HEADER` | Yes | The specific sampling event (e.g. one CTD cast) — position, depth, timing, comments. |
| `METEO_HEADER` | Yes | Meteorological conditions recorded during the event. |
| `INSTRUMENT_HEADER` | Yes | The instrument that collected the data — type, model, serial number. |
| `QUALITY_HEADER` | Yes | Quality Control (QC) tests applied to the data and related comments. |
| `POLYNOMIAL_CAL_HEADER` | Optional | Polynomial calibration coefficients for a parameter. |
| `GENERAL_CAL_HEADER` | Optional | Non-polynomial calibrations (equation plus coefficients). |
| `COMPASS_CAL_HEADER` | Optional | Compass swing calibration, as direction/correction pairs. |
| `HISTORY_HEADER` | Yes | When the data were last modified, and the ordered list of processing steps applied. |
| `PARAMETER_HEADER` | Yes (one per column) | Describes one data column: code, name, units, null value, print formatting, and value range/counts. |
| `RECORD_HEADER` | Yes | Counts of calibration, swing, history, and parameter blocks, and of data cycles. |

Two conventions recur throughout the format and are worth calling out on their own:

#### The SYTM date/time format

Dates and times are stored as 23-character strings of the form `dd-MMM-yyyy
hh:mm:ss.ss` (e.g. `14-JUN-1999 14:47:40.37`). This is the **SYTM** format, a holdover
from the CMSYS system of the mid-1980s. Its null value, `17-NOV-1858 00:00:00.00`,
corresponds to time zero on the original VAX/VMS platform the format was designed for —
a detail that only makes sense in light of that history, but which the toolbox still has
to reproduce exactly for files to be considered valid ODF.

#### Parameter Codes (originally named GF3 codes)

Every data column is identified by a short parameter code (e.g. `PRES_01`, `TE90_01`)
drawn from a large, standardized code table (an extension of the GF3 parameter code
list). Each code has an associated description, units, and default print formatting.
The toolbox ships this table as a packaged lookup table (see
[`read_seaodf_parameters`](reference.md#read_seaodf_parameterspy) and
[`lookup_parameter`](reference.md#lookup_parameterpy)) so that parameter metadata can be
looked up and validated rather than typed out by hand for every file.

## How the toolbox is organized

The codebase is split into a few packages, each with a distinct responsibility:

```text
src/
├── datashop_toolbox/   # ODF data model, processing pipelines, interactive QC, GUI
├── odf_oracle/         # Loads populated ODF objects into the ODF_ARCHIVE Oracle database
├── seabird/            # Sea-Bird .cnv file parsing (extends the PySeabird project)
└── cotede/             # Vendored CoTeDe QC-test library, used for automated flagging
```

### `datashop_toolbox`: the ODF Data Model

At the core of the toolbox is a set of classes, one per ODF header block, that mirror
the specification directly: `CruiseHeader`, `EventHeader`, `MeteoHeader`,
`InstrumentHeader`, `QualityHeader`, `PolynomialCalHeader`, `GeneralCalHeader`,
`CompassCalHeader`, `HistoryHeader`, `ParameterHeader`, and `RecordHeader`. Each is built
on a shared `ValidatedBase`/`BaseHeader` foundation (Pydantic models) that normalizes
values, enforces the SYTM format on any date-like field, and knows how to render itself
back to ODF-formatted text.

These header objects are composed together by `OdfHeader`, which represents an entire
ODF file: it aggregates all of the header sections plus the tabular data (`DataRecords`,
a thin wrapper around a [pandas](https://pandas.pydata.org/) `DataFrame`), and provides the methods that do the actual
file I/O — `read_odf()`, `write_odf()`, `update_odf()` — along with helpers for managing
processing history and parameter codes. `ThermographHeader` (in `thermograph.py`) and
`Multinet` (in `multinet.py`) subclass `OdfHeader` to add instrument-specific behaviour
for moored temperature loggers and HYDRO-BIOS multinet CTD profiles, respectively.
`NetCdfHeader` similarly extends `OdfHeader` to support converting NetCDF files to ODF.

Around this data model sit the processing pipelines and tools:

- **Thermograph / MTR processing** — `thermograph.py` implements the core logic for
  reading raw MTR/minilog files and metadata, deriving SYTM timestamps and sampling
  intervals, and populating parameter headers; `process_mtr_files.py` wraps this into a
  batch pipeline (including a `QThread` worker so it can run from the GUI without
  blocking); `ai_thermograph_data.py` adds experimental, still-under-development
  QC assistance that uses regional bioregion and climatology lookups to sanity-check
  thermograph data automatically.
- **Interactive QC** — `qc_odf_data.py` is a unified `PySide6`/`pyqtgraph`-based QC tool
  that auto-detects whether an ODF file holds thermograph (time-series) or CTD (profile)
  data and presents the appropriate interactive plot, lasso-selection for flagging bad
  points, and metadata-aware overlays (e.g. deployment/recovery markers for
  thermographs).
- **Sea-Bird interoperability** — `compare_seabird_xmlcons.py` parses `.xmlcon` sensor
  configuration files, and `rbr_to_odf.py` reads RBR `.rsk` files (via `pyrsktools`),
  derives density, and plots profiles as part of converting RBR data to ODF.
- **File and metadata utilities** — smaller, focused modules round out the toolbox:
  `metadata_report.py`/`generate_metadata_report.py` build Excel summaries of a
  directory of ODF files; `concatenate_qat_files.py` merges QAT files from a mission;
  `fix_btl_header.py` repairs column spacing in `.btl` files; `remove_parameter.py`
  drops a parameter (and its data column) from an `OdfHeader` object;
  `select_metadata_file_and_data_folder.py` and `create_parameters_database.py` support
  the interactive tools and the packaged parameter-code lookup, respectively.
- **GUI** (`datashop_toolbox/gui/`) — PySide6 widgets and dialogs that give the above
  pipelines a user interface: `OdfMetadataForm`/`OdfMetadataDialog` for entering ODF
  metadata by hand, `rbr_to_odf_mainwindow.py` and `rbr_profile_plot.py` for the RBR→ODF
  workflow, and `thermograph_gui_loader.py` for collecting thermograph-processing inputs.
  Qt-Designer-generated `ui_*.py` files back these widgets but are treated as generated
  code, not hand-maintained source.

Two runnable entry points at the repository root tie these pieces together for everyday
use: `run_MTR_tools.py` (a small menu for processing raw MTR files, running thermograph
QC, or trying the experimental AI-assisted QC) and `run_SEABIRD_tools.py` (an example of
loading a Sea-Bird `.cnv` file with the bundled `seabird` parser).

### `odf_oracle`: archiving to Oracle

Once an `OdfHeader` object has been fully populated and QC'd, `odf_oracle` is
responsible for loading it into DFO's `ODF_ARCHIVE` Oracle database. It mirrors the ODF
header structure with one loader function per block type (`cruise_event_to_oracle`,
`instrument_to_oracle`, `quality_to_oracle`, `polynomial_cal_to_oracle`,
`general_cal_to_oracle`, `compass_cal_to_oracle`, `history_to_oracle`, `data_to_oracle`,
and their `*_comments_to_oracle`/`*_tests_to_oracle` companions), all of which are
orchestrated by `odf_to_oracle.py`. Supporting modules handle the pieces that don't map
one-to-one onto an ODF block: `database_connection_pool.py` configures Oracle sessions,
`sytm_to_timestamp.py` converts ODF's SYTM date/time strings to Oracle timestamps, and
`fix_null.py` normalizes ODF's numeric null sentinels (`-99`, `-99.9`, `-999`, `-999.9`)
to `NaN` before loading.

### `seabird` and `cotede`: open source dependencies

The toolbox utilizes a few third-party-derived packages. Most were written by
[Guilherme Castelão](https://github.com/castelao). A couple needed to be modified in
order to get them working because they are not actively maintained. The two such
packages are stored in `src/` rather than pulled in normally as external dependencies.
These two packages are:

- **`seabird`** extends the PySeabird project's `.cnv` parser to handle the range of
  Sea-Bird firmware output the toolbox encounters in practice — commented XML/CDATA
  blocks, partial or missing position/station metadata, and conversion of
  degrees-minutes-seconds coordinates to decimal degrees — exposing parsed profiles as
  NumPy masked arrays or pandas DataFrames.
- **`cotede`** (CoTeDe) supplies a configurable library of QC tests (range checks,
  spike detection, gradient checks, climatology comparisons, and more) that can be
  applied to a profile and combined into an overall QC flag, used as the automated
  quality-control layer underneath the toolbox's interactive QC tools.

## How it fits together

A typical workflow involves data being handled by these packages in sequence: raw
instrument output (e.g., a Sea-Bird `.cnv`, an RBR `.rsk`, or a raw MTR/minilog file)
is initially parsed into a `pandas` DataFrame and its associated metadata is populated
within an `OdfHeader` (or a subclass such as `ThermographHeader`). Next, automated QC
(via `cotede`) and/or interactive QC (via `qc_odf_data.py`) are used to assess the
data and assign quality flags and record history entries within the ODF header.
The completed `OdfHeader` is written out as a standards-compliant ODF file with
`write_odf()`. The data is then centrally archived by using `odf_oracle` to load
the output ODF file into the `ODF_ARCHIVE` Oracle database. The ODF object/file
remains the central self-describing artifact of this pipeline — which is
exactly the role the ODF format was designed to play.
