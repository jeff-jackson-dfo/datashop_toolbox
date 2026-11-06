"""
gtspp_stage2.py
---------------
GTSPP Stage 2 (profile) quality control for ODF files.

Implements the twelve Stage 2 tests of the GTSPP Real-Time Quality Control
Manual (IOC Manuals and Guides 22, first revised edition, 2010) for CTD
profiles read with :class:`~datashop_toolbox.odfhdr.OdfHeader`. It builds on
``gtspp_stage1.py``, which must be importable alongside it.

  Tests (GTSPP test index in parentheses)
  ───────────────────────────────────────
  • 2.1   Global Impossible Parameter Values   (64)
  • 2.2   Regional Impossible Parameter Values (128)
  • 2.3   Increasing Depth                     (256)
  • 2.4   Profile Envelope                     (512)
  • 2.5   Constant Profile                     (1024)
  • 2.6   Freezing Point                       (2048)
  • 2.7   Spike                                (4096)
  • 2.8   Top and Bottom Spike                 (8192)
  • 2.9   Gradient                             (16384)
  • 2.10  Density Inversion                    (32768)
  • 2.11  Bottom                               (8388608)
  • 2.12  Temperature Inversion                (16777216)

  Sources and assumptions
  ───────────────────────
  • Tests 2.1 to 2.5 follow the full rules of the manual.
  • Tests 2.6 to 2.12 follow the GTSPP test descriptions published by NOAA
    NCEI, which give thresholds for 2.7 to 2.10 but not every rule. Choices
    that go beyond that text are marked ``ASSUMPTION`` in the code: the
    density comparison pressure (2.10), the bottom tolerance (2.11) and the
    inversion definition (2.12, off until an amplitude is set).

  Flag policy
  ───────────
  • A test only ever makes a flag worse. A value with flag 0 that passes
    becomes 1. Values already flagged erroneous or missing are ignored by
    later tests.
  • After the tests, every remaining unflagged value becomes 1 and derived
    parameters (PSAL, POTM, SIGP, DOXY ...) inherit the worse flag of the
    parameters they are computed from (see :data:`DERIVED_FROM`).
  • Nothing is written to the ODF here; ``gtspp_odf_output.py`` does that.

  Shared infrastructure
  ─────────────────────
  • Test2                – test indices
  • Stage2Config         – limits, thresholds, flags to assign, options
  • Profile              – one profile's values, flags and failure reasons
  • profile_from_station – build a profile from a Stage 1 station
  • run_stage2           – run tests 2.1 to 2.12 and summarise the results
  • flagged_values       – list every doubtful or erroneous value

  Usage
  ─────
      stations = load_stations("odf_folder")
      profiles = load_profiles(stations)
      summary = run_stage2(profiles, Stage2Config())
      details = flagged_values(profiles)

  From the command line (runs both stages and writes CSV files):

      python gtspp_stage2.py odf_folder --out-prefix cruise
"""

from __future__ import annotations

import argparse
import logging
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import IntFlag
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:  # inside the datashop_toolbox package ...
    from datashop_toolbox.gtspp_stage1 import (
        QF,
        Bathymetry,
        NetCDFBathymetry,
        Stage1Config,
        Station,
        load_stations,
        run_stage1,
    )
except ImportError:  # ... or side by side in a plain folder
    from gtspp_stage1 import QF, Bathymetry, NetCDFBathymetry, Stage1Config, Station, load_stations, run_stage1

log = logging.getLogger("gtspp_stage2")


class Test2(IntFlag):
    """Stage 2 test indices, as used in the GTSPP QCP / QCF bit masks.

    Attributes:
        NONE: No test.
        GLOBAL_RANGE: Test 2.1, Global Impossible Parameter Values (64).
        REGIONAL_RANGE: Test 2.2, Regional Impossible Parameter Values (128).
        INCREASING_DEPTH: Test 2.3, Increasing Depth (256).
        PROFILE_ENVELOPE: Test 2.4, Profile Envelope (512).
        CONSTANT_PROFILE: Test 2.5, Constant Profile (1024).
        FREEZING_POINT: Test 2.6, Freezing Point (2048).
        SPIKE: Test 2.7, Spike (4096).
        TOP_BOTTOM_SPIKE: Test 2.8, Top and Bottom Spike (8192).
        GRADIENT: Test 2.9, Gradient (16384).
        DENSITY_INVERSION: Test 2.10, Density Inversion (32768).
        BOTTOM: Test 2.11, Bottom (8388608).
        TEMPERATURE_INVERSION: Test 2.12, Temperature Inversion (16777216).
    """

    NONE = 0
    GLOBAL_RANGE = 64
    REGIONAL_RANGE = 128
    INCREASING_DEPTH = 256
    PROFILE_ENVELOPE = 512
    CONSTANT_PROFILE = 1024
    FREEZING_POINT = 2048
    SPIKE = 4096
    TOP_BOTTOM_SPIKE = 8192
    GRADIENT = 16384
    DENSITY_INVERSION = 32768
    BOTTOM = 8388608
    TEMPERATURE_INVERSION = 16777216


BAD_I = (int(QF.ERRONEOUS), int(QF.MISSING))
NOT_GOOD_I = (int(QF.DOUBTFUL), int(QF.ERRONEOUS), int(QF.MISSING))
_RANK = {0: 0, 1: 1, 2: 2, 5: 2, 3: 3, 4: 4, 9: 5}

TEMP_CODES = ("TEMP", "TE90", "TE68")
SAL_CODES = ("PSAL",)


def kind_of(code: str) -> str | None:
    """Classify a parameter code.

    Args:
        code: Four-character GF3 parameter code, for example ``"TEMP"``.

    Returns:
        ``"temperature"``, ``"salinity"``, ``"pressure"`` or ``"depth"``, or
        ``None`` for any other parameter.
    """
    if code in TEMP_CODES:
        return "temperature"
    if code in SAL_CODES:
        return "salinity"
    if code == "PRES":
        return "pressure"
    if code == "DEPH":
        return "depth"
    return None


# --------------------------------------------------------------------------- #
# Tables from the manual
# --------------------------------------------------------------------------- #
# Table 2.1 (subset that maps cleanly onto ODF/GF3 codes; extend as needed and
# make sure your ODF units match the manual's units!)
GLOBAL_LIMITS: dict[str, tuple[float, float]] = {
    "TEMP": (-2.0, 40.0),
    "TE90": (-2.0, 40.0),
    "TE68": (-2.0, 40.0),  # degrees C
    "PSAL": (0.0, 41.0),  # psu
    "PRES": (0.0, 10000.0),  # manual lists Depth 0-10000 m; dbar ~ m
    "DEPH": (0.0, 10000.0),  # m
    "SVEL": (1425.0, 1575.0),  # m/s
    "CPHL": (0.0, 30.0),  # mg/m3
    "PHPH": (6.5, 9.0),
}
SOUNDING_LIMITS = (0.0, 10000.0)

