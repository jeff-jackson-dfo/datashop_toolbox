"""
gtspp_stage1.py
---------------
GTSPP Stage 1 (location and identification) quality control for ODF files.

Implements the six Stage 1 tests of the GTSPP Real-Time Quality Control
Manual (IOC Manuals and Guides 22, first revised edition, 2010) for ODF
files read with :class:`~datashop_toolbox.odfhdr.OdfHeader`.

  Tests (GTSPP test index in parentheses)
  ───────────────────────────────────────
  • 1.1  Platform Identification  (1)   : platform is a known identifier
  • 1.2  Impossible Date/Time     (2)   : year, month, day, hour, minute
  • 1.3  Impossible Location      (4)   : latitude and longitude range
  • 1.4  Position on Land         (8)   : needs a bathymetry source
  • 1.5  Impossible Speed         (16)  : between consecutive stations
  • 1.6  Impossible Sounding      (32)  : needs a bathymetry source

  Quality flags
  ─────────────
  0 unchecked · 1 good · 2 inconsistent · 3 doubtful · 4 erroneous ·
  5 changed · 9 missing

  Design notes
  ────────────
  • The manual's rules ask an operator to choose between "doubtful" and
    "erroneous", or to infer a correction. Here those choices are automated
    through :class:`Stage1Config`. The only corrections made are the manual's
    deterministic ones (hour 24, minute 60, longitude 180-360); the original
    value is kept in :attr:`Station.original` and the flag is set to 5.
  • Stage 1 judges header fields (platform, date/time, position, sounding),
    for which an ODF has no flag columns. Results are kept on the
    :class:`Station` objects; ``gtspp_odf_output.py`` writes them to the ODF
    ``QUALITY_HEADER``.
  • All access to ``datashop_toolbox`` is confined to :data:`ODF_FIELD_MAP`,
    :func:`read_odf_file` and :func:`station_from_odf`. When the toolbox
    rejects a file (for example ``31-FEB-2008`` in ``START_DATE_TIME``),
    :func:`station_from_raw_text` still reads the header fields so that the
    tests can report the problem.
  • QCP / QCF: per station, the bit masks of the tests performed and failed
    (sums of the test indices above), available as hexadecimal strings from
    :attr:`Station.qcp_hex` and :attr:`Station.qcf_hex`.

  Shared infrastructure
  ─────────────────────
  • QF / Test            – quality-flag values and test indices
  • Stage1Config         – thresholds, flags to assign and optional inputs
  • Station              – one ODF header plus its Stage 1 results
  • Bathymetry           – protocol for a water-depth source
  • NetCDFBathymetry     – GEBCO / ETOPO style netCDF implementation
  • run_stage1           – run tests 1.1 to 1.6 and summarise the results
  • load_stations        – read a folder of ODF files into stations

  Usage
  ─────
      stations = load_stations("odf_folder")
      cfg = Stage1Config()  # known platforms and speed limits come from lookups/platforms.csv
      summary = run_stage1(stations, cfg)

  From the command line:

      python gtspp_stage1.py odf_folder
"""

from __future__ import annotations

import argparse
import calendar
import logging
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import IntEnum, IntFlag
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

log = logging.getLogger("gtspp_stage1")


# --------------------------------------------------------------------------- #
# Flags and test indices
# --------------------------------------------------------------------------- #
class QF(IntEnum):
    """Quality-flag values used by GTSPP and written to ODF ``Q<code>`` columns.

    Attributes:
        UNCHECKED: 0 - the value has not been quality controlled.
        GOOD: 1 - the value seems to be correct.
        PROBABLY_GOOD: 2 - the value appears inconsistent with other values.
        DOUBTFUL: 3 - the value seems doubtful.
        ERRONEOUS: 4 - the value seems erroneous.
        CHANGED: 5 - the value was modified.
        MISSING: 9 - the value is missing.
    """

    UNCHECKED = 0
    GOOD = 1
    PROBABLY_GOOD = 2
    DOUBTFUL = 3
    ERRONEOUS = 4
    CHANGED = 5
    MISSING = 9


class Test(IntFlag):
    """Stage 1 test indices, as used in the GTSPP QCP / QCF bit masks.

    Attributes:
        NONE: No test.
        PLATFORM_ID: Test 1.1, Platform Identification (1).
        DATE_TIME: Test 1.2, Impossible Date/Time (2).
        LOCATION: Test 1.3, Impossible Location (4).
        ON_LAND: Test 1.4, Position on Land (8).
        SPEED: Test 1.5, Impossible Speed (16).
        SOUNDING: Test 1.6, Impossible Sounding (32).
    """

    NONE = 0
    PLATFORM_ID = 1
    DATE_TIME = 2
    LOCATION = 4
    ON_LAND = 8
    SPEED = 16
    SOUNDING = 32


BAD = (QF.ERRONEOUS, QF.MISSING)
DATE_PARTS = ("year", "month", "day", "hour", "minute")
FLAG_KEYS = ("platform", *DATE_PARTS, "latitude", "longitude", "sounding")


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #
def _platforms_csv_path() -> Path:
    """Return the path of the platform lookup table, relative to the working directory."""
    return Path.cwd() / "src/datashop_toolbox/lookups/platforms.csv"


def get_platforms() -> list:
    """Read the known platform names from the toolbox lookup table.

    Reads ``src/datashop_toolbox/lookups/platforms.csv`` relative to the
    current working directory, so run from the repository root. The first
    row of the file is treated as a header and the first column
    (``platform_name``) is used.

    Returns:
        The values of the first column, in file order.

    Raises:
        FileNotFoundError: If the lookup file does not exist.
    """
    platform_path = _platforms_csv_path()
    df = pd.read_csv(platform_path)
    my_list = df.iloc[:, 0].tolist()
    return my_list


def get_platform_speeds() -> dict[str, float]:
    """Read the maximum speed of each platform from the toolbox lookup table.

    Uses the ``platform_name`` and ``max_velocity`` columns of the table
    described in :func:`get_platforms`. The speeds are taken to be in knots.
    If a name appears more than once (vessels with the same name and
    different call signs), the largest speed is kept, so that test 1.5 does
    not fail a vessel because of the slower namesake.

    Returns:
        Maximum speed in knots, by platform name as written in the table.

    Raises:
        FileNotFoundError: If the lookup file does not exist.
        ValueError: If the file has no ``platform_name`` or ``max_velocity``
            column.
    """
    df = pd.read_csv(_platforms_csv_path())
    missing = {"platform_name", "max_velocity"} - set(df.columns)
    if missing:
        raise ValueError(f"platforms.csv has no column(s): {sorted(missing)}")
    speeds: dict[str, float] = {}
    names = df["platform_name"].tolist()
    values = np.asarray(pd.to_numeric(df["max_velocity"], errors="coerce"), dtype=float)
    for name, v in zip(names, values, strict=True):
        if isinstance(name, str) and math.isfinite(v):
            speeds[name] = max(float(v), speeds.get(name, float(v)))
    return speeds


