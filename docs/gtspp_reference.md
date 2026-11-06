# `gtspp_stage1` / `gtspp_stage2` / `gtspp_odf_output` — Reference

> **Status:** Draft, generated from the in-code docstrings.
> **Diátaxis quadrant:** [Reference](https://diataxis.fr/reference/) — this document is
> information-oriented and describes the public interface of the GTSPP quality control
> modules as it exists in code. It is not a tutorial or a how-to guide, and it does not
> explain *why* the modules are built this way.

## About this document

These three modules implement the Stage 1 and Stage 2 tests of the GTSPP Real-Time Quality
Control Manual (IOC Manuals and Guides 22, first revised edition, 2010) for ODF files read
with `datashop_toolbox`, and write the results back into the ODF files. This reference is
organized like the toolbox's own: one subsection per Python module, listing a one-line
summary, its classes with their methods, and its module-level functions. Signatures and
descriptions come directly from the source and docstrings, so regenerate this document
whenever the code changes. Private helpers (names beginning with an underscore) are listed
because they affect how the classes behave.

## Modules covered

| Module | Purpose |
|---|---|
| [`gtspp_stage1.py`](#gtspp_stage1py) | Stage 1 tests 1.1 to 1.6: platform, date/time, location, land, speed and sounding. |
| [`gtspp_stage2.py`](#gtspp_stage2py) | Stage 2 tests 2.1 to 2.12 on CTD profiles, plus flag inheritance for derived parameters. |
| [`gtspp_odf_output.py`](#gtspp_odf_outputpy) | Writes flags, `QCFF_01` and the `QUALITY_HEADER` into quality-controlled copies of the ODF files. |

The three modules work side by side in any folder, or inside `src/datashop_toolbox/`.

## Command-line entry points

| Command | Description |
|---|---|
| `python gtspp_stage1.py FOLDER` | Run Stage 1 and write a CSV summary. |
| `python gtspp_stage2.py FOLDER` | Run Stage 1 and Stage 2 and write CSV summaries and a list of flagged values. |
| `python gtspp_odf_output.py FOLDER --out-dir OUT` | Run both stages and write quality-controlled ODF files to `OUT`. |

---

## `datashop_toolbox` GTSPP modules

#### `gtspp_stage1.py`

GTSPP Stage 1 (location and identification) quality control for ODF files.

**class `QF(IntEnum)`**

Quality-flag values used by GTSPP and written to ODF ``Q<code>`` columns.

**class `Test(IntFlag)`**

Stage 1 test indices, as used in the GTSPP QCP / QCF bit masks.

**class `Stage1Config`**

Settings for the Stage 1 tests.

| Method | Description |
|---|---|
| `now_utc() -> datetime` | Return the reference time used by the date/time tests. |

**class `Station`**

One ODF file (event) with its Stage 1 inputs and results.

| Method | Description |
|---|---|
| `note(msg: str) -> None` | Append a message to :attr:`messages`. |
| `fail(test: Test, msg: str) -> None` | Record a failed test. |
| `any_bad(*keys: str) -> bool` | Check whether any named field is flagged erroneous or missing. |
| *(property)* `platform_key() -> str \| None` | Return the platform identifier in normalised form. |
| *(property)* `when() -> datetime \| None` | Return the observation time as a ``datetime``. |
| *(property)* `position_ok() -> bool` | Check that the start position can be used by later tests. |
| *(property)* `qcp_hex() -> str` | Return the QCP code (tests performed) as hexadecimal text. |
| *(property)* `qcf_hex() -> str` | Return the QCF code (tests failed) as hexadecimal text. |
| *(property)* `label() -> str` | Return a short identifier for reports and messages. |

**class `Bathymetry(Protocol)`**

Protocol for a source of water depth.

| Method | Description |
|---|---|
| `depth_at(lat: float, lon: float) -> float \| None` | Return the water depth at a position. |

**class `NetCDFBathymetry`**

Nearest-grid-cell water depth from a netCDF grid.

| Method | Description |
|---|---|
| `__init__(path: str \| Path, var: str \| None = None, elevation_positive_up: bool = True)` | Open a bathymetry grid. |
| `depth_at(lat: float, lon: float) -> float \| None` | Return the water depth at the grid cell nearest a position. |

| Function | Description |
|---|---|
| `get_platforms() -> list` | Read the known platform names from the toolbox lookup table. |
| `_default_known_platforms() -> set[str]` | Return the default for :attr:`Stage1Config.known_platforms`. |
| `_norm(s: Any) -> str \| None` | Normalise an identifier for comparison. |
| `_to_float(x: Any) -> float \| None` | Convert a value to a finite float. |
| `parse_datetime_parts(value: Any) -> dict \| None` | Split a date/time into integer parts without validating it. |
| `_to_datetime(o: dict \| None) -> datetime \| None` | Build a ``datetime`` from the parts made by :func:`parse_datetime_parts`. |
| `_days_in_month(y: int, m: int) -> int` | Return the number of days in a month. |
| `haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float` | Compute the great-circle distance between two positions. |
| `test_1_1_platform_id(stations: Sequence[Station], cfg: Stage1Config) -> None` | Run test 1.1, Platform Identification. |
| `test_1_2_date_time(s: Station, cfg: Stage1Config) -> None` | Run test 1.2, Impossible Date/Time. |
| `test_1_3_location(s: Station, cfg: Stage1Config) -> None` | Run test 1.3, Impossible Location. |
| `_sounding_value(s: Station, cfg: Stage1Config) -> float \| None` | Return a station's sounding, or ``None`` if it is missing. |
| `_sounding_agrees(sounding: float, depth: float, tol: float) -> bool` | Check a sounding against the bathymetry. |
| `test_1_4_position_on_land(s: Station, cfg: Stage1Config) -> None` | Run test 1.4, Position on Land. |
| `test_1_6_impossible_sounding(s: Station, cfg: Stage1Config) -> None` | Run test 1.6, Impossible Sounding. |
| `test_1_5_impossible_speed(stations: Sequence[Station], cfg: Stage1Config) -> None` | Run test 1.5, Impossible Speed. |
| `run_stage1(stations: Sequence[Station], cfg: Stage1Config) -> pd.DataFrame` | Run tests 1.1 to 1.6 in the manual's order. |
| `results_frame(stations: Sequence[Station]) -> pd.DataFrame` | Summarise Stage 1 results in a table. |
| `_fetch(odf: Any, key: str) -> Any` | Read one header field from a toolbox object. |
| `read_odf_file(path: str \| Path) -> Any` | Read one ODF file with ``datashop_toolbox``. |
| `_pos(x: Any) -> float \| None` | Convert a position to a float, treating ODF null markers as missing. |
| `station_from_odf(odf: Any, source: str \| Path = '') -> Station` | Build a :class:`Station` from a toolbox object. |
| `station_from_raw_text(path: str \| Path) -> Station` | Build a :class:`Station` from the raw header text of an ODF file. |
| `load_stations(folder: str \| Path, pattern: str = '*.ODF') -> list[Station]` | Read a folder of ODF files into stations. |
| `main() -> None` | Run Stage 1 from the command line and write a CSV summary. |

#### `gtspp_stage2.py`

GTSPP Stage 2 (profile) quality control for ODF files.

**class `Test2(IntFlag)`**

Stage 2 test indices, as used in the GTSPP QCP / QCF bit masks.

**class `Region`**

A sea area with its own parameter limits (test 2.2).

**class `Stage2Config`**

Settings for the Stage 2 tests.

**class `Profile`**

One profile with its values, quality flags and failure reasons.

| Method | Description |
|---|---|
| *(static)* `code(col: str) -> str` | Return the parameter code of a column name. |
| `cols_of(kind: str) -> list[str]` | List the columns of one kind of parameter. |
| `partner(col: str, kind: str) -> str \| None` | Find the column of another kind that belongs to the same sensor. |
| *(property)* `pos_ok() -> bool` | Check that the profile position can be used. |
| `eligible(col: str, skip: Sequence[int] = BAD_I) -> np.ndarray` | Select the values that a test may use. |
| `_gsw()` | Import and return the ``gsw`` package, or ``None`` if it is missing. |
| `depth_m() -> np.ndarray` | Return the depth of each level in metres. |
| `pressure_dbar() -> np.ndarray` | Return the pressure of each level in decibars. |
| `_n() -> int` | Return the number of levels (rows) in the profile. |
| `t90(col: str, cfg: Stage2Config) -> np.ndarray` | Return a temperature column on the ITS-90 scale. |
| `t68(col: str, cfg: Stage2Config) -> np.ndarray` | Return a temperature column on the IPTS-68 scale. |
| `flag(col: str, idx, new: QF, test: Test2) -> None` | Set the flag of one or more values. |
| `note(msg: str) -> None` | Append a message to :attr:`messages`. |

| Function | Description |
|---|---|
| `kind_of(code: str) -> str \| None` | Classify a parameter code. |
| `_apply_range(p: Profile, col: str, lo: float, hi: float, flag: QF, test: Test2) -> None` | Flag the values of a column that are outside a range. |
| `test_2_1_global_range(p: Profile, cfg: Stage2Config) -> None` | Run test 2.1, Global Impossible Parameter Values. |
| `_in_polygon(lat: float, lon: float, poly: Sequence[tuple[float, float]]) -> bool` | Check whether a position is inside a polygon. |
| `test_2_2_regional_range(p: Profile, cfg: Stage2Config) -> None` | Run test 2.2, Regional Impossible Parameter Values. |
| `test_2_3_increasing_depth(p: Profile, cfg: Stage2Config) -> None` | Run test 2.3, Increasing Depth. |
| `_envelope_for(depth: float, table: Sequence[tuple])` | Find the test 2.4 envelope for a depth. |
| `test_2_4_profile_envelope(p: Profile, cfg: Stage2Config) -> None` | Run test 2.4, Profile Envelope. |
| `test_2_5_constant_profile(p: Profile, cfg: Stage2Config) -> None` | Run test 2.5, Constant Profile. |
| `freezing_point_ipts68(sal, pres_dbar)` | Compute the freezing point of seawater (UNESCO, 1983). |
| `test_2_6_freezing_point(p: Profile, cfg: Stage2Config) -> None` | Run test 2.6, Freezing Point. |
| `_tests_columns(p: Profile)` | Iterate over the temperature and salinity columns of a profile. |
| `test_2_7_spike(p: Profile, cfg: Stage2Config) -> None` | Run test 2.7, Spike. |
| `test_2_8_top_bottom_spike(p: Profile, cfg: Stage2Config) -> None` | Run test 2.8, Top and Bottom Spike. |
| `test_2_9_gradient(p: Profile, cfg: Stage2Config) -> None` | Run test 2.9, Gradient. |
| `test_2_10_density_inversion(p: Profile, cfg: Stage2Config) -> None` | Run test 2.10, Density Inversion. |
| `test_2_11_bottom(p: Profile, cfg: Stage2Config) -> None` | Run test 2.11, Bottom. |
| `test_2_12_temperature_inversion(p: Profile, cfg: Stage2Config) -> None` | Run test 2.12, Temperature Inversion. |
| `test_enabled(test: Test2, p: Profile, cfg: Stage2Config) -> bool` | Check whether a test can run in this configuration. |
| `inherit_derived_flags(p: Profile, cfg: Stage2Config) -> None` | Give derived parameters the worse flag of their sources. |
| `run_stage2(profiles: Sequence[Profile], cfg: Stage2Config) -> pd.DataFrame` | Run tests 2.1 to 2.12 on every profile. |
| `combined_codes(station: Station \| None, p: Profile) -> tuple[str, str]` | Combine the Stage 1 and Stage 2 QCP / QCF codes. |
| `profile_summary(profiles: Sequence[Profile]) -> pd.DataFrame` | Summarise Stage 2 results in a table. |
| `flagged_values(profiles: Sequence[Profile]) -> pd.DataFrame` | List every doubtful or erroneous value. |
| `_get_dataframe(odf: Any) -> pd.DataFrame` | Find the data table of a toolbox object. |
| `_null_values(odf: Any) -> dict[str, float]` | Read the null value of each parameter. |
| `profile_from_station(st: Station, default_null: float = -99.0) -> Profile` | Build a :class:`Profile` from a Stage 1 station. |
| `load_profiles(stations: Sequence[Station]) -> list[Profile]` | Build profiles for every station that has toolbox data. |
| `profile_from_arrays(label: str, lat: float, lon: float, columns: Mapping[str, Sequence[float]], sounding: float \| None = None) -> Profile` | Build a :class:`Profile` directly from arrays. |
| `main() -> None` | Run Stage 1 and Stage 2 from the command line and write CSV files. |

#### `gtspp_odf_output.py`

Save GTSPP quality control results into ODF files with ``datashop_toolbox``.

**class `TestSpec`**

A Stage 2 test as it appears in the quality header.

| Method | Description |
|---|---|
| *(property)* `bit() -> int` | Return the GTSPP test index, added to QCFF when the test fails. |

**class `Stage1Spec`**

A Stage 1 test as it appears in the quality header.

| Method | Description |
|---|---|
| *(property)* `bit() -> int` | Return the GTSPP test index (1, 2, 4, 8, 16 or 32). |

| Function | Description |
|---|---|
| `_clean(text: str) -> str` | Make text safe for a single-quoted ODF header string. |
| `_result_stage1(st: Station, spec: Stage1Spec) -> str` | Describe the outcome of a Stage 1 test for the quality header. |
| `compute_qcff(p: Profile) -> np.ndarray` | Compute the QCFF value of every data row. |
| `_density_label(p: Profile, col: str) -> str` | Name the density column that a test 2.10 result refers to. |
| `_result(p: Profile, spec: TestSpec) -> str` | Describe the outcome of a Stage 2 test for the quality header. |
| `build_quality_header(p: Profile, date: str \| None = None)` | Build the ``QUALITY_HEADER`` for a profile. |
| `_is_flag_code(code: str, df_cols) -> bool` | Check whether a parameter code is itself a flag column. |
| `ensure_flag_columns(odf) -> None` | Make sure every parameter has a ``Q<code>`` column. |
| `_qcff_header()` | Create the parameter header of the ``QCFF_01`` column. |
| `apply_profile_to_odf(p: Profile, add_history: bool = True) -> None` | Write a profile's results into its toolbox object. |
| `_raw_file_spec(path: str) -> str \| None` | Read ``FILE_SPECIFICATION`` from the raw text of an ODF file. |
| `write_profile_odf(p: Profile, out_dir: str \| Path, add_history: bool = True) -> Path` | Write one quality-controlled ODF file. |
| `verify_written(p: Profile, path: Path) -> list[str]` | Check a written file against the in-memory results. |
| `print_summary(stations: Sequence[Station], profiles: Sequence[Profile]) -> None` | Print the Stage 1 and Stage 2 results to the console. |
| `save_stage2_to_odf(profiles: Sequence[Profile], out_dir: str \| Path, add_history: bool = True, verify: bool = True) -> list[Path]` | Write quality-controlled ODF files for all profiles. |
| `main() -> None` | Run Stage 1 and Stage 2 from the command line and write the ODF files. |