# Table 2.4: (max depth m, Tmin, Tmax, Smin, Smax); bins are (previous max, this max]
ENVELOPE = [
    (25, -2.0, 37, 0, 41),
    (50, -2.0, 36, 0, 41),
    (100, -2.0, 36, 1, 41),
    (150, -2.0, 34, 3, 41),
    (200, -2.0, 33, 3, 41),
    (300, -2.0, 29, 3, 41),
    (400, -2.0, 27, 3, 41),
    (1100, -2.0, 27, 10, 41),
    (3000, -1.5, 18, 22, 38),
    (5500, -1.5, 7, 33, 37),
    (12000, -1.5, 4, 33, 37),
]


# Derived parameter (GF3 code) -> codes it is computed from.  Sources are matched on the same
# sensor number (SIGP_02 <- TEMP_02, PSAL_02); PRES/DEPH apply to every sensor.  Order matters:
# PSAL comes first because POTM/SIGP/DOXY are computed from it.  Edit freely; e.g. if your
# oxygen sensor 2 is computed with the primary T/S, change the DOXY rule accordingly.
DERIVED_FROM: dict[str, tuple[str, ...]] = {
    "PSAL": ("CRAT", "TEMP", "TE90", "TE68", "PRES"),
    "POTM": ("TEMP", "TE90", "TE68", "PSAL", "PRES"),
    "SIGP": ("TEMP", "TE90", "TE68", "PSAL", "PRES"),
    "SIGT": ("TEMP", "TE90", "TE68", "PSAL"),
    "SVEL": ("TEMP", "TE90", "TE68", "PSAL", "PRES"),
    "DOXY": ("OXYV", "TEMP", "TE90", "TE68", "PSAL", "PRES"),
    "DEPH": ("PRES",),
}


@dataclass
class Region:
    """A sea area with its own parameter limits (test 2.2).

    Attributes:
        name: Name of the region.
        polygon: Corner points as ``(latitude, longitude)`` pairs.
        limits: ``(minimum, maximum)`` for ``temperature``, ``salinity`` and
            ``depth``.
    """

    name: str
    polygon: list[tuple[float, float]]  # (lat, lon) vertices
    limits: dict[str, tuple[float, float]]  # temperature / salinity / depth


# Table 2.2
REGIONS = [
    Region(
        "Mediterranean Sea",
        [(30, -6), (30, 40), (40, 35), (42, 20), (50, 15), (40, 5), (30, -6)],
        {"temperature": (13.0, 40.0), "salinity": (0.0, 40.0), "depth": (0.0, 5200.0)},
    ),
    Region(
        "Red Sea",
        [(10, 40), (20, 50), (30, 30), (10, 40)],
        {"temperature": (21.7, 40.0), "salinity": (0.0, 40.0), "depth": (0.0, 3500.0)},
    ),
]


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass
class Stage2Config:
    """Settings for the Stage 2 tests.

    The manual lets an operator decide, case by case, whether a failure is
    "doubtful" (3) or "erroneous" (4). Those decisions are made here, once,
    through the ``*_flag`` attributes. The defaults follow the NCEI
    descriptions of the tests.

    Attributes:
        global_limits: ``(minimum, maximum)`` by parameter code for test 2.1.
            The units must match the manual's (for example degrees C and
            psu); check them before adding parameters.
        regions: Sea areas for test 2.2.
        envelope: Depth-dependent temperature and salinity ranges for test
            2.4, as ``(maximum depth, Tmin, Tmax, Smin, Smax)`` rows.
        range_flag: Flag for tests 2.1 and 2.2.
        depth_flag: Flag for test 2.3.
        envelope_flag: Flag for test 2.4.
        constant_flag: Flag for test 2.5.
        freezing_flag: Flag for test 2.6.
        spike_flag: Flag for tests 2.7 and 2.8.
        gradient_flag: Flag for test 2.9.
        density_flag: Flag for test 2.10.
        bottom_flag: Flag for test 2.11 (assumption).
        inversion_flag: Flag for test 2.12 (assumption).
        untested_parameters_good: If ``True``, every present value that was
            not flagged becomes 1 after the tests, including parameters no
            test examines directly. If ``False`` they stay at 0.
        inherit_derived_flags: If ``True``, derived parameters inherit the
            worse flag of their sources.
        derived_from: Which parameters each derived parameter is computed
            from (see :data:`DERIVED_FROM`).
        allow_equal_depth: Allow equal consecutive depths in test 2.3. The
            manual requires strictly increasing depths.
        digitized_at_inflection_points: Use the first form of test 2.5
            (three identical consecutive values) instead of the "selected
            depths" form (the whole profile is constant).
        freezing_method: ``"unesco83"`` for the UNESCO (1983) formula or
            ``"teos10"`` for ``gsw.t_freezing``.
        temperature_scale: Temperature scale of each temperature code,
            ``"ITS-90"`` or ``"IPTS-68"``. In GF3, ``TEMP`` is IPTS-68.
        spike_thresholds: Spike limits for ``temperature`` and ``salinity``
            (2.7).
        top_bottom_thresholds: Limits for the first and last values (2.8).
        gradient_limits: Gradient limits per unit pressure (2.9).
        density_inversion_threshold: Largest allowed density decrease with
            depth, in kg/m3 (2.10).
        bathymetry: Water-depth source for test 2.11. The test is off when
            ``None``.
        bottom_tolerance: Allowed excess of the observation depth over the
            bathymetry, as a fraction (2.11, assumption).
        inversion_layer_m: Layer thickness, in metres, searched for a
            temperature inversion (2.12).
        inversion_amplitude_c: Smallest temperature difference counted as
            an inversion. ``None`` switches test 2.12 off.
    """

    global_limits: Mapping[str, tuple] = field(default_factory=lambda: dict(GLOBAL_LIMITS))
    regions: Sequence[Region] = field(default_factory=lambda: list(REGIONS))
    envelope: Sequence[tuple] = field(default_factory=lambda: list(ENVELOPE))

    # flags assigned on failure (manual: operator picks 3 or 4; defaults follow NCEI text)
    range_flag: QF = QF.ERRONEOUS  # 2.1, 2.2
    depth_flag: QF = QF.DOUBTFUL  # 2.3
    envelope_flag: QF = QF.DOUBTFUL  # 2.4
    constant_flag: QF = QF.DOUBTFUL  # 2.5
    freezing_flag: QF = QF.ERRONEOUS  # 2.6
    spike_flag: QF = QF.DOUBTFUL  # 2.7, 2.8
    gradient_flag: QF = QF.DOUBTFUL  # 2.9
    density_flag: QF = QF.DOUBTFUL  # 2.10
    bottom_flag: QF = QF.DOUBTFUL  # 2.11   ASSUMPTION
    inversion_flag: QF = QF.DOUBTFUL  # 2.12   ASSUMPTION

    # After the tests, every value that is present and was not flagged gets 1 -- including
    # parameters no Stage 2 test examines directly (CRAT, FLOR, OXYV, POTM, SIGP ...).
    # Set False to leave those at 0 ("not quality controlled").
    untested_parameters_good: bool = True

    # Derived parameters inherit the worse (3 or 4) flag of the parameters they are computed from.
    inherit_derived_flags: bool = True
    derived_from: Mapping[str, Sequence[str]] = field(default_factory=lambda: dict(DERIVED_FROM))

    allow_equal_depth: bool = False  # 2.3: the manual requires strictly deeper
    digitized_at_inflection_points: bool = False  # 2.5: False -> "selected depths" form

    freezing_method: str = "unesco83"  # or "teos10" (gsw.t_freezing)
    # scale of each temperature code (GF3: TEMP = IPTS-68, TE90 = ITS-90; check yours)
    temperature_scale: Mapping[str, str] = field(
        default_factory=lambda: {"TE90": "ITS-90", "TEMP": "IPTS-68", "TE68": "IPTS-68"}
    )

    spike_thresholds: Mapping[str, float] = field(default_factory=lambda: {"temperature": 2.0, "salinity": 0.3})
    top_bottom_thresholds: Mapping[str, float] = field(default_factory=lambda: {"temperature": 10.0, "salinity": 5.0})
    gradient_limits: Mapping[str, float] = field(default_factory=lambda: {"temperature": 10.0, "salinity": 5.0})
    density_inversion_threshold: float = 0.05  # kg/m3: fail if rho2 - rho1 < -0.05

    bathymetry: Bathymetry | None = None  # needed for 2.11
    bottom_tolerance: float = 0.10  # ASSUMPTION: same 10% as tests 1.4/1.6
    # 2.12: NCEI text gives the 50 m layer but not the amplitude -> disabled until set
    inversion_layer_m: float = 50.0
    inversion_amplitude_c: float | None = None