def _default_known_platforms() -> set[str]:
    """Return the default for :attr:`Stage1Config.known_platforms`.

    Returns:
        The platforms from :func:`get_platforms`, or an empty set, with a
        warning, if the lookup file cannot be found from the current working
        directory.
    """
    try:
        return set(get_platforms())
    except FileNotFoundError as exc:
        log.warning("Known platforms not loaded (%s); pass known_platforms or --platforms", exc)
        return set()


def _default_max_speeds() -> dict[str, float]:
    """Return the default for :attr:`Stage1Config.max_speed_knots`.

    Returns:
        The speeds from :func:`get_platform_speeds`, or an empty dict if the
        lookup file cannot be found. :func:`_default_known_platforms` already
        warns about that, so this logs only at debug level.
    """
    try:
        return get_platform_speeds()
    except FileNotFoundError as exc:
        log.debug("Platform speeds not loaded (%s)", exc)
        return {}


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass
class Stage1Config:
    """Settings for the Stage 1 tests.

    The manual lets an operator decide, case by case, whether a failure is
    "doubtful" (3) or "erroneous" (4). Those decisions are made here, once,
    through the ``*_flag`` attributes.

    Attributes:
        known_platforms: Platform identifiers accepted by test 1.1. Case and
            repeated spaces are ignored. Defaults to the platforms in the
            toolbox lookup table (see :func:`get_platforms`).
        unknown_platform_flag: Flag for a platform that is not in
            ``known_platforms`` and occurs only once in the run.
        now: Reference time for the date/time tests. Defaults to the current
            UTC time when ``None``.
        realtime: If ``True``, apply the "not older than 30 days" rule of
            test 1.2 (real-time data only).
        old_realtime_flag: Flag for a real-time observation older than 30
            days. ``None`` skips the check, which the manual allows.
        date_flag: Flag assigned to a date/time part that fails test 1.2.
        apply_rollover: If ``True``, hour 24 becomes hour 0 of the next day
            and minute 60 becomes minute 0 of the next hour (flag 5) instead
            of failing.
        position_flag: Flag for an impossible latitude or longitude (1.3).
        convert_lon_0_360: If ``True``, longitudes in the range (180, 360]
            are converted to negative longitudes before test 1.3.
        bathymetry: Water-depth source for tests 1.4 and 1.6. Both tests
            are skipped when ``None``.
        land_flag: Flag for a position on land (1.4).
        sounding_tolerance: Largest allowed relative difference between the
            sounding and the bathymetry (0.10 means 10%).
        sounding_flag: Flag for a sounding that disagrees with the
            bathymetry (1.4, 1.6).
        sounding_null_values: Sounding values that mean "missing".
        max_speed_knots: Maximum plausible speed in knots, by platform
            identifier (1.5). Defaults to the ``max_velocity`` column of the
            toolbox lookup table (see :func:`get_platform_speeds`).
        default_max_speed_knots: Limit for platforms that are not in
            ``max_speed_knots`` (the lookup table by default). ``None`` means such platforms are not
            tested, as in the manual.
        speed_flag: Flag for a position that implies an impossible speed.
    """

    # Test 1.1 -- list of known platform identifiers (as they appear in ODF)
    known_platforms: set[str] = field(default_factory=_default_known_platforms)
    unknown_platform_flag: QF = QF.DOUBTFUL

    # Test 1.2
    now: datetime | None = None  # defaults to current UTC time
    realtime: bool = False  # apply the "within 30 days" rule
    old_realtime_flag: QF | None = None  # None = operator ignores >30 d (manual allows)
    date_flag: QF = QF.ERRONEOUS
    apply_rollover: bool = True  # hour 24 / minute 60 corrections

    # Test 1.3
    position_flag: QF = QF.ERRONEOUS
    convert_lon_0_360: bool = True  # 180 < lon <= 360  ->  lon - 360

    # Tests 1.4 / 1.6 -- needs a bathymetry object (see Bathymetry below)
    bathymetry: Bathymetry | None = None
    land_flag: QF = QF.DOUBTFUL
    sounding_tolerance: float = 0.10  # "within 10%" of bathymetry
    sounding_flag: QF = QF.DOUBTFUL
    sounding_null_values: tuple = (-99.0,)  # ODF null for numerics

    # Test 1.5 -- knots; platform must be in this table (or default is given)
    max_speed_knots: Mapping[str, float] = field(default_factory=_default_max_speeds)
    default_max_speed_knots: float | None = None
    speed_flag: QF = QF.DOUBTFUL

    def now_utc(self) -> datetime:
        """Return the reference time used by the date/time tests.

        Returns:
            :attr:`now` converted to UTC and made timezone-naive, or the current
            UTC time if :attr:`now` is ``None``.
        """
        n = self.now or datetime.now(UTC)
        return n.replace(tzinfo=None) if n.tzinfo is None else n.astimezone(UTC).replace(tzinfo=None)


# --------------------------------------------------------------------------- #
# Station record (one ODF file / event)
# --------------------------------------------------------------------------- #
@dataclass
class Station:
    """One ODF file (event) with its Stage 1 inputs and results.

    A station is built from the header of an ODF file by
    :func:`station_from_odf`, or from the raw header text by
    :func:`station_from_raw_text` when the toolbox cannot read the file.

    Attributes:
        source: Path of the ODF file.
        platform: Platform name from ``CRUISE_HEADER``.
        cruise_number: Cruise number from ``CRUISE_HEADER``.
        event_number: Event number from ``EVENT_HEADER``.
        data_type: Data type from ``EVENT_HEADER`` (for example ``CTD``).
        obs: Start date/time as a dict with the integer keys ``year``,
            ``month``, ``day``, ``hour``, ``minute`` and ``second``. Values
            are not validated, so impossible dates survive to be flagged.
        end_obs: End date/time, in the same form as ``obs``.
        latitude: Start latitude in decimal degrees.
        longitude: Start longitude in decimal degrees.
        end_latitude: End latitude, if present.
        end_longitude: End longitude, if present.
        sounding: Water depth in metres from the header.
        odf: The :class:`~datashop_toolbox.odfhdr.OdfHeader` object, kept so
            that results can be written back. ``None`` for stations read
            from raw text.
        flags: Quality flag (:class:`QF`) for each tested field: ``platform``,
            ``year``, ``month``, ``day``, ``hour``, ``minute``,
            ``latitude``, ``longitude`` and ``sounding``.
        original: Original values of fields that were corrected.
        ran: Tests that were enabled for this station.
        performed: Tests that found data to examine (the GTSPP QCP mask).
        failed: Tests that failed (the GTSPP QCF mask).
        messages: Human-readable notes, each prefixed with ``[TEST_NAME]``.
    """

    source: str = ""
    platform: str | None = None
    cruise_number: str | None = None
    event_number: str | None = None
    data_type: str | None = None
    obs: dict | None = None  # year, month, day, hour, minute, second
    end_obs: dict | None = None
    latitude: float | None = None
    longitude: float | None = None
    end_latitude: float | None = None
    end_longitude: float | None = None
    sounding: float | None = None
    odf: Any = None  # the toolbox object, kept for write-back
    flags: dict = field(default_factory=lambda: {k: QF.UNCHECKED for k in FLAG_KEYS})
    original: dict = field(default_factory=dict)  # originals of changed values
    ran: Test = Test.NONE  # tests that were enabled/executed for this station
    performed: Test = Test.NONE  # QCP: tests that found data to examine
    failed: Test = Test.NONE  # QCF
    messages: list = field(default_factory=list)

    # -- helpers ---------------------------------------------------------- #
    def note(self, msg: str) -> None:
        """Append a message to :attr:`messages`.

        Args:
            msg: Message text, conventionally prefixed with ``[TEST_NAME]``.
        """
        self.messages.append(msg)

    def fail(self, test: Test, msg: str) -> None:
        """Record a failed test.

        Sets the test's bit in :attr:`failed` and appends the message.

        Args:
            test: The test that failed.
            msg: Explanation, stored as ``[TEST_NAME] <msg>``.
        """
        self.failed |= test
        self.note(f"[{test.name}] {msg}")

    def any_bad(self, *keys: str) -> bool:
        """Check whether any named field is flagged erroneous or missing.

        Args:
            *keys: Keys of :attr:`flags`, for example ``"latitude"``.

        Returns:
            ``True`` if at least one of the fields has flag 4 or 9.
        """
        return any(self.flags[k] in BAD for k in keys)

    @property
    def platform_key(self) -> str | None:
        """Return the platform identifier in normalised form.

        Returns:
            :attr:`platform` upper-cased, with quotes removed and repeated
            spaces collapsed, or ``None`` if there is no platform.
        """
        return _norm(self.platform)

    @property
    def when(self) -> datetime | None:
        """Return the observation time as a ``datetime``.

        Returns:
            The start time, or ``None`` if a date/time part is missing, cannot
            form a real date, or is flagged erroneous or missing.
        """
        return _to_datetime(self.obs) if not self.any_bad(*DATE_PARTS) else None

    @property
    def position_ok(self) -> bool:
        """Check that the start position can be used by later tests.

        Returns:
            ``True`` if latitude and longitude are present and neither is
            flagged erroneous or missing.
        """
        return self.latitude is not None and self.longitude is not None and not self.any_bad("latitude", "longitude")

    @property
    def qcp_hex(self) -> str:
        """Return the QCP code (tests performed) as hexadecimal text."""
        return f"{int(self.performed):X}"

    @property
    def qcf_hex(self) -> str:
        """Return the QCF code (tests failed) as hexadecimal text."""
        return f"{int(self.failed):X}"

    @property
    def label(self) -> str:
        """Return a short identifier for reports and messages.

        Returns:
            ``<data type>_<cruise number>_<event number>``, using the parts that
            exist, or the file name if none of them is set.
        """
        parts = [self.data_type, self.cruise_number, self.event_number]
        return "_".join(str(p) for p in parts if p) or Path(self.source).name


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def _norm(s: Any) -> str | None:
    """Normalise an identifier for comparison.

    Args:
        s: Identifier such as a platform name, or ``None``.

    Returns:
        The identifier upper-cased with quotes removed and repeated spaces
        collapsed, or ``None`` if ``s`` is ``None`` or empty.
    """
    if s is None:
        return None
    s = re.sub(r"\s+", " ", str(s).strip().strip("'\"")).upper()
    return s or None


def _to_float(x: Any) -> float | None:
    """Convert a value to a finite float.

    Args:
        x: Number or numeric text. Quotes around text are ignored.

    Returns:
        The value as a ``float``, or ``None`` if it is not numeric or not
        finite.
    """
    try:
        v = float(str(x).strip().strip("'\"")) if isinstance(x, str) else float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


_MONTHS = {m.upper(): i for i, m in enumerate(calendar.month_abbr) if m}
_ODF_DT = re.compile(r"^\s*'?(\d{1,2})-([A-Za-z]{3})-(\d{4})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2})(?:\.\d+)?)?'?\s*$")
_ISO_DT = re.compile(r"^\s*'?(\d{4})-(\d{1,2})-(\d{1,2})[T ](\d{1,2}):(\d{1,2})(?::(\d{1,2})(?:\.\d+)?)?Z?'?\s*$")


def parse_datetime_parts(value: Any) -> dict | None:
    """Split a date/time into integer parts without validating it.

    Impossible values such as ``31-FEB-2008 25:61:00.00`` are kept so that
    test 1.2 can detect them.

    Args:
        value: A ``datetime``, ``pandas.Timestamp``, ODF text
            (``DD-MON-YYYY HH:MM:SS.ss``) or ISO text
            (``YYYY-MM-DD HH:MM:SS``).

    Returns:
        A dict with the keys ``year``, ``month``, ``day``, ``hour``,
        ``minute`` and ``second``, or ``None`` if ``value`` is empty,
        unrecognised, or the ODF null date ``17-NOV-1858``.
    """
    if value is None:
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return dict(
            year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute, second=value.second
        )
    s = str(value)
    m = _ODF_DT.match(s)
    if m and m.group(2).upper() in _MONTHS:
        d, mon, y, h, mi, sec = m.groups()
        if (int(d), mon.upper(), int(y)) == (17, "NOV", 1858):  # ODF null date (MJD epoch)
            return None
        return dict(
            year=int(y), month=_MONTHS[mon.upper()], day=int(d), hour=int(h), minute=int(mi), second=int(sec or 0)
        )
    m = _ISO_DT.match(s)
    if m:
        y, mon, d, h, mi, sec = m.groups()
        return dict(year=int(y), month=int(mon), day=int(d), hour=int(h), minute=int(mi), second=int(sec or 0))
    return None


def _to_datetime(o: dict | None) -> datetime | None:
    """Build a ``datetime`` from the parts made by :func:`parse_datetime_parts`.

    Args:
        o: Dict of date/time parts, or ``None``.

    Returns:
        The ``datetime``, or ``None`` if ``o`` is empty or does not form a
        real date and time.
    """
    if not o:
        return None
    try:
        return datetime(o["year"], o["month"], o["day"], o["hour"], o["minute"], o.get("second", 0))
    except (ValueError, TypeError, KeyError):
        return None