# --------------------------------------------------------------------------- #
# Profile record
# --------------------------------------------------------------------------- #
@dataclass
class Profile:
    """One profile with its values, quality flags and failure reasons.

    Built by :func:`profile_from_station` from a Stage 1
    :class:`~gtspp_stage1.Station`, or by :func:`profile_from_arrays` for
    testing. Columns are named as in the ODF data section, for example
    ``TEMP_01`` or ``PSAL_02``.

    Attributes:
        source: Path of the ODF file.
        label: Short identifier of the profile.
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        sounding: Water depth in metres, or ``None``.
        values: Float array for each column, with ``NaN`` for missing values.
        flags: Integer flag array for each column.
        depth_col: Column used as depth or pressure (``PRES`` is preferred
            to ``DEPH``).
        station: The Stage 1 station this profile belongs to.
        ran: Tests that were enabled for this profile.
        performed: Tests that found data to examine (the QCP mask).
        failed: Tests that failed (the QCF mask).
        reasons: Tests that flagged each value, keyed by ``(column, row)``.
        inherited: Source columns of each inherited flag, keyed by
            ``(derived column, row)``.
        messages: Human-readable notes, each prefixed with ``[TEST_NAME]``.
    """

    source: str
    label: str
    latitude: float | None
    longitude: float | None
    sounding: float | None
    values: dict  # column -> float array (NaN = missing)
    flags: dict  # column -> int array
    depth_col: str | None = None
    station: Station | None = None
    ran: Test2 = Test2.NONE  # tests that were executed (enabled), even if no data applied
    performed: Test2 = Test2.NONE  # tests that found data to examine
    failed: Test2 = Test2.NONE
    reasons: dict = field(default_factory=dict)  # (column, index) -> [test names]
    inherited: dict = field(default_factory=dict)  # (derived column, index) -> [source columns]
    messages: list = field(default_factory=list)
    _cache: dict = field(default_factory=dict, repr=False)

    # -- structure helpers ------------------------------------------------ #
    @staticmethod
    def code(col: str) -> str:
        """Return the parameter code of a column name.

        Args:
            col: Column name such as ``"TEMP_01"``.

        Returns:
            The part before the underscore, for example ``"TEMP"``.
        """
        return col.split("_")[0]

    def cols_of(self, kind: str) -> list[str]:
        """List the columns of one kind of parameter.

        Args:
            kind: ``"temperature"``, ``"salinity"``, ``"pressure"`` or
                ``"depth"``.

        Returns:
            Matching column names, in file order.
        """
        return [c for c in self.values if kind_of(self.code(c)) == kind]

    def partner(self, col: str, kind: str) -> str | None:
        """Find the column of another kind that belongs to the same sensor.

        Args:
            col: Column name, for example ``"TEMP_02"``.
            kind: Kind of column wanted, for example ``"salinity"``.

        Returns:
            The column of that kind with the same sensor number (``PSAL_02``),
            otherwise the first column of that kind, or ``None``.
        """
        cands = self.cols_of(kind)
        suffix = col.split("_", 1)[-1]
        same = [c for c in cands if c.endswith("_" + suffix)]
        return (same or cands or [None])[0]

    @property
    def pos_ok(self) -> bool:
        """Check that the profile position can be used.

        Returns:
            ``True`` if the position is present and, when a station exists, not
            flagged erroneous or missing by Stage 1.
        """
        if self.station is not None:
            return self.station.position_ok
        return self.latitude is not None and self.longitude is not None

    def eligible(self, col: str, skip: Sequence[int] = BAD_I) -> np.ndarray:
        """Select the values that a test may use.

        Args:
            col: Column name.
            skip: Flags to exclude. The default excludes erroneous (4) and
                missing (9) values.

        Returns:
            Boolean array that is ``True`` where the value is finite and its
            flag is not in ``skip``.
        """
        v, f = self.values[col], self.flags[col]
        return np.isfinite(v) & ~np.isin(f, skip)

    # -- depth / pressure ------------------------------------------------- #
    def _gsw(self):
        """Import and return the ``gsw`` package, or ``None`` if it is missing."""
        try:
            import gsw

            return gsw
        except ImportError:
            return None

    def depth_m(self) -> np.ndarray:
        """Return the depth of each level in metres.

        Returns:
            The depth column as is, or the pressure column converted with
            ``gsw.z_from_p``. Without ``gsw``, pressure in dbar is used as an
            approximation of depth. The result is cached.
        """
        if "depth" in self._cache:
            return self._cache["depth"]
        col = self.depth_col
        out = np.full(self._n(), np.nan)
        if col:
            v = self.values[col].astype(float)
            if self.code(col) == "DEPH":
                out = v
            else:  # pressure (dbar) -> depth (m)
                gsw = self._gsw()
                lat = self.latitude if self.latitude is not None else 45.0
                out = -gsw.z_from_p(v, lat) if gsw else v
        self._cache["depth"] = out
        return out

    def pressure_dbar(self) -> np.ndarray:
        """Return the pressure of each level in decibars.

        Returns:
            The pressure column as is, or the depth column converted with
            ``gsw.p_from_z``. Without ``gsw``, depth in metres is used as an
            approximation of pressure. The result is cached.
        """
        if "pres" in self._cache:
            return self._cache["pres"]
        col = self.depth_col
        out = np.full(self._n(), np.nan)
        if col:
            v = self.values[col].astype(float)
            if self.code(col) == "PRES":
                out = v
            else:
                gsw = self._gsw()
                lat = self.latitude if self.latitude is not None else 45.0
                out = gsw.p_from_z(-v, lat) if gsw else v
        self._cache["pres"] = out
        return out

    def _n(self) -> int:
        """Return the number of levels (rows) in the profile."""
        return len(next(iter(self.values.values()))) if self.values else 0

    def t90(self, col: str, cfg: Stage2Config) -> np.ndarray:
        """Return a temperature column on the ITS-90 scale.

        Args:
            col: Temperature column name.
            cfg: Settings, used for :attr:`Stage2Config.temperature_scale`.

        Returns:
            The values, divided by 1.00024 if the column is IPTS-68.
        """
        v = self.values[col].astype(float)
        return v / 1.00024 if cfg.temperature_scale.get(self.code(col), "ITS-90") == "IPTS-68" else v

    def t68(self, col: str, cfg: Stage2Config) -> np.ndarray:
        """Return a temperature column on the IPTS-68 scale.

        Args:
            col: Temperature column name.
            cfg: Settings, used for :attr:`Stage2Config.temperature_scale`.

        Returns:
            The values, multiplied by 1.00024 if the column is ITS-90.
        """
        v = self.values[col].astype(float)
        return v if cfg.temperature_scale.get(self.code(col), "ITS-90") == "IPTS-68" else v * 1.00024

    # -- flagging --------------------------------------------------------- #
    def flag(self, col: str, idx, new: QF, test: Test2) -> None:
        """Set the flag of one or more values.

        Flags only get worse. ``GOOD`` replaces only an unchecked flag (0). A
        worse flag replaces a better one but never a flag that is already
        worse, and a missing value (9) is never changed. A failure is always
        recorded in :attr:`reasons` and :attr:`failed`, even if the flag itself
        was already as bad.

        Args:
            col: Column name.
            idx: Row index or indices.
            new: Flag to set.
            test: Test responsible, recorded as the reason for a failure.
        """
        f = self.flags[col]
        for i in np.atleast_1d(idx):
            i = int(i)
            cur = int(f[i])
            if new == QF.GOOD:
                if cur == QF.UNCHECKED:
                    f[i] = QF.GOOD
                continue
            if _RANK.get(cur, 0) < _RANK[int(new)]:
                f[i] = int(new)
            self.reasons.setdefault((col, i), []).append(test.name)
            self.failed |= test

    def note(self, msg: str) -> None:
        """Append a message to :attr:`messages`.

        Args:
            msg: Message text, conventionally prefixed with ``[TEST_NAME]``.
        """
        self.messages.append(msg)


# --------------------------------------------------------------------------- #
# 2.1 / 2.2  Impossible parameter values (global and regional)
# --------------------------------------------------------------------------- #
def _apply_range(p: Profile, col: str, lo: float, hi: float, flag: QF, test: Test2) -> None:
    """Flag the values of a column that are outside a range.

    Values outside ``[lo, hi]`` get ``flag``. Values inside it become 1 if
    they were unchecked. Missing values are left alone.

    Args:
        p: Profile to update.
        col: Column name.
        lo: Smallest allowed value.
        hi: Largest allowed value.
        flag: Flag for a value outside the range.
        test: Test responsible, recorded as the reason.
    """
    v, f = p.values[col], p.flags[col]
    m = np.isfinite(v) & (f != QF.MISSING)
    out = m & ((v > hi) | (v < lo))  # rules 2.1.1 / 2.1.16: > max or < min fails
    p.flag(col, np.flatnonzero(out), flag, test)
    p.flag(col, np.flatnonzero(m & ~out), QF.GOOD, test)


def test_2_1_global_range(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.1, Global Impossible Parameter Values.

    Each parameter in :attr:`Stage2Config.global_limits` must lie within
    its limits. The station sounding is checked against 0 to 10000 m.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    for col in p.values:
        lim = cfg.global_limits.get(p.code(col))
        if lim:
            p.performed |= Test2.GLOBAL_RANGE
            _apply_range(p, col, lim[0], lim[1], cfg.range_flag, Test2.GLOBAL_RANGE)
    if p.sounding is not None and p.station is not None:
        lo, hi = SOUNDING_LIMITS
        if not lo <= p.sounding <= hi:
            p.station.flags["sounding"] = cfg.range_flag
            p.failed |= Test2.GLOBAL_RANGE
            p.note(f"[GLOBAL_RANGE] sounding {p.sounding} outside {SOUNDING_LIMITS}")


def _in_polygon(lat: float, lon: float, poly: Sequence[tuple[float, float]]) -> bool:
    """Check whether a position is inside a polygon.

    Uses the ray-casting method on longitude and latitude.

    Args:
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        poly: Corner points as ``(latitude, longitude)`` pairs.

    Returns:
        ``True`` if the position is inside the polygon.
    """
    inside = False
    n = len(poly)
    for i in range(n):
        la1, lo1 = poly[i]
        la2, lo2 = poly[(i + 1) % n]
        if (lo1 > lon) != (lo2 > lon):
            if lat < (la2 - la1) * (lon - lo1) / (lo2 - lo1) + la1:
                inside = not inside
    return inside


def test_2_2_regional_range(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.2, Regional Impossible Parameter Values.

    If the profile lies in one of :attr:`Stage2Config.regions` (the
    Mediterranean and Red Seas in the manual), temperature, salinity and
    depth are checked against that region's limits. Profiles outside every
    region are not affected. Skipped if the position is unusable.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    if not p.pos_ok or p.latitude is None or p.longitude is None:
        return  # rule 2.2.1
    for reg in cfg.regions:
        if not _in_polygon(p.latitude, p.longitude, reg.polygon):
            continue
        p.performed |= Test2.REGIONAL_RANGE
        for kind, (lo, hi) in reg.limits.items():
            cols = p.cols_of(kind) if kind != "depth" else ([p.depth_col] if p.depth_col else [])
            for col in cols:
                _apply_range(p, col, lo, hi, cfg.range_flag, Test2.REGIONAL_RANGE)
        if p.sounding is not None and p.station is not None:
            lo, hi = reg.limits["depth"]
            if not lo <= p.sounding <= hi:
                p.station.flags["sounding"] = cfg.range_flag
                p.failed |= Test2.REGIONAL_RANGE
        p.note(f"[REGIONAL_RANGE] inside {reg.name}")


# --------------------------------------------------------------------------- #
# 2.3  Increasing depth
# --------------------------------------------------------------------------- #
def test_2_3_increasing_depth(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.3, Increasing Depth.

    Each depth must be greater than the one before it. As in the manual, the
    comparison depth moves on to the current depth even after a failure.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    col = p.depth_col
    if not col:
        return
    idx = np.flatnonzero(p.eligible(col))
    if len(idx) < 2:  # rule 2.3.1
        return
    p.performed |= Test2.INCREASING_DEPTH
    v = p.values[col]
    d1 = v[idx[0]]
    for i in idx[1:]:
        d2 = v[i]
        if d2 > d1 or (cfg.allow_equal_depth and d2 == d1):
            p.flag(col, i, QF.GOOD, Test2.INCREASING_DEPTH)
        else:
            p.flag(col, i, cfg.depth_flag, Test2.INCREASING_DEPTH)
        d1 = d2  # rules 2.3.10 / 2.3.12 / 2.3.13


# --------------------------------------------------------------------------- #
# 2.4  Global profile envelope
# --------------------------------------------------------------------------- #
def _envelope_for(depth: float, table: Sequence[tuple]):
    """Find the test 2.4 envelope for a depth.

    Args:
        depth: Depth in metres.
        table: Envelope rows, as in :attr:`Stage2Config.envelope`.

    Returns:
        The row whose depth bin contains ``depth``, or ``None`` if the depth
        is negative or deeper than the table.
    """
    prev = -math.inf
    for row in table:
        if prev < depth <= row[0] or (depth == 0 and prev == -math.inf):
            return row
        prev = row[0]
    return None


def test_2_4_profile_envelope(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.4, Profile Envelope.

    Temperature and salinity must lie within the depth-dependent ranges of
    :attr:`Stage2Config.envelope`. Levels with an unusable depth are
    skipped.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    if not p.depth_col:
        return
    z = p.depth_m()
    dep_ok = np.isfinite(z) & ~np.isin(p.flags[p.depth_col], BAD_I)
    for kind, (lo_i, hi_i) in (("temperature", (1, 2)), ("salinity", (3, 4))):
        for col in p.cols_of(kind):
            ok = p.eligible(col) & dep_ok
            if not ok.any():
                continue
            p.performed |= Test2.PROFILE_ENVELOPE
            for i in np.flatnonzero(ok):
                row = _envelope_for(z[i], cfg.envelope)
                if row is None:
                    continue
                v = p.values[col][i]
                if not row[lo_i] <= v <= row[hi_i]:
                    p.flag(col, i, cfg.envelope_flag, Test2.PROFILE_ENVELOPE)


# --------------------------------------------------------------------------- #
# 2.5  Constant profile
# --------------------------------------------------------------------------- #
def test_2_5_constant_profile(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.5, Constant Profile.

    By default a parameter fails if every usable value in the profile is
    identical. With :attr:`Stage2Config.digitized_at_inflection_points`, a
    value fails when it and both of its neighbours are identical.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    dep_ok = np.isfinite(p.values[p.depth_col]) & ~np.isin(p.flags[p.depth_col], BAD_I) if p.depth_col else True
    for col in p.values:
        if col == p.depth_col or p.code(col) not in cfg.global_limits:
            continue
        idx = np.flatnonzero(p.eligible(col) & dep_ok)
        v = p.values[col]
        if cfg.digitized_at_inflection_points:  # form 1 (rules 2.5.2-2.5.19)
            if len(idx) < 3:
                continue
            p.performed |= Test2.CONSTANT_PROFILE
            for a, b, c in zip(idx[:-2], idx[1:-1], idx[2:], strict=True):
                if v[a] == v[b] == v[c]:
                    p.flag(col, b, cfg.constant_flag, Test2.CONSTANT_PROFILE)
        else:  # form 2 (rules 2.5.20-2.5.29)
            if len(idx) < 2:
                continue
            p.performed |= Test2.CONSTANT_PROFILE
            if np.all(v[idx] == v[idx[0]]):
                p.flag(col, idx, cfg.constant_flag, Test2.CONSTANT_PROFILE)
                p.note(f"[CONSTANT_PROFILE] {col} is constant over {len(idx)} levels")


# --------------------------------------------------------------------------- #
# 2.6  Freezing point
# --------------------------------------------------------------------------- #
def freezing_point_ipts68(sal, pres_dbar):
    """Compute the freezing point of seawater (UNESCO, 1983).

    Args:
        sal: Practical salinity.
        pres_dbar: Pressure in decibars.

    Returns:
        The freezing temperature in degrees C on the IPTS-68 scale.
    """
    s = np.asarray(sal, float)
    return -0.0575 * s + 1.710523e-3 * s**1.5 - 2.154996e-4 * s**2 - 7.53e-4 * np.asarray(pres_dbar, float)


def test_2_6_freezing_point(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.6, Freezing Point.

    Temperature must not be below the freezing point for the salinity and
    pressure of the same level and sensor. Temperature is compared on the
    IPTS-68 scale for ``unesco83``, or on ITS-90 for ``teos10``. Levels
    where temperature, salinity or pressure is unusable are skipped.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    if not p.depth_col:
        return
    P = p.pressure_dbar()
    for tcol in p.cols_of("temperature"):
        scol = p.partner(tcol, "salinity")
        if scol is None:
            continue
        ok = p.eligible(tcol) & p.eligible(scol) & np.isfinite(P)
        if not ok.any():
            continue
        p.performed |= Test2.FREEZING_POINT
        i = np.flatnonzero(ok)  # only compute where inputs are usable
        S = p.values[scol][i]
        fail = np.zeros(len(p.values[tcol]), dtype=bool)
        gsw = p._gsw()
        if cfg.freezing_method == "teos10" and gsw is not None:
            SA = gsw.SA_from_SP(S, P[i], p.longitude, p.latitude) if p.pos_ok else gsw.SR_from_SP(S)
            fail[i] = p.t90(tcol, cfg)[i] < gsw.t_freezing(SA, P[i], 0.0)
        else:
            fail[i] = p.t68(tcol, cfg)[i] < freezing_point_ipts68(S, P[i])
        p.flag(tcol, np.flatnonzero(fail), cfg.freezing_flag, Test2.FREEZING_POINT)


# --------------------------------------------------------------------------- #
# 2.7 / 2.8 / 2.9  Spike, top-and-bottom spike, gradient
# --------------------------------------------------------------------------- #
def _tests_columns(p: Profile):
    """Iterate over the temperature and salinity columns of a profile.

    Args:
        p: Profile.

    Yields:
        ``(kind, column)`` pairs, with ``kind`` ``"temperature"`` or
        ``"salinity"``.
    """
    for kind in ("temperature", "salinity"):
        for col in p.cols_of(kind):
            yield kind, col


def test_2_7_spike(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.7, Spike.

    For each interior value V2 with neighbours V1 and V3, a spike is
    ``|V2 - (V1 + V3) / 2| - |(V3 - V1) / 2|`` above the threshold.
    Neighbours are the nearest values not flagged erroneous or missing.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    for kind, col in _tests_columns(p):
        idx = np.flatnonzero(p.eligible(col))
        if len(idx) < 3:
            continue
        p.performed |= Test2.SPIKE
        v = p.values[col][idx]
        v1, v2, v3 = v[:-2], v[1:-1], v[2:]
        # |V2 - (V1+V3)/2| - |(V3-V1)/2| > threshold   (the NCEI text has a typo in the
        # first term; this is the standard IGOSS/GTSPP form)
        score = np.abs(v2 - (v1 + v3) / 2.0) - np.abs((v3 - v1) / 2.0)
        hit = idx[1:-1][score > cfg.spike_thresholds[kind]]
        p.flag(col, hit, cfg.spike_flag, Test2.SPIKE)


def test_2_8_top_bottom_spike(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.8, Top and Bottom Spike.

    The first and last usable value of each temperature and salinity
    column is compared with its single neighbour. A difference at or above
    :attr:`Stage2Config.top_bottom_thresholds` flags the end value.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    for kind, col in _tests_columns(p):
        idx = np.flatnonzero(p.eligible(col))
        if len(idx) < 2:
            continue
        p.performed |= Test2.TOP_BOTTOM_SPIKE
        v, thr = p.values[col], cfg.top_bottom_thresholds[kind]
        if abs(v[idx[0]] - v[idx[1]]) >= thr:  # surface point vs next
            p.flag(col, idx[0], cfg.spike_flag, Test2.TOP_BOTTOM_SPIKE)
        if abs(v[idx[-1]] - v[idx[-2]]) >= thr:  # bottom point vs previous
            p.flag(col, idx[-1], cfg.spike_flag, Test2.TOP_BOTTOM_SPIKE)


def test_2_9_gradient(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.9, Gradient.

    The deviation of a value from the mean of its neighbours, divided by
    the pressure change between the neighbours (an assumption), must not
    exceed :attr:`Stage2Config.gradient_limits`. Values flagged doubtful,
    erroneous or missing are not used.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    P = p.pressure_dbar()
    for kind, col in _tests_columns(p):
        # doubtful, erroneous and missing values are not considered
        idx = np.flatnonzero(p.eligible(col, NOT_GOOD_I) & np.isfinite(P))
        if len(idx) < 3:
            continue
        p.performed |= Test2.GRADIENT
        v, pr = p.values[col][idx], P[idx]
        dp = pr[2:] - pr[:-2]  # ASSUMPTION: "change in pressure" = P3 - P1
        with np.errstate(divide="ignore", invalid="ignore"):
            grad = np.abs(v[1:-1] - (v[:-2] + v[2:]) / 2.0) / dp
        hit = idx[1:-1][(dp > 0) & (grad > cfg.gradient_limits[kind])]
        p.flag(col, hit, cfg.gradient_flag, Test2.GRADIENT)


# --------------------------------------------------------------------------- #
# 2.10  Density inversion
# --------------------------------------------------------------------------- #
def test_2_10_density_inversion(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.10, Density Inversion.

    Density is computed with ``gsw`` from each temperature and salinity
    pair and compared with the previous level at their mid-point pressure
    (an assumption). A decrease larger than
    :attr:`Stage2Config.density_inversion_threshold` flags temperature,
    salinity and the matching ``SIGP`` column at the deeper level. The test
    is skipped, with a note, if ``gsw`` is not installed.

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    gsw = p._gsw()
    if gsw is None:
        p.note("[DENSITY_INVERSION] skipped: package 'gsw' not installed")
        return
    P = p.pressure_dbar()
    for tcol in p.cols_of("temperature"):
        scol = p.partner(tcol, "salinity")
        if scol is None:
            continue
        ok = p.eligible(tcol, NOT_GOOD_I) & p.eligible(scol, NOT_GOOD_I) & np.isfinite(P)
        idx = np.flatnonzero(ok)
        if len(idx) < 2:
            continue
        p.performed |= Test2.DENSITY_INVERSION
        SP, T, pr = p.values[scol][idx], p.t90(tcol, cfg)[idx], P[idx]
        SA = gsw.SA_from_SP(SP, pr, p.longitude, p.latitude) if p.pos_ok else gsw.SR_from_SP(SP)
        CT = gsw.CT_from_t(SA, T, pr)
        # ASSUMPTION: compare the two densities at a common (mid-point) pressure, so that
        # the normal increase of in-situ density with pressure is not mistaken for stability
        pref = 0.5 * (pr[:-1] + pr[1:])
        d = gsw.rho(SA[1:], CT[1:], pref) - gsw.rho(SA[:-1], CT[:-1], pref)
        hit = idx[1:][d < -cfg.density_inversion_threshold]
        p.flag(tcol, hit, cfg.density_flag, Test2.DENSITY_INVERSION)
        p.flag(scol, hit, cfg.density_flag, Test2.DENSITY_INVERSION)  # density needs both
        dcol = "SIGP_" + tcol.split("_", 1)[-1]  # the file's own density column
        if dcol in p.values and len(hit):
            p.flag(dcol, hit, cfg.density_flag, Test2.DENSITY_INVERSION)


# --------------------------------------------------------------------------- #
# 2.11  Bottom        (ASSUMPTION: depth may not exceed bathymetry by more than tolerance)
# --------------------------------------------------------------------------- #
def test_2_11_bottom(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.11, Bottom.

    Skipped without a bathymetry source. Levels deeper than the bathymetry
    plus :attr:`Stage2Config.bottom_tolerance` are flagged (an assumption).

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    if cfg.bathymetry is None or p.latitude is None or p.longitude is None or not p.pos_ok or not p.depth_col:
        return
    water = cfg.bathymetry.depth_at(p.latitude, p.longitude)
    if water is None or not math.isfinite(water) or water <= 0:
        return
    p.performed |= Test2.BOTTOM
    z = p.depth_m()
    too_deep = np.flatnonzero(np.isfinite(z) & (z > water * (1 + cfg.bottom_tolerance)))
    if len(too_deep):
        for col in p.values:
            if col == p.depth_col or p.code(col) in cfg.global_limits:
                p.flag(col, too_deep, cfg.bottom_flag, Test2.BOTTOM)
        p.note(f"[BOTTOM] {len(too_deep)} levels deeper than bathymetry ({water:.0f} m)")


# --------------------------------------------------------------------------- #
# 2.12  Temperature inversion
# ASSUMPTION: an inversion = a local minimum with a local maximum below it, within
# `inversion_layer_m`, whose temperature difference exceeds `inversion_amplitude_c`.
# The NCEI text gives the 50 m layer only; the test stays off until you set an amplitude.
# --------------------------------------------------------------------------- #
def test_2_12_temperature_inversion(p: Profile, cfg: Stage2Config) -> None:
    """Run test 2.12, Temperature Inversion.

    Off unless :attr:`Stage2Config.inversion_amplitude_c` is set. A local
    temperature minimum with a local maximum below it, within
    :attr:`Stage2Config.inversion_layer_m` and differing by more than the
    amplitude, is flagged from the minimum to the maximum (an assumption).

    Args:
        p: Profile to test.
        cfg: Test settings.
    """
    if cfg.inversion_amplitude_c is None or not p.depth_col:
        return
    z_all = p.depth_m()
    for col in p.cols_of("temperature"):
        idx = np.flatnonzero(p.eligible(col) & np.isfinite(z_all))
        if len(idx) < 3:
            continue
        p.performed |= Test2.TEMPERATURE_INVERSION
        t, z = p.values[col][idx], z_all[idx]
        lmin = [k for k in range(1, len(t) - 1) if t[k] < t[k - 1] and t[k] <= t[k + 1]]
        lmax = [k for k in range(1, len(t) - 1) if t[k] > t[k - 1] and t[k] >= t[k + 1]]
        for kmin in lmin:
            for kmax in lmax:
                if kmax <= kmin:
                    continue
                if z[kmax] - z[kmin] > cfg.inversion_layer_m:
                    break
                if t[kmax] - t[kmin] > cfg.inversion_amplitude_c:
                    p.flag(col, idx[kmin : kmax + 1], cfg.inversion_flag, Test2.TEMPERATURE_INVERSION)


# --------------------------------------------------------------------------- #
# Driver and reports
# --------------------------------------------------------------------------- #
STAGE2_TESTS = (
    (Test2.GLOBAL_RANGE, test_2_1_global_range),
    (Test2.REGIONAL_RANGE, test_2_2_regional_range),
    (Test2.INCREASING_DEPTH, test_2_3_increasing_depth),
    (Test2.PROFILE_ENVELOPE, test_2_4_profile_envelope),
    (Test2.CONSTANT_PROFILE, test_2_5_constant_profile),
    (Test2.FREEZING_POINT, test_2_6_freezing_point),
    (Test2.SPIKE, test_2_7_spike),
    (Test2.TOP_BOTTOM_SPIKE, test_2_8_top_bottom_spike),
    (Test2.GRADIENT, test_2_9_gradient),
    (Test2.DENSITY_INVERSION, test_2_10_density_inversion),
    (Test2.BOTTOM, test_2_11_bottom),
    (Test2.TEMPERATURE_INVERSION, test_2_12_temperature_inversion),
)


def test_enabled(test: Test2, p: Profile, cfg: Stage2Config) -> bool:
    """Check whether a test can run in this configuration.

    Args:
        test: Test to check.
        p: Profile the test would run on.
        cfg: Test settings.

    Returns:
        ``False`` if an input is missing: no bathymetry for 2.11, no
        amplitude for 2.12 or no ``gsw`` package for 2.10. ``True``
        otherwise.
    """
    if test is Test2.BOTTOM:
        return cfg.bathymetry is not None
    if test is Test2.TEMPERATURE_INVERSION:
        return cfg.inversion_amplitude_c is not None
    if test is Test2.DENSITY_INVERSION:
        return p._gsw() is not None
    return True


_INH = np.zeros(10, dtype=int)  # flag -> inheritance rank: only 3 (doubtful) and 4 (erroneous)
_INH[3], _INH[4] = 3, 4


def inherit_derived_flags(p: Profile, cfg: Stage2Config) -> None:
    """Give derived parameters the worse flag of their sources.

    For each rule in :attr:`Stage2Config.derived_from`, a present value
    takes the worst doubtful (3) or erroneous (4) flag among the same-row
    values it is computed from, if that is worse than its own. Missing
    sources are not inherited. Rules are applied in order, so ``PSAL``
    passes flags on to ``POTM``, ``SIGP`` and ``DOXY``. Runs after all tests,
    so inherited flags never feed back into a test.

    Args:
        p: Profile to update. :attr:`Profile.inherited` records the sources.
        cfg: Test settings.
    """
    for dcode, scodes in cfg.derived_from.items():
        for dcol in [c for c in p.values if p.code(c) == dcode]:
            suffix = dcol.split("_", 1)[-1]
            srcs: list[str] = []
            for sc in scodes:
                same = [c for c in p.values if p.code(c) == sc and c.endswith("_" + suffix)]
                srcs += same or ([c for c in p.values if p.code(c) == sc] if sc in ("PRES", "DEPH") else [])
            srcs = [c for c in dict.fromkeys(srcs) if c != dcol]
            if not srcs:
                continue
            ranks = np.vstack([_INH[np.clip(p.flags[c], 0, 9)] for c in srcs])
            worst = ranks.max(axis=0)
            cur = p.flags[dcol]
            for i in np.flatnonzero((worst >= 3) & np.isfinite(p.values[dcol])):
                if _RANK.get(int(cur[i]), 0) < _RANK[int(worst[i])]:
                    cur[i] = int(worst[i])
                    p.inherited[(dcol, int(i))] = [c for c, r in zip(srcs, ranks[:, i], strict=True) if r == worst[i]]


def run_stage2(profiles: Sequence[Profile], cfg: Stage2Config) -> pd.DataFrame:
    """Run tests 2.1 to 2.12 on every profile.

    Args:
        profiles: Profiles to test. Their flags, reasons and QCP / QCF masks
            are updated in place.
        cfg: Test settings.

    Returns:
        One row per profile, from :func:`profile_summary`.
    """
    for p in profiles:
        for test, fn in STAGE2_TESTS:
            if test_enabled(test, p, cfg):
                fn(p, cfg)
                p.ran |= test
        if cfg.untested_parameters_good:
            for col, v in p.values.items():
                p.flag(col, np.flatnonzero(np.isfinite(v)), QF.GOOD, Test2.NONE)  # 0 -> 1 only
        if cfg.inherit_derived_flags:
            inherit_derived_flags(p, cfg)
    return profile_summary(profiles)


def combined_codes(station: Station | None, p: Profile) -> tuple[str, str]:
    """Combine the Stage 1 and Stage 2 QCP / QCF codes.

    Args:
        station: Stage 1 station of the profile, or ``None``.
        p: Profile.

    Returns:
        The QCP and QCF codes as hexadecimal text.
    """
    s1p = int(station.performed) if station else 0
    s1f = int(station.failed) if station else 0
    return f"{s1p | int(p.performed):X}", f"{s1f | int(p.failed):X}"


def profile_summary(profiles: Sequence[Profile]) -> pd.DataFrame:
    """Summarise Stage 2 results in a table.

    Args:
        profiles: Profiles that have been through :func:`run_stage2`.

    Returns:
        A DataFrame with one row per profile: the combined QCP / QCF codes,
        the failed Stage 2 tests, the number of doubtful and erroneous
        values for each temperature, salinity and pressure column, and the
        messages.
    """
    rows = []
    for p in profiles:
        qcp, qcf = combined_codes(p.station, p)
        row: dict[str, Any] = {
            "file": Path(p.source).name,
            "station": p.label,
            "QCP": qcp,
            "QCF": qcf,
            "stage2_failed": ",".join(str(t.name) for t in Test2 if t and t in p.failed),
        }
        for col, f in p.flags.items():
            if col == p.depth_col or p.code(col) in ("DEPH", "PRES") or kind_of(p.code(col)):
                row[f"{col}_doubtful"] = int((f == QF.DOUBTFUL).sum())
                row[f"{col}_erroneous"] = int((f == QF.ERRONEOUS).sum())
        row["messages"] = " | ".join(p.messages)
        rows.append(row)
    return pd.DataFrame(rows)


def flagged_values(profiles: Sequence[Profile]) -> pd.DataFrame:
    """List every doubtful or erroneous value.

    Args:
        profiles: Profiles that have been through :func:`run_stage2`.

    Returns:
        A DataFrame with one row per flagged value: station, parameter,
        level, depth, value, flag, the tests responsible and, for inherited
        flags, the source columns.
    """
    rows = []
    for p in profiles:
        z = p.depth_m() if p.depth_col else None
        for col, f in p.flags.items():
            for i in np.flatnonzero(np.isin(f, (int(QF.DOUBTFUL), int(QF.ERRONEOUS)))):
                src = p.inherited.get((col, int(i)), [])
                tests = set(p.reasons.get((col, int(i)), []))
                for s in src:  # inherited: tests that flagged the sources
                    tests |= set(p.reasons.get((s, int(i)), []))
                rows.append(
                    {
                        "station": p.label,
                        "parameter": col,
                        "level": int(i),
                        "depth_m": None if z is None else float(z[i]),
                        "value": float(p.values[col][i]),
                        "flag": int(f[i]),
                        "tests": ",".join(sorted(tests)),
                        "inherited_from": ",".join(src),
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# datashop_toolbox adapter (data section) -- edit here if attribute names differ
# --------------------------------------------------------------------------- #
SKIP_CODES = ("FFFF", "CNTR", "SNCN", "SYTM")  # counters / SBE flag / time: not tested
COL_RE = re.compile(r"^([A-Z][A-Z0-9]{3})_(\d{2})$")  # e.g. PRES_01, TE90_01, PSAL_02


def _get_dataframe(odf: Any) -> pd.DataFrame:
    """Find the data table of a toolbox object.

    Args:
        odf: An :class:`~datashop_toolbox.odfhdr.OdfHeader`.

    Returns:
        The data section as a DataFrame.

    Raises:
        AttributeError: If no DataFrame can be found on the object.
    """
    data = getattr(odf, "data", None)
    for obj, names in ((data, ("data_frame", "df", "dataframe")), (odf, ("data_frame", "df"))):
        for n in names:
            df = getattr(obj, n, None) if obj is not None else None
            if isinstance(df, pd.DataFrame):
                return df
    if isinstance(data, pd.DataFrame):
        return data
    raise AttributeError(
        "Could not find the data DataFrame on the toolbox object; edit _get_dataframe() in gtspp_stage2.py"
    )


def _null_values(odf: Any) -> dict[str, float]:
    """Read the null value of each parameter.

    Args:
        odf: An :class:`~datashop_toolbox.odfhdr.OdfHeader`.

    Returns:
        Null value by parameter code, for example ``{"TEMP_01": -99.0}``,
        from the parameter headers.
    """
    out = {}
    for ph in getattr(odf, "parameter_headers", None) or []:
        code = getattr(ph, "code", None) or getattr(ph, "get_code", lambda: None)()
        nv = getattr(ph, "null_string", None)  # toolbox stores the null as a string
        nv = getattr(ph, "null_value", None) if nv in (None, "") else nv
        try:
            if code is not None and nv is not None:
                out[str(code).strip().strip("'")] = float(nv)
        except (TypeError, ValueError):
            pass
    return out


def profile_from_station(st: Station, default_null: float = -99.0) -> Profile:
    """Build a :class:`Profile` from a Stage 1 station.

    Numeric columns named like ``PRES_01`` are taken from the data section.
    Counters, the Sea-Bird flag column and time are skipped
    (:data:`SKIP_CODES`). Null values become ``NaN`` with flag 9, and an
    existing ``Q<code>`` flag column is used as the starting flags.

    Args:
        st: Station whose ``odf`` holds the data.
        default_null: Null value used when a parameter header has none.

    Returns:
        The profile.
    """
    df = _get_dataframe(st.odf)
    nulls = _null_values(st.odf)
    values, flags = {}, {}
    for col in df.columns:
        if not COL_RE.match(str(col)) or str(col)[:4] in SKIP_CODES:
            continue
        v = np.array(pd.to_numeric(df[col], errors="coerce"), dtype=float)
        if np.isnan(v).all():
            continue
        v[np.isclose(v, nulls.get(col, default_null))] = np.nan
        qcol = f"Q{col}"  # existing ODF flag column, if any
        f = (
            np.nan_to_num(np.array(pd.to_numeric(df[qcol], errors="coerce"), dtype=float), nan=0.0).astype(int)
            if qcol in df.columns
            else np.zeros(len(v), dtype=int)
        )
        f[np.isnan(v)] = int(QF.MISSING)
        values[col], flags[col] = v, f
    depth_col = next((c for c in values if c.startswith("PRES_")), None) or next(
        (c for c in values if c.startswith("DEPH_")), None
    )
    snd = st.sounding if st.sounding not in (None, -99.0) else None
    return Profile(
        source=st.source,
        label=st.label,
        latitude=st.latitude,
        longitude=st.longitude,
        sounding=snd,
        values=values,
        flags=flags,
        depth_col=depth_col,
        station=st,
    )


def load_profiles(stations: Sequence[Station]) -> list[Profile]:
    """Build profiles for every station that has toolbox data.

    Args:
        stations: Stage 1 stations.

    Returns:
        The profiles. Stations read from raw text have no data and are
        skipped with a warning.
    """
    out = []
    for st in stations:
        if st.odf is None:
            log.warning("Skipping %s for Stage 2: no profile data (header read from raw text)", st.label)
            continue
        try:
            out.append(profile_from_station(st))
        except Exception as exc:
            log.error("No profile data for %s: %s", st.label, exc)
    return out


def profile_from_arrays(
    label: str, lat: float, lon: float, columns: Mapping[str, Sequence[float]], sounding: float | None = None
) -> Profile:
    """Build a :class:`Profile` directly from arrays.

    Useful for tests and for data that does not come from an ODF file.

    Args:
        label: Identifier of the profile.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        columns: Values by column name, for example ``{"PRES_01": [...]}``.
        sounding: Water depth in metres, if known.

    Returns:
        The profile, with ``NaN`` values flagged missing.
    """
    values = {c: np.asarray(v, float).copy() for c, v in columns.items()}
    flags = {c: np.where(np.isnan(v), int(QF.MISSING), 0).astype(int) for c, v in values.items()}
    depth_col = next((c for c in values if c.startswith("PRES_")), None) or next(
        (c for c in values if c.startswith("DEPH_")), None
    )
    return Profile(
        source=label,
        label=label,
        latitude=lat,
        longitude=lon,
        sounding=sounding,
        values=values,
        flags=flags,
        depth_col=depth_col,
    )


# --------------------------------------------------------------------------- #
# Command line: Stage 1 then Stage 2 on a folder of ODF files
# --------------------------------------------------------------------------- #
def main() -> None:
    """Run Stage 1 and Stage 2 from the command line and write CSV files."""
    ap = argparse.ArgumentParser(description="GTSPP Stage 1 + Stage 2 QC on a folder of ODF files")
    ap.add_argument("folder")
    ap.add_argument("--pattern", default="*.ODF")
    ap.add_argument(
        "--platforms",
        help="text file: known platform identifiers, one per line (default: the toolbox lookups/platforms.csv)",
    )
    ap.add_argument("--bathy", help="GEBCO/ETOPO netCDF (tests 1.4, 1.6, 2.11)")
    ap.add_argument(
        "--max-speed-knots", type=float, help="speed limit in knots for platforms that are not in the lookup table"
    )
    ap.add_argument("--inversion-amplitude", type=float, help="enable test 2.12 (deg C)")
    ap.add_argument("--out-prefix", default="gtspp")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    c1 = Stage1Config(default_max_speed_knots=args.max_speed_knots)
    c2 = Stage2Config(inversion_amplitude_c=args.inversion_amplitude)
    if args.platforms:
        c1.known_platforms = {ln.strip() for ln in Path(args.platforms).read_text().splitlines() if ln.strip()}
    if args.bathy:
        c1.bathymetry = c2.bathymetry = NetCDFBathymetry(args.bathy)

    stations = load_stations(args.folder, args.pattern)
    run_stage1(stations, c1).to_csv(f"{args.out_prefix}_stage1.csv", index=False)
    profiles = load_profiles(stations)
    summary = run_stage2(profiles, c2)
    summary.to_csv(f"{args.out_prefix}_stage2.csv", index=False)
    flagged_values(profiles).to_csv(f"{args.out_prefix}_stage2_flagged_values.csv", index=False)
    print(f"{len(profiles)} profiles; {int((summary['stage2_failed'] != '').sum())} with Stage 2 flags")


if __name__ == "__main__":
    main()