def _days_in_month(y: int, m: int) -> int:
    """Return the number of days in a month.

    Args:
        y: Year.
        m: Month.

    Returns:
        The number of days, or 31 if the year or month is out of range.
    """
    return calendar.monthrange(y, m)[1] if 1 <= y <= 9999 and 1 <= m <= 12 else 31


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the great-circle distance between two positions.

    Args:
        lat1: Latitude of the first position, in degrees.
        lon1: Longitude of the first position, in degrees.
        lat2: Latitude of the second position, in degrees.
        lon2: Longitude of the second position, in degrees.

    Returns:
        The distance in metres, using a spherical Earth of mean radius
        6371008.8 m.
    """
    R = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


# --------------------------------------------------------------------------- #
# Bathymetry (tests 1.4 and 1.6)
# --------------------------------------------------------------------------- #
class Bathymetry(Protocol):
    """Protocol for a source of water depth.

    Any object with a :meth:`depth_at` method can be used by tests 1.4, 1.6
    and (in ``gtspp_stage2.py``) 2.11.
    """

    def depth_at(self, lat: float, lon: float) -> float | None:
        """Return the water depth at a position.

        Args:
            lat: Latitude in degrees.
            lon: Longitude in degrees.

        Returns:
            Water depth in metres, positive down. A value of zero or less means
            land. ``None`` means there is no data at that position.
        """


class NetCDFBathymetry:
    """Nearest-grid-cell water depth from a netCDF grid, read with xarray.

    Works with GEBCO and ETOPO style files, whole or a downloaded
    sub-area. Positions are matched to the nearest grid cell, as with
    ``DataArray.sel(..., method="nearest")``, and many positions can be
    looked up at once with :meth:`depths_at`. Positions outside the grid
    return ``None`` (no data) rather than the nearest edge cell.

    Requires the ``xarray`` package and a netCDF engine for it (``netCDF4``
    or ``h5netcdf``). ``datashop_toolbox`` installs none of them.

    Attributes:
        ds: The open ``xarray.Dataset``.
        da: The elevation (or depth) ``DataArray``.
        lat_name: Name of the latitude coordinate.
        lon_name: Name of the longitude coordinate.
        var: Name of the elevation or depth variable.
        lat: Latitude grid values.
        lon: Longitude grid values.
        positive_up: ``True`` if the variable is an elevation (negative
            below sea level), as in GEBCO.
    """

    _BATCH = 500  # positions per xarray lookup, to bound memory for long lists

    def __init__(self, path: str | Path, var: str | None = None, elevation_positive_up: bool = True):
        """Open a bathymetry grid.

        Args:
            path: Path of the netCDF file.
            var: Name of the elevation or depth variable. If ``None``, the first
                of ``elevation``, ``z``, ``depth``, ``bathymetry`` or ``topo``
                that exists is used.
            elevation_positive_up: ``True`` if the variable is an elevation
                (negative at sea), ``False`` if it is a depth (positive at sea).

        Raises:
            ImportError: If ``xarray`` is not installed.
            ValueError: If the latitude, longitude or elevation variable cannot
                be identified, or latitude and longitude are not dimensions of
                the elevation variable.
        """
        try:
            import xarray as xr
        except ImportError as exc:
            raise ImportError(
                "NetCDFBathymetry needs the 'xarray' package and a netCDF engine: pip install xarray netCDF4"
            ) from exc

        self._xr = xr
        self.ds = xr.open_dataset(path)
        names = {str(n).lower(): str(n) for n in self.ds.variables}

        def pick(opts):
            return next((names[o] for o in opts if o in names), None)

        lat_name = pick(("lat", "latitude", "y"))
        lon_name = pick(("lon", "longitude", "x"))
        var_name = var or pick(("elevation", "z", "depth", "bathymetry", "topo"))
        if lat_name is None or lon_name is None or var_name is None:
            raise ValueError(f"Cannot identify lat/lon/elevation variables in {path}: {list(names.values())}")
        self.da = self.ds[var_name]
        if lat_name not in self.da.dims or lon_name not in self.da.dims:
            raise ValueError(f"{var_name} must have {lat_name} and {lon_name} as dimensions; it has {self.da.dims}")
        self.lat_name: str = lat_name
        self.lon_name: str = lon_name
        self.var: str = var_name
        self.lat = np.asarray(self.ds[lat_name].values, dtype=float)
        self.lon = np.asarray(self.ds[lon_name].values, dtype=float)
        self.positive_up = elevation_positive_up
        # half a grid cell, so a position on the outer edge of the grid still counts as inside it
        self._half_lat = float(np.abs(np.diff(self.lat)).mean()) / 2 if len(self.lat) > 1 else 0.0
        self._half_lon = float(np.abs(np.diff(self.lon)).mean()) / 2 if len(self.lon) > 1 else 0.0

    def close(self) -> None:
        """Close the underlying file."""
        self.ds.close()

    def __enter__(self) -> NetCDFBathymetry:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def depths_at(self, lats: Sequence[float], lons: Sequence[float]) -> list[float | None]:
        """Return the water depth at each of a list of positions.

        Each position is matched to its nearest grid cell in one vectorised
        xarray lookup (in batches of 500). Longitudes are shifted by 360
        degrees if the grid uses 0 to 360.

        Args:
            lats: Latitudes in degrees.
            lons: Longitudes in degrees, matching ``lats`` index for index.

        Returns:
            Water depth in metres, positive down (zero or less on land), for
            each position. ``None`` for a position that is outside the grid,
            not finite, or on a masked grid cell.

        Raises:
            ValueError: If ``lats`` and ``lons`` differ in length.
        """
        lat_arr = np.asarray(lats, dtype=float)
        lon_arr = np.asarray(lons, dtype=float)
        if lat_arr.shape != lon_arr.shape:
            raise ValueError("lats and lons must have the same length")
        if self.lon.max() > 180:
            lon_arr = np.where(lon_arr < 0, lon_arr + 360.0, lon_arr)
        with np.errstate(invalid="ignore"):  # NaN positions compare False, so they are not "inside"
            inside = (
                (lat_arr >= self.lat.min() - self._half_lat)
                & (lat_arr <= self.lat.max() + self._half_lat)
                & (lon_arr >= self.lon.min() - self._half_lon)
                & (lon_arr <= self.lon.max() + self._half_lon)
            )
        out: list[float | None] = [None] * len(lat_arr)
        idx = np.flatnonzero(inside)
        for start in range(0, len(idx), self._BATCH):
            chunk = idx[start : start + self._BATCH]
            picked = self.da.sel(
                {
                    self.lat_name: self._xr.DataArray(lat_arr[chunk], dims="point"),
                    self.lon_name: self._xr.DataArray(lon_arr[chunk], dims="point"),
                },
                method="nearest",
            )
            for k, v in zip(chunk, np.asarray(picked.values, dtype=float), strict=True):
                if np.isfinite(v):
                    out[int(k)] = -float(v) if self.positive_up else float(v)
        return out

    def depth_at(self, lat: float, lon: float) -> float | None:
        """Return the water depth at the grid cell nearest a position.

        Args:
            lat: Latitude in degrees.
            lon: Longitude in degrees.

        Returns:
            Water depth in metres, positive down (zero or less on land), or
            ``None`` if the position is outside the grid or the grid cell is
            masked. Tests that need a depth skip such positions.
        """
        return self.depths_at([lat], [lon])[0]


# --------------------------------------------------------------------------- #
# Test 1.1  Platform Identification
# --------------------------------------------------------------------------- #
def test_1_1_platform_id(stations: Sequence[Station], cfg: Stage1Config) -> None:
    """Run test 1.1, Platform Identification.

    A platform passes if it is in :attr:`Stage1Config.known_platforms`. An
    unknown platform that occurs more than once in the run is accepted and
    noted (rules 1.1.5 and 1.1.6 of the manual); one that occurs only once
    fails and gets :attr:`Stage1Config.unknown_platform_flag`. A missing
    platform gets flag 9.

    Args:
        stations: All stations of the run (the test needs the whole set).
        cfg: Test settings.
    """
    known = {_norm(p) for p in cfg.known_platforms}
    counts = Counter(s.platform_key for s in stations if s.platform_key)
    for s in stations:
        s.performed |= Test.PLATFORM_ID
        key = s.platform_key
        if key is None:
            s.flags["platform"] = QF.MISSING
            s.fail(Test.PLATFORM_ID, "platform identifier missing")
        elif key in known:
            s.flags["platform"] = QF.GOOD
        elif counts[key] > 1:
            # Rule 1.1.5/1.1.6: repeated in the file -> accepted, added to known list
            known.add(key)
            s.flags["platform"] = QF.GOOD
            s.note(f"[PLATFORM_ID] '{s.platform}' not in known list but occurs {counts[key]}x in file; accepted")
        else:
            s.flags["platform"] = cfg.unknown_platform_flag
            s.fail(Test.PLATFORM_ID, f"unknown, single-occurrence platform '{s.platform}'")


# --------------------------------------------------------------------------- #
# Test 1.2  Impossible Date and Time
# --------------------------------------------------------------------------- #
def test_1_2_date_time(s: Station, cfg: Stage1Config) -> None:
    """Run test 1.2, Impossible Date/Time.

    Year, month, day, hour and minute are checked in that order. A part
    fails if it is outside its range, if an earlier part is already
    erroneous, or if the date and time are in the future. Hour 24 and
    minute 60 are rolled over first when
    :attr:`Stage1Config.apply_rollover` is set; changed parts get flag 5 and
    their originals are stored in :attr:`Station.original`.

    Args:
        s: Station to test; its flags and messages are updated.
        cfg: Test settings.
    """
    s.performed |= Test.DATE_TIME
    o = s.obs
    if not o or any(o.get(k) is None for k in DATE_PARTS):
        for k in DATE_PARTS:
            s.flags[k] = QF.MISSING
        s.fail(Test.DATE_TIME, "date/time missing or unparseable")
        return

    now = cfg.now_utc()
    f = s.flags
    changed: set[str] = set()

    # Deterministic corrections: hour 24 -> 0 (+1 day), minute 60 -> 0 (+1 hour)
    if cfg.apply_rollover and (o["hour"] == 24 or o["minute"] == 60):
        y, m, d = o["year"], o["month"], o["day"]
        if (
            1 <= y <= 9999
            and 1 <= m <= 12
            and 1 <= d <= _days_in_month(y, m)
            and 0 <= o["hour"] <= 24
            and 0 <= o["minute"] <= 60
        ):
            new = datetime(y, m, d) + timedelta(hours=o["hour"], minutes=o["minute"])
            for k, v in zip(DATE_PARTS, (new.year, new.month, new.day, new.hour, new.minute), strict=True):
                if o[k] != v:
                    s.original[k] = o[k]
                    o[k] = v
                    changed.add(k)
            s.note(
                "[DATE_TIME] 24:00 / minute 60 rolled over; changed: "
                + ", ".join(k for k in DATE_PARTS if k in changed)
            )

    y, m, d, h, mi = (o[k] for k in DATE_PARTS)
    failed = False

    def good(k):
        f[k] = QF.CHANGED if k in changed else QF.GOOD

    def bad(k, why):
        nonlocal failed
        f[k] = cfg.date_flag
        failed = True
        s.note(f"[DATE_TIME] {k}={o[k]}: {why}")

    # Part 1 -- year not in the future
    good("year") if y <= now.year else bad("year", "year is in the future")

    # Part 2 -- month 1..12, year not erroneous, (year, month) not in the future
    if not 1 <= m <= 12:
        bad("month", "month outside 1-12")
    elif f["year"] in BAD:
        bad("month", "year flagged erroneous")
    elif (y, m) > (now.year, now.month):
        bad("month", "year/month in the future")
    else:
        good("month")

    # Part 3 -- day valid for month/year, earlier flags ok, not in the future
    if not 1 <= d <= _days_in_month(y, m):
        bad("day", "day not possible for this month/year")
    elif f["year"] in BAD or f["month"] in BAD:
        bad("day", "year or month flagged erroneous")
    elif (y, m, d) > (now.year, now.month, now.day):
        bad("day", "date is in the future")
    elif cfg.realtime and cfg.old_realtime_flag is not None and now - datetime(y, m, d) > timedelta(days=30):
        f["day"] = cfg.old_realtime_flag
        failed = True
        s.note("[DATE_TIME] real-time observation older than 30 days")
    else:
        good("day")

    # Part 4 -- hour 0..23
    if not 0 <= h <= 23:
        bad("hour", "hour outside 0-23")
    elif s.any_bad("year", "month", "day"):
        bad("hour", "year/month/day flagged erroneous")
    elif (y, m, d, h) > (now.year, now.month, now.day, now.hour):
        bad("hour", "date/hour in the future")
    else:
        good("hour")

    # Part 5 -- minute 0..59
    if not 0 <= mi <= 59:
        bad("minute", "minute outside 0-59")
    elif s.any_bad("year", "month", "day", "hour"):
        bad("minute", "an earlier date/time part is flagged erroneous")
    elif (y, m, d, h, mi) > (now.year, now.month, now.day, now.hour, now.minute):
        bad("minute", "date/time is in the future")
    else:
        good("minute")

    if failed:
        s.failed |= Test.DATE_TIME


# --------------------------------------------------------------------------- #
# Test 1.3  Impossible Location
# --------------------------------------------------------------------------- #
def test_1_3_location(s: Station, cfg: Stage1Config) -> None:
    """Run test 1.3, Impossible Location.

    Latitude must be within +/-90 and longitude within +/-180. Longitudes
    from 180 to 360 are converted first when
    :attr:`Stage1Config.convert_lon_0_360` is set. Missing values get
    flag 9.

    Args:
        s: Station to test; its flags and messages are updated.
        cfg: Test settings.
    """
    s.performed |= Test.LOCATION

    if s.latitude is None:
        s.flags["latitude"] = QF.MISSING
        s.fail(Test.LOCATION, "latitude missing")
    elif not -90.0 <= s.latitude <= 90.0:
        s.flags["latitude"] = cfg.position_flag
        s.fail(Test.LOCATION, f"latitude {s.latitude} outside +/-90")
    else:
        s.flags["latitude"] = QF.GOOD

    if s.longitude is not None and cfg.convert_lon_0_360 and 180.0 < s.longitude <= 360.0:
        s.original["longitude"] = s.longitude
        s.longitude = round(s.longitude - 360.0, 6)
        s.note(f"[LOCATION] longitude converted from {s.original['longitude']} to {s.longitude}")

    if s.longitude is None:
        s.flags["longitude"] = QF.MISSING
        s.fail(Test.LOCATION, "longitude missing")
    elif not -180.0 <= s.longitude <= 180.0:
        s.flags["longitude"] = cfg.position_flag
        s.fail(Test.LOCATION, f"longitude {s.longitude} outside +/-180")
    else:
        s.flags["longitude"] = QF.GOOD


# --------------------------------------------------------------------------- #
# Tests 1.4 (Position on Land) and 1.6 (Impossible Sounding)
# --------------------------------------------------------------------------- #
def _sounding_value(s: Station, cfg: Stage1Config) -> float | None:
    """Return a station's sounding, or ``None`` if it is missing.

    Args:
        s: Station.
        cfg: Test settings, used for :attr:`Stage1Config.sounding_null_values`.
    """
    v = s.sounding
    if v is None or any(abs(v - n) < 1e-9 for n in cfg.sounding_null_values):
        return None
    return v


def _sounding_agrees(sounding: float, depth: float, tol: float) -> bool:
    """Check a sounding against the bathymetry.

    Args:
        sounding: Sounding in metres.
        depth: Bathymetry depth in metres.
        tol: Allowed relative difference (0.10 means 10%).

    Returns:
        ``True`` if the sounding is within ``tol`` of the bathymetry.
    """
    return abs(sounding - depth) <= tol * depth


def test_1_4_position_on_land(s: Station, cfg: Stage1Config) -> None:
    """Run test 1.4, Position on Land.

    Skipped if there is no bathymetry or the position is unusable. A depth of
    zero or less fails with :attr:`Stage1Config.land_flag`. At sea, the
    sounding is compared with the bathymetry as in rules 1.4.3 to 1.4.12 of
    the manual (the same comparison as test 1.6).

    Args:
        s: Station to test; its flags and messages are updated.
        cfg: Test settings.
    """
    lat, lon = s.latitude, s.longitude
    if cfg.bathymetry is None or lat is None or lon is None or not s.position_ok:
        return  # rule 1.4.1: skip
    depth = cfg.bathymetry.depth_at(lat, lon)
    if depth is None or not math.isfinite(depth):
        return  # no bathymetry here
    s.performed |= Test.ON_LAND

    if depth <= 0:  # on land (rules 1.4.16-24)
        s.flags["latitude"] = s.flags["longitude"] = cfg.land_flag
        s.fail(Test.ON_LAND, f"position ({s.latitude:.4f}, {s.longitude:.4f}) is on land (bathymetry {depth:.0f} m)")
        return

    snd = _sounding_value(s, cfg)  # at sea (rules 1.4.3-12)
    if snd is None or s.flags["sounding"] in BAD:
        return
    if not _sounding_agrees(snd, depth, cfg.sounding_tolerance):
        s.flags["sounding"] = cfg.sounding_flag
        s.fail(Test.ON_LAND, f"sounding {snd:.0f} m vs bathymetry {depth:.0f} m (> {cfg.sounding_tolerance:.0%} apart)")


def test_1_6_impossible_sounding(s: Station, cfg: Stage1Config) -> None:
    """Run test 1.6, Impossible Sounding.

    Compares the header sounding with the bathymetry at the station's
    position. The flag is set to 1 when they agree and to
    :attr:`Stage1Config.sounding_flag` when they do not. If there is nothing
    to compare (no sounding, an unusable position, or no bathymetry value at
    the position, including a position outside the grid) the flag stays at 0
    and the test is not counted as performed.

    Args:
        s: Station to test; its flags and messages are updated.
        cfg: Test settings.
    """
    if cfg.bathymetry is None:
        return
    snd = _sounding_value(s, cfg)
    if snd is None:
        return  # rules 1.6.2 / 1.6.4
    lat, lon = s.latitude, s.longitude
    if lat is None or lon is None or not s.position_ok:
        s.flags["sounding"] = QF.UNCHECKED  # rule 1.6.3
        return
    depth = cfg.bathymetry.depth_at(lat, lon)
    if depth is None or not math.isfinite(depth) or depth <= 0:
        s.flags["sounding"] = QF.UNCHECKED  # on land / no data: nothing to compare
        return
    s.performed |= Test.SOUNDING
    if _sounding_agrees(snd, depth, cfg.sounding_tolerance):
        s.flags["sounding"] = QF.GOOD
    else:
        s.flags["sounding"] = cfg.sounding_flag
        s.fail(
            Test.SOUNDING, f"sounding {snd:.0f} m vs bathymetry {depth:.0f} m (> {cfg.sounding_tolerance:.0%} apart)"
        )


# --------------------------------------------------------------------------- #
# Test 1.5  Impossible Speed
# --------------------------------------------------------------------------- #
def test_1_5_impossible_speed(stations: Sequence[Station], cfg: Stage1Config) -> None:
    """Run test 1.5, Impossible Speed.

    Stations are grouped by platform and sorted by time. Each station is
    compared with the most recent earlier station that has not itself
    failed, using the end of that cast when it is usable. A speed above the
    platform's limit flags the later station's position with
    :attr:`Stage1Config.speed_flag`. Platforms without a limit are not
    tested.

    Args:
        stations: All stations of the run.
        cfg: Test settings.
    """
    groups: dict[str, list[Station]] = defaultdict(list)
    for s in stations:
        if s.platform_key:
            groups[s.platform_key].append(s)

    table = {_norm(k): v for k, v in cfg.max_speed_knots.items()}
    for key, grp in groups.items():
        vmax = table.get(key, cfg.default_max_speed_knots)
        if vmax is None:
            continue  # rule 1.5.2: platform not in table
        # (time, latitude, longitude, station) for every usable station of this platform
        eligible: list[tuple[datetime, float, float, Station]] = []
        for g in grp:  # rules 1.5.3-4
            when = g.when
            if g.position_ok and when is not None and g.latitude is not None and g.longitude is not None:
                eligible.append((when, g.latitude, g.longitude, g))
        eligible.sort(key=lambda e: e[0])
        if len(eligible) < 2:  # rule 1.5.1
            continue

        ref = eligible[0][3]
        for when, lat, lon, s in eligible[1:]:
            s.performed |= Test.SPEED
            # use the end of the previous cast if it is usable, else its start
            ref_when = ref.when
            assert ref_when is not None and ref.latitude is not None and ref.longitude is not None
            lat0, lon0, t0 = ref.latitude, ref.longitude, ref_when
            if (
                ref.end_latitude is not None
                and ref.end_longitude is not None
                and (e := _to_datetime(ref.end_obs)) is not None
                and t0 <= e <= when
            ):
                lat0, lon0, t0 = ref.end_latitude, ref.end_longitude, e
            dist = haversine_m(lat0, lon0, lat, lon)
            dt = (when - t0).total_seconds()
            speed_kn = math.inf if dt <= 0 and dist > 0 else (0.0 if dist == 0 else dist / dt / 0.514444)
            if speed_kn > vmax:
                # the later station is assumed to be the suspect one
                s.flags["latitude"] = s.flags["longitude"] = cfg.speed_flag
                shown = "infinite" if math.isinf(speed_kn) else format(speed_kn, ".1f")
                s.fail(
                    Test.SPEED,
                    f"{shown} kn from {ref.label} exceeds {vmax:.1f} kn "
                    f"({dist / 1000:.1f} km in {dt / 3600:.2f} h); position or date/time suspect",
                )
                # keep the previous good reference so one bad cast doesn't poison the next
            else:
                ref = s


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def run_stage1(stations: Sequence[Station], cfg: Stage1Config) -> pd.DataFrame:
    """Run tests 1.1 to 1.6 in the manual's order.

    Args:
        stations: Stations to test. Their flags, messages and QCP / QCF
            masks are updated in place.
        cfg: Test settings.

    Returns:
        One row per station, from :func:`results_frame`.
    """
    speed_platforms = {_norm(k) for k in cfg.max_speed_knots}
    for s in stations:  # which tests are enabled for this station
        s.ran = Test.PLATFORM_ID | Test.DATE_TIME | Test.LOCATION
        if cfg.bathymetry is not None:
            s.ran |= Test.ON_LAND | Test.SOUNDING
        if s.platform_key and (s.platform_key in speed_platforms or cfg.default_max_speed_knots is not None):
            s.ran |= Test.SPEED
    test_1_1_platform_id(stations, cfg)
    for s in stations:
        test_1_2_date_time(s, cfg)
    for s in stations:
        test_1_3_location(s, cfg)
    for s in stations:
        test_1_4_position_on_land(s, cfg)
    test_1_5_impossible_speed(stations, cfg)
    for s in stations:
        test_1_6_impossible_sounding(s, cfg)
    return results_frame(stations)


def results_frame(stations: Sequence[Station]) -> pd.DataFrame:
    """Summarise Stage 1 results in a table.

    Args:
        stations: Stations that have been through :func:`run_stage1`.

    Returns:
        A DataFrame with one row per station: identification, date/time,
        position, sounding, one ``qf_<field>`` column per flag, the QCP and
        QCF hexadecimal codes, the names of the failed tests and the
        messages.
    """
    rows = []
    for s in stations:
        row = {
            "file": Path(s.source).name,
            "station": s.label,
            "platform": s.platform,
            "datetime": s.when,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "sounding": s.sounding,
        }
        row.update({f"qf_{k}": int(s.flags[k]) for k in FLAG_KEYS})
        row["QCP"], row["QCF"] = s.qcp_hex, s.qcf_hex
        row["failed_tests"] = ",".join(str(t.name) for t in Test if t and t in s.failed)
        row["messages"] = " | ".join(s.messages)
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# datashop_toolbox adapter -- the ONLY place that knows toolbox attribute names
# --------------------------------------------------------------------------- #
# (section attribute on the OdfHeader object, field name within that section)
ODF_FIELD_MAP = {
    "platform": ("cruise_header", "platform"),
    "cruise_number": ("cruise_header", "cruise_number"),
    "data_type": ("event_header", "data_type"),
    "event_number": ("event_header", "event_number"),
    "start_date_time": ("event_header", "start_date_time"),
    "end_date_time": ("event_header", "end_date_time"),
    "latitude": ("event_header", "initial_latitude"),
    "longitude": ("event_header", "initial_longitude"),
    "end_latitude": ("event_header", "end_latitude"),
    "end_longitude": ("event_header", "end_longitude"),
    "sounding": ("event_header", "sounding"),
}


def _fetch(odf: Any, key: str) -> Any:
    """Read one header field from a toolbox object.

    The field is looked up through :data:`ODF_FIELD_MAP`. Plain attributes,
    ``get_<name>()`` accessors and dict-like headers are all accepted.

    Args:
        odf: An :class:`~datashop_toolbox.odfhdr.OdfHeader`.
        key: Key of :data:`ODF_FIELD_MAP`.

    Returns:
        The field value (strings are stripped of quotes), or ``None`` if the
        section or field does not exist.
    """
    section_name, field_name = ODF_FIELD_MAP[key]
    section = getattr(odf, section_name, None)
    if section is None:
        return None
    if isinstance(section, Mapping):
        return section.get(field_name) or section.get(field_name.upper())
    val = getattr(section, field_name, None)
    if val is None and callable(getter := getattr(section, f"get_{field_name}", None)):
        val = getter()
    return val.strip().strip("'\"") if isinstance(val, str) else val


def read_odf_file(path: str | Path) -> Any:
    """Read one ODF file with ``datashop_toolbox``.

    Args:
        path: Path of the ODF file.

    Returns:
        The populated :class:`~datashop_toolbox.odfhdr.OdfHeader`.

    Raises:
        ImportError: If ``OdfHeader`` cannot be imported from
            ``datashop_toolbox.odfhdr``.
    """
    try:
        from datashop_toolbox.odfhdr import OdfHeader
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Could not import OdfHeader from datashop_toolbox.odfhdr; adjust this import to "
            "match your installed version of the toolbox."
        ) from e
    odf = OdfHeader()
    result = odf.read_odf(Path(path))  # the toolbox asserts a pathlib.Path, not a str
    return result if result is not None and hasattr(result, "event_header") else odf


ODF_NULL_POSITIONS = (-99.0, -99.9, -999.0, -999.9)


def _pos(x: Any) -> float | None:
    """Convert a position to a float, treating ODF null markers as missing.

    Args:
        x: Latitude or longitude value or text.

    Returns:
        The value as a ``float``, or ``None`` if it is missing, not numeric,
        or one of :data:`ODF_NULL_POSITIONS`.
    """
    v = _to_float(x)
    return None if v is None or any(abs(v - n) < 1e-9 for n in ODF_NULL_POSITIONS) else v


def station_from_odf(odf: Any, source: str | Path = "") -> Station:
    """Build a :class:`Station` from a toolbox object.

    Args:
        odf: A populated :class:`~datashop_toolbox.odfhdr.OdfHeader`.
        source: Path of the file the object was read from.

    Returns:
        The station, with all flags unchecked.
    """

    def g(k):
        return _fetch(odf, k)

    return Station(
        source=str(source),
        platform=g("platform"),
        cruise_number=g("cruise_number"),
        event_number=g("event_number"),
        data_type=g("data_type"),
        obs=parse_datetime_parts(g("start_date_time")),
        end_obs=parse_datetime_parts(g("end_date_time")),
        latitude=_pos(g("latitude")),
        longitude=_pos(g("longitude")),
        end_latitude=_pos(g("end_latitude")),
        end_longitude=_pos(g("end_longitude")),
        sounding=_to_float(g("sounding")),
        odf=odf,
    )


_RAW_KEYS = {
    "PLATFORM": "platform",
    "CRUISE_NUMBER": "cruise_number",
    "DATA_TYPE": "data_type",
    "EVENT_NUMBER": "event_number",
    "START_DATE_TIME": "start",
    "END_DATE_TIME": "end",
    "INITIAL_LATITUDE": "latitude",
    "INITIAL_LONGITUDE": "longitude",
    "END_LATITUDE": "end_latitude",
    "END_LONGITUDE": "end_longitude",
    "SOUNDING": "sounding",
}


def station_from_raw_text(path: str | Path) -> Station:
    """Build a :class:`Station` from the raw header text of an ODF file.

    Used when the toolbox refuses a file, because its validators reject
    impossible values such as ``31-FEB-2008`` or ``24:00:00`` in
    ``START_DATE_TIME``. Only the fields Stage 1 needs are read, so test 1.2
    can still see and flag the bad value.

    Args:
        path: Path of the ODF file.

    Returns:
        The station, with :attr:`Station.odf` set to ``None``. A message
        records that the toolbox rejected the file.
    """
    found: dict[str, str] = {}
    for line in Path(path).read_text(errors="replace").splitlines():
        if "-- DATA --" in line:
            break
        m = re.match(r"^\s*([A-Z_0-9]+)\s*=\s*(.*?),?\s*$", line)
        if m and m.group(1) in _RAW_KEYS and _RAW_KEYS[m.group(1)] not in found:
            found[_RAW_KEYS[m.group(1)]] = m.group(2).strip().strip("'\"")
    g = found.get
    st = Station(
        source=str(path),
        platform=g("platform"),
        cruise_number=g("cruise_number"),
        event_number=g("event_number"),
        data_type=g("data_type"),
        obs=parse_datetime_parts(g("start")),
        end_obs=parse_datetime_parts(g("end")),
        latitude=_pos(g("latitude")),
        longitude=_pos(g("longitude")),
        end_latitude=_pos(g("end_latitude")),
        end_longitude=_pos(g("end_longitude")),
        sounding=_to_float(g("sounding")),
        odf=None,
    )
    if st.obs is None and g("start"):
        st.note(f"[DATE_TIME] START_DATE_TIME '{g('start')}' could not be parsed")
    st.note("[READ] toolbox rejected this file; header fields read from raw text, no profile data")
    return st


def load_stations(folder: str | Path, pattern: str = "*.ODF") -> list[Station]:
    """Read a folder of ODF files into stations.

    Each file is read with the toolbox. If that fails, the header is read
    from the raw text instead, and a warning is logged.

    Args:
        folder: Folder containing the ODF files.
        pattern: Glob pattern for the files. If nothing matches, the
            lower-case pattern is tried.

    Returns:
        One station per readable file, in file-name order.
    """
    files = sorted(Path(folder).glob(pattern)) or sorted(Path(folder).glob(pattern.lower()))
    stations = []
    for fp in files:
        try:
            stations.append(station_from_odf(read_odf_file(fp), fp))
        except Exception as exc:
            why = next(
                (
                    ln.strip()
                    for ln in str(exc).splitlines()
                    if "error" in ln.lower() and "validation error" not in ln.lower()
                ),
                type(exc).__name__,
            )
            log.warning("Toolbox could not read %s (%s); reading header from raw text", fp.name, why[:110])
            try:
                stations.append(station_from_raw_text(fp))
            except Exception as exc2:
                log.error("Could not read %s at all: %s", fp.name, exc2)
    log.info("Loaded %d of %d ODF files", len(stations), len(files))
    return stations


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #
def main() -> None:
    """Run Stage 1 from the command line and write a CSV summary."""
    ap = argparse.ArgumentParser(description="GTSPP Stage 1 QC on a folder of ODF files")
    ap.add_argument("folder", help="folder containing .ODF files")
    ap.add_argument("--pattern", default="*.ODF")
    ap.add_argument(
        "--platforms",
        help="text file: one known platform identifier per line (default: the toolbox lookups/platforms.csv)",
    )
    ap.add_argument("--bathy", help="GEBCO/ETOPO netCDF file (enables tests 1.4 and 1.6)")
    ap.add_argument(
        "--max-speed-knots", type=float, help="speed limit in knots for platforms that are not in the lookup table"
    )
    ap.add_argument("--realtime", action="store_true")
    ap.add_argument("--out", default="gtspp_stage1_results.csv")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cfg = Stage1Config(realtime=args.realtime, default_max_speed_knots=args.max_speed_knots)
    if args.platforms:
        cfg.known_platforms = {ln.strip() for ln in Path(args.platforms).read_text().splitlines() if ln.strip()}
    if args.bathy:
        cfg.bathymetry = NetCDFBathymetry(args.bathy)

    stations = load_stations(args.folder, args.pattern)
    df = run_stage1(stations, cfg)
    df.to_csv(args.out, index=False)
    n_fail = int((df["QCF"] != "0").sum())
    print(f"{len(df)} stations, {n_fail} with at least one Stage 1 failure -> {args.out}")
    if n_fail:
        print(df.loc[df["QCF"] != "0", ["station", "QCP", "QCF", "failed_tests", "messages"]].to_string(index=False))


if __name__ == "__main__":
    main()
