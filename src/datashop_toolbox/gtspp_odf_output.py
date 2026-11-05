"""
gtspp_odf_output.py
-------------------
Save GTSPP quality control results into ODF files with ``datashop_toolbox``.

Takes the Stage 1 results (``gtspp_stage1.py``) and Stage 2 results
(``gtspp_stage2.py``) and writes quality-controlled copies of the ODF files.
The original files are never overwritten.

  What is written for each profile
  ────────────────────────────────
  • Flag columns : the per-value flags go to the ``Q<code>`` columns (for
                   example ``QTEMP_01``). The columns are created with
                   :meth:`~datashop_toolbox.odfhdr.OdfHeader.add_quality_flags`
                   if the file has none.
  • QCFF_01      : for every data row, the sum of the GTSPP test indices of
                   all Stage 2 tests that flagged any value in that row.
  • QUALITY_HEADER : the tests run (Stage 1 and Stage 2), the quality-code
                   and QCFF explanations, and the result of each test.
  • HISTORY_HEADER : one short entry listing the tests run (optional).

  Test names and numbers
  ──────────────────────
  Names and numbers are the GTSPP manual's own (1.1 to 1.6 and 2.1 to
  2.12). The number in parentheses, and the value added to QCFF when a Stage 2
  test fails, is the manual's test index (for example 2.1 -> 64, 2.10 ->
  32768, 2.12 -> 16777216). Only tests that were run are listed. Test 1.4,
  1.6 and 2.11 need a bathymetry file, 1.5 needs a speed limit and 2.12
  needs an amplitude setting.

  Stage 1 results
  ───────────────
  Stage 1 tests judge header fields, for which an ODF has no flag columns,
  so they appear only in the ``QUALITY_HEADER`` (tests run and results).
  ``QCFF`` is a Stage 2, per-row channel and does not include them.

  Shared infrastructure
  ─────────────────────
  • SCHEME / STAGE1_SCHEME : test numbers, names and indices
  • compute_qcff           : the QCFF value of every row of a profile
  • build_quality_header   : the ``QUALITY_HEADER`` of a profile
  • write_profile_odf      : write one QC'd ODF file
  • save_stage2_to_odf     : write all profiles and verify the files
  • print_summary          : console summary of failures

  Usage
  ─────
      stations = load_stations("odf_folder")
      run_stage1(stations, Stage1Config(known_platforms={"HUDSON"}))
      profiles = load_profiles(stations)
      run_stage2(profiles, Stage2Config())
      save_stage2_to_odf(profiles, "qc_odf")

  From the command line:

      python gtspp_odf_output.py odf_folder --out-dir qc_odf --platforms known.txt

  Requirements
  ────────────
  ``datashop_toolbox`` must be installed. ``gsw`` is needed for test 2.10 and
  ``netCDF4`` only for ``--bathy``; the toolbox installs neither.
"""

from __future__ import annotations

import argparse
import logging
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from datashop_toolbox.gtspp_stage1 import (
    DATE_PARTS,
    NetCDFBathymetry,
    Stage1Config,
    Station,
    load_stations,
    run_stage1,
)
from datashop_toolbox.gtspp_stage1 import Test as Test1
from datashop_toolbox.gtspp_stage2 import Profile, Stage2Config, Test2, load_profiles, run_stage2

log = logging.getLogger("gtspp_odf_output")

QCFF_CODE = "QCFF_01"
FLAG_EXCLUDED = ("SYTM", "CNTR", "SNCNTR")  # same exclusions as OdfHeader.add_quality_flags()


# --------------------------------------------------------------------------- #
# Test numbering / wording
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TestSpec:
    """A Stage 2 test as it appears in the quality header.

    Attributes:
        test: The test, as a :class:`~gtspp_stage2.Test2` member.
        number: GTSPP test number, for example ``"2.1"``.
        name: GTSPP test name, for example ``"Global Impossible Parameter
            Values"``.
    """

    test: Test2
    number: str  # GTSPP manual test number, "2.1"
    name: str  # GTSPP manual test name

    @property
    def bit(self) -> int:  # GTSPP test index; value added to QCFF on failure
        """Return the GTSPP test index, added to QCFF when the test fails."""
        return int(self.test)


SCHEME: tuple[TestSpec, ...] = (
    TestSpec(Test2.GLOBAL_RANGE, "2.1", "Global Impossible Parameter Values"),
    TestSpec(Test2.REGIONAL_RANGE, "2.2", "Regional Impossible Parameter Values"),
    TestSpec(Test2.INCREASING_DEPTH, "2.3", "Increasing Depth"),
    TestSpec(Test2.PROFILE_ENVELOPE, "2.4", "Profile Envelope"),
    TestSpec(Test2.CONSTANT_PROFILE, "2.5", "Constant Profile"),
    TestSpec(Test2.FREEZING_POINT, "2.6", "Freezing Point"),
    TestSpec(Test2.SPIKE, "2.7", "Spike"),
    TestSpec(Test2.TOP_BOTTOM_SPIKE, "2.8", "Top and Bottom Spike"),
    TestSpec(Test2.GRADIENT, "2.9", "Gradient"),
    TestSpec(Test2.DENSITY_INVERSION, "2.10", "Density Inversion"),
    TestSpec(Test2.BOTTOM, "2.11", "Bottom"),
    TestSpec(Test2.TEMPERATURE_INVERSION, "2.12", "Temperature Inversion"),
)
BIT_OF = {s.test.name: s.bit for s in SCHEME}


# Stage 1 (location / identification) -- GTSPP manual names and test indices (1, 2, 4 ... 32).
# These tests judge header fields (platform, date/time, position, sounding), for which an ODF
# has no flag columns, so they appear only in the QUALITY_HEADER (tests run + results);
# QCFF stays a Stage 2, per-row channel.
@dataclass(frozen=True)
class Stage1Spec:
    """A Stage 1 test as it appears in the quality header.

    Attributes:
        test: The test, as a :class:`~gtspp_stage1.Test` member.
        number: GTSPP test number, for example ``"1.1"``.
        name: GTSPP test name, for example ``"Platform Identification"``.
    """

    test: Test1
    number: str
    name: str

    @property
    def bit(self) -> int:
        """Return the GTSPP test index (1, 2, 4, 8, 16 or 32)."""
        return int(self.test)


STAGE1_SCHEME: tuple[Stage1Spec, ...] = (
    Stage1Spec(Test1.PLATFORM_ID, "1.1", "Platform Identification"),
    Stage1Spec(Test1.DATE_TIME, "1.2", "Impossible Date/Time"),
    Stage1Spec(Test1.LOCATION, "1.3", "Impossible Location"),
    Stage1Spec(Test1.ON_LAND, "1.4", "Position on Land"),
    Stage1Spec(Test1.SPEED, "1.5", "Impossible Speed"),
    Stage1Spec(Test1.SOUNDING, "1.6", "Impossible Sounding"),
)
_S1_FIELDS = {
    Test1.PLATFORM_ID: ("platform",),
    Test1.DATE_TIME: DATE_PARTS,
    Test1.LOCATION: ("latitude", "longitude"),
    Test1.ON_LAND: ("latitude", "longitude", "sounding"),
    Test1.SPEED: ("latitude", "longitude"),
    Test1.SOUNDING: ("sounding",),
}
_S1_NOT_APPLICABLE = {
    Test1.ON_LAND: "no usable position or no bathymetry value here",
    Test1.SPEED: "no earlier station for this platform in this run, or position/date unusable",
    Test1.SOUNDING: "no sounding in the header, or no usable position/bathymetry",
}


def _clean(text: str) -> str:
    """Make text safe for a single-quoted ODF header string.

    Args:
        text: Text to clean.

    Returns:
        The text without quotes and with repeated spaces collapsed.
    """
    return re.sub(r"\s+", " ", text.replace("'", "").replace('"', "")).strip()


def _result_stage1(st: Station, spec: Stage1Spec) -> str:
    """Describe the outcome of a Stage 1 test for the quality header.

    Args:
        st: Station that has been through :func:`~gtspp_stage1.run_stage1`.
        spec: The test.

    Returns:
        ``ok``, ``ok (<corrections>)``, ``failed (<reasons>; flags: ...)``
        or ``not applicable (<why>)``.
    """
    tag = f"[{spec.test.name}] "
    msgs = [_clean(m[len(tag) :]) for m in st.messages if m.startswith(tag)]
    flags = [f"{k}={int(st.flags[k])}" for k in _S1_FIELDS[spec.test] if int(st.flags[k]) in (2, 3, 4, 5, 9)]
    if spec.test is Test1.DATE_TIME:  # drop the "earlier part flagged erroneous" cascade lines
        msgs = [m for m in msgs if "flagged erroneous" not in m] or msgs
    if spec.test in st.failed:
        return "failed (" + "; ".join(msgs + ([f"flags: {', '.join(flags)}"] if flags else [])) + ")"
    if spec.test in st.performed or spec.test in (Test1.PLATFORM_ID, Test1.DATE_TIME, Test1.LOCATION):
        extra = msgs + (
            [f"flags: {', '.join(f for f in flags if f.endswith('=5'))}"]
            if any(f.endswith("=5") for f in flags)
            else []
        )
        return "ok" + (f" ({'; '.join(extra)})" if extra else "")
    return f"not applicable ({_S1_NOT_APPLICABLE.get(spec.test, 'no usable data')})"


QUALITY_CODES_TEXT = [
    "QUALITY CODES",
    "0: Value has not been quality controlled",
    "1: Value seems to be correct",
    "2: Value appears inconsistent with other values",
    "3: Value seems doubtful",
    "4: Value seems erroneous",
    "5: Value was modified",
    "9: Value is missing",
]
QCFF_TEXT = [
    "QCFF CHANNEL",
    "The QCFF flag allows one to determine from which test(s) the quality flag(s) originate",
    "It only applies to the stage 2 quality control tests.",
    "Each test in this step is associated with a number 2x, where x is a whole positive number.",
    "Before running the quality control, a QCFF value of 0 is attributed to each line of data.",
    "When a test fails, the value of 2x that is associated with that test is added to the QCFF.",
    "In this way one can easily identify which tests failed by analyzing the QCFF value.",
    "If the QC flag of a record is modified by hand, a value of 1 is added to the QCFF.",
]


# --------------------------------------------------------------------------- #
# QCFF and result wording
# --------------------------------------------------------------------------- #
def compute_qcff(p: Profile) -> np.ndarray:
    """Compute the QCFF value of every data row.

    Args:
        p: Profile that has been through :func:`~gtspp_stage2.run_stage2`.

    Returns:
        Integer array with one value per row: the sum of the distinct test
        indices of all tests that flagged any value in that row, or 0.
    """
    n = len(next(iter(p.values.values()))) if p.values else 0
    q = np.zeros(n, dtype=int)
    for (_col, i), names in p.reasons.items():
        for nm in set(names):
            q[i] |= BIT_OF.get(nm, 0)
    return q


def _density_label(p: Profile, col: str) -> str:
    """Name the density column that a test 2.10 result refers to.

    Args:
        p: Profile.
        col: A temperature, salinity or density column.

    Returns:
        The ``SIGP`` column of the same sensor if the profile has one,
        otherwise ``col``.
    """
    d = "SIGP_" + col.split("_", 1)[-1]
    return d if d in p.values else col


def _result(p: Profile, spec: TestSpec) -> str:
    """Describe the outcome of a Stage 2 test for the quality header.

    Args:
        p: Profile that has been through :func:`~gtspp_stage2.run_stage2`.
        spec: The test.

    Returns:
        ``ok``, ``failed (<column>: <count> value(s) flagged)``, ``not
        applicable (no usable data)``, or for test 2.10 ``ok (<columns>)``
        and ``Density inversion found (<columns>)``.
    """
    name = spec.test.name
    hit = Counter(col for (col, _i), names in p.reasons.items() if name in names)
    if spec.test is Test2.DENSITY_INVERSION:
        if hit:
            cols = sorted({_density_label(p, c) for c in hit})
            return f"Density inversion found ({', '.join(cols)})"
        cols = sorted({_density_label(p, t) for t in p.cols_of("temperature") if p.partner(t, "salinity")})
        return "ok" + (f" ({', '.join(cols)})" if cols else "")
    if hit:
        detail = ", ".join(f"{c}: {n}" for c, n in sorted(hit.items()))
        return f"failed ({detail} value(s) flagged)"
    if spec.test in p.performed or spec.test is Test2.REGIONAL_RANGE:  # 2.2: no region = ok
        return "ok"
    return "not applicable (no usable data)"


def build_quality_header(p: Profile, date: str | None = None):
    """Build the ``QUALITY_HEADER`` for a profile.

    Lists the Stage 1 and Stage 2 tests that were run, the quality-code and
    QCFF explanations, and the result of each test.

    Args:
        p: Profile that has been through Stage 2. Its station supplies the
            Stage 1 results; Stage 1 is omitted if it was not run.
        date: Value for ``QUALITY_DATE``. Defaults to the current date and
            time.

    Returns:
        A populated :class:`~datashop_toolbox.qualityhdr.QualityHeader`.
    """
    from datashop_toolbox.qualityhdr import QualityHeader
    from datashop_toolbox.validated_base import get_current_date_time

    specs = [s for s in SCHEME if s.test in p.ran]
    st = p.station
    specs1 = [s for s in STAGE1_SCHEME if st is not None and s.test in st.ran]  # none if Stage 1 not run
    qh = QualityHeader()
    qh.quality_date = date or get_current_date_time()
    qh.quality_tests = ["QUALITY CONTROL TESTS RUN"] + [
        f"Test {s.number}: GTSPP {s.name} ({s.bit})" for s in specs1 + specs
    ]
    qh.quality_comments = (
        QUALITY_CODES_TEXT
        + QCFF_TEXT
        + ["QUALITY CONTROL TEST RESULTS"]
        + [f"Test {s.number} {s.name} -> {_result_stage1(st, s)}" for s in specs1]
        + [f"Test {s.number} {s.name} -> {_result(p, s)}" for s in specs]
    )
    return qh


# --------------------------------------------------------------------------- #
# Editing the toolbox object
# --------------------------------------------------------------------------- #
def _is_flag_code(code: str, df_cols) -> bool:
    """Check whether a parameter code is itself a flag column.

    Args:
        code: Parameter code, for example ``"QTEMP_01"``.
        df_cols: Column names of the data table.

    Returns:
        ``True`` for ``QCFF`` codes and for codes ``Q<code>`` where
        ``<code>`` is a data column.
    """
    return code.startswith("QCFF") or (code.startswith("Q") and code[1:] in df_cols)


def ensure_flag_columns(odf) -> None:
    """Make sure every parameter has a ``Q<code>`` column.

    Uses the toolbox's own
    :meth:`~datashop_toolbox.odfhdr.OdfHeader.add_quality_flags` when the
    file has none. ``SYTM``, ``CNTR`` and ``SNCNTR`` get no flag column.

    Args:
        odf: An :class:`~datashop_toolbox.odfhdr.OdfHeader`, updated in
            place.

    Raises:
        ValueError: If only some parameters have flag columns.
    """
    df = odf.data.data_frame
    codes = [
        ph.code
        for ph in odf.parameter_headers
        if not ph.code.startswith(FLAG_EXCLUDED) and not _is_flag_code(ph.code, df.columns)
    ]
    have = [c for c in codes if f"Q{c}" in df.columns]
    if not have:
        odf.add_quality_flags()  # creates headers + zero-filled columns
    elif len(have) != len(codes):
        missing = [c for c in codes if c not in have]
        raise ValueError(f"Partial set of quality-flag columns; missing Q-columns for {missing}")


def _qcff_header():
    """Create the parameter header of the ``QCFF_01`` column.

    Returns:
        A :class:`~datashop_toolbox.parameterhdr.ParameterHeader` of type
        ``INTE`` with print width 8 and no decimals, since the GTSPP test
        indices reach 16777216.
    """
    from datashop_toolbox.parameterhdr import ParameterHeader

    ph = ParameterHeader()
    ph.type = "INTE"
    ph.name = "Quality flag: QCFF"
    ph.units = "none"
    ph.code = QCFF_CODE
    from datashop_toolbox.basehdr import BaseHeader

    ph.null_string = f"{BaseHeader.NULL_VALUE}"  # same null as the toolbox's Q<code> headers
    ph.print_field_width = 8  # GTSPP indices go up to 16777216
    ph.print_decimal_places = 0
    return ph


def apply_profile_to_odf(p: Profile, add_history: bool = True) -> None:
    """Write a profile's results into its toolbox object.

    Fills the ``Q<code>`` columns, adds or updates ``QCFF_01``, replaces the
    quality header and, optionally, adds a history entry. The ODF file is
    not written; see :func:`write_profile_odf`.

    Args:
        p: Profile that has been through Stage 2, with a station that holds
            the toolbox object.
        add_history: If ``True``, add a ``HISTORY_HEADER`` entry listing the
            tests run.
    """
    odf = p.station.odf
    ensure_flag_columns(odf)
    df = odf.data.data_frame

    # 1. individual flags -> Q<code> columns
    for col, flags in p.flags.items():
        qcol = f"Q{col}"
        if qcol in df.columns:
            df[qcol] = np.asarray(flags, dtype=int)

    # 2. QCFF column (+ parameter header)
    qcff = compute_qcff(p)
    new_header = QCFF_CODE not in df.columns
    df[QCFF_CODE] = qcff
    if new_header:
        odf.parameter_headers.append(_qcff_header())
    qph = next(ph for ph in odf.parameter_headers if ph.code == QCFF_CODE)
    qph.number_valid, qph.number_null = len(df), 0
    odf.data.data_frame = df
    odf.data.parameter_list = odf.get_parameter_codes()
    for ph in odf.parameter_headers:  # tidy fixed-width printing of flags
        if ph.code.startswith("Q") and ph.code not in odf.data.print_formats:
            odf.data.print_formats[ph.code] = "8.0" if ph.code == QCFF_CODE else "1.0"

    # 3. quality header
    if odf.quality_header is not None and any("QUALITY CONTROL" in t for t in odf.quality_header.quality_tests):
        log.info("%s: replacing the quality header written by an earlier QC run", p.label)
    odf.quality_header = build_quality_header(p)

    # 4. processing history
    if add_history:
        ran = [s.number for s in STAGE1_SCHEME if p.station and s.test in p.station.ran] + [
            s.number for s in SCHEME if s.test in p.ran
        ]
        odf.add_history()
        odf.add_to_history(f"GTSPP quality control tests run: {', '.join(ran)}")
        odf.add_to_history(f"Quality flags saved to Q<parameter> columns; test numbers in {QCFF_CODE}")


def _raw_file_spec(path: str) -> str | None:
    """Read ``FILE_SPECIFICATION`` from the raw text of an ODF file.

    Args:
        path: Path of the ODF file.

    Returns:
        The file specification, or ``None`` if it is missing or the file
        cannot be read.
    """
    try:
        for line in Path(path).read_text(errors="replace").splitlines()[:6]:
            m = re.match(r"^\s*FILE_SPECIFICATION\s*=\s*'?([^',]*)'?", line)
            if m and m.group(1).strip():
                return m.group(1).strip()
    except OSError:
        pass
    return None


def write_profile_odf(p: Profile, out_dir: str | Path, add_history: bool = True) -> Path:
    """Write one quality-controlled ODF file.

    Applies the results with :func:`apply_profile_to_odf`, restores
    ``FILE_SPECIFICATION`` if the toolbox read left it empty, refreshes the
    record header counts and writes the file. The minimum and maximum of the
    original parameters are kept, because the toolbox's ``update_odf``
    would include null values in them.

    Args:
        p: Profile that has been through Stage 2.
        out_dir: Folder for the output file, which keeps its original name.
        add_history: If ``True``, add a history entry.

    Returns:
        Path of the file written.

    Raises:
        ValueError: If the profile has no toolbox object, or ``out_dir``
            would overwrite the input file.
    """
    if p.station is None or p.station.odf is None:
        raise ValueError(f"{p.label}: no toolbox object to write")
    odf = p.station.odf
    apply_profile_to_odf(p, add_history=add_history)
    if not odf.file_specification:  # the toolbox read can leave this empty
        odf.file_specification = _raw_file_spec(p.source) or Path(p.source).stem
    # update_odf() refreshes the record-header counts (needed: NUM_PARAM grows) but also resets every
    # parameter's MIN/MAX from ALL values, null (-99) included.  Keep the original min/max for the
    # existing parameters; only the new Q/QCFF headers take the recomputed values.
    cols = odf.data.data_frame.columns
    saved = {
        ph.code: (ph.minimum_value, ph.maximum_value)
        for ph in odf.parameter_headers
        if not _is_flag_code(ph.code, cols)
    }
    odf.update_odf()
    for ph in odf.parameter_headers:
        if ph.code in saved:
            ph.minimum_value, ph.maximum_value = saved[ph.code]
    out = Path(out_dir) / Path(p.source).name
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.resolve() == Path(p.source).resolve():
        raise ValueError("refusing to overwrite the input file; choose a different out_dir")
    odf.write_odf(out)
    return out


def verify_written(p: Profile, path: Path) -> list[str]:
    """Check a written file against the in-memory results.

    Reads the file back with the toolbox and compares the ``Q<code>``
    columns, ``QCFF_01`` and the quality header.

    Args:
        p: Profile whose results were written.
        path: Path of the written file.

    Returns:
        A list of problems found. Empty if the file is correct.
    """
    from datashop_toolbox.odfhdr import OdfHeader

    o = OdfHeader()
    o.read_odf(Path(path))
    df, problems = o.data.data_frame, []
    for col, flags in p.flags.items():
        if f"Q{col}" not in df.columns:
            problems.append(f"missing column Q{col}")
        elif not np.array_equal(df[f"Q{col}"].astype(int).to_numpy(), np.asarray(flags, int)):
            problems.append(f"Q{col} differs from computed flags")
    if QCFF_CODE not in df.columns:
        problems.append(f"missing column {QCFF_CODE}")
    elif not np.array_equal(df[QCFF_CODE].astype(int).to_numpy(), compute_qcff(p)):
        problems.append(f"{QCFF_CODE} differs from computed values")
    want = build_quality_header(p, date=o.quality_header.quality_date if o.quality_header else None)
    if o.quality_header is None:
        problems.append("no QUALITY_HEADER")
    else:
        if [t.strip() for t in o.quality_header.quality_tests] != want.quality_tests:
            problems.append("QUALITY_TESTS differ")
        if [t.strip() for t in o.quality_header.quality_comments] != want.quality_comments:
            problems.append("QUALITY_COMMENTS differ")
    return problems


def print_summary(stations: Sequence[Station], profiles: Sequence[Profile]) -> None:
    """Print the Stage 1 and Stage 2 results to the console.

    For each test, shows how many stations or profiles failed out of how
    many were run, and names the failures. Also prints notes on corrections
    and lists files that could not be written.

    Args:
        stations: Stage 1 stations.
        profiles: Stage 2 profiles.
    """
    print(f"\nStage 1 (location and identification), {len(stations)} stations:")
    any1 = False
    for spec in STAGE1_SCHEME:
        bad = [s.label for s in stations if spec.test in s.failed]
        ran = sum(1 for s in stations if spec.test in s.ran)
        if ran:
            print(
                f"  Test {spec.number} {spec.name}: {len(bad)} failed of {ran} run"
                + (f"  -> {', '.join(bad)}" if bad else "")
            )
            any1 |= bool(bad)
    for s in stations:
        for m in s.messages:
            if "not in known list" in m or "rolled" in m or "converted" in m:
                print(f"  note {s.label}: {_clean(m)}")
    unreadable = [s.label for s in stations if s.odf is None]
    if unreadable:
        print(f"  NOT WRITTEN (toolbox could not read the file; Stage 1 only): {', '.join(unreadable)}")
    print(f"\nStage 2 (profile), {len(profiles)} profiles:")
    for spec in SCHEME:
        bad = [p.label for p in profiles if spec.test in p.failed]
        ran = sum(1 for p in profiles if spec.test in p.ran)
        if ran:
            print(
                f"  Test {spec.number} {spec.name}: {len(bad)} failed of {ran} run"
                + (f"  -> {', '.join(bad)}" if bad else "")
            )


def save_stage2_to_odf(
    profiles: Sequence[Profile], out_dir: str | Path, add_history: bool = True, verify: bool = True
) -> list[Path]:
    """Write quality-controlled ODF files for all profiles.

    Each file is written with :func:`write_profile_odf` and, if requested,
    checked with :func:`verify_written`. Errors are logged and the run
    continues with the next profile.

    Args:
        profiles: Profiles that have been through Stage 2.
        out_dir: Folder for the output files.
        add_history: If ``True``, add a history entry to each file.
        verify: If ``True``, read each file back and compare it with the
            results.

    Returns:
        Paths of the files written.
    """
    written = []
    for p in profiles:
        try:
            path = write_profile_odf(p, out_dir, add_history=add_history)
        except Exception as exc:
            log.error("Could not write %s: %s", p.label, exc)
            continue
        if verify:
            for msg in verify_written(p, path):
                log.error("%s: verification failed: %s", path.name, msg)
        written.append(path)
    return written


# --------------------------------------------------------------------------- #
# Command line: Stage 1 + Stage 2 + write QC'd ODF files
# --------------------------------------------------------------------------- #
def main() -> None:
    """Run Stage 1 and Stage 2 from the command line and write the ODF files."""
    ap = argparse.ArgumentParser(description="Run GTSPP stage 1+2 and save flags/QCFF/quality header into ODF files")
    ap.add_argument("folder")
    ap.add_argument("--out-dir", required=True, help="folder for the QC'd ODF files")
    ap.add_argument("--pattern", default="*.ODF")
    ap.add_argument("--platforms", help="text file: known platform identifiers, one per line")
    ap.add_argument("--bathy", help="GEBCO/ETOPO netCDF (tests 1.4, 1.6, 2.11)")
    ap.add_argument("--max-speed-knots", type=float)
    ap.add_argument("--no-history", action="store_true", help="do not add a HISTORY_HEADER entry")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    c1 = Stage1Config(default_max_speed_knots=args.max_speed_knots)
    c2 = Stage2Config()
    if args.platforms:
        c1.known_platforms = {ln.strip() for ln in Path(args.platforms).read_text().splitlines() if ln.strip()}
    if args.bathy:
        c1.bathymetry = c2.bathymetry = NetCDFBathymetry(args.bathy)

    stations = load_stations(args.folder, args.pattern)
    run_stage1(stations, c1)
    profiles = load_profiles(stations)
    run_stage2(profiles, c2)
    written = save_stage2_to_odf(profiles, args.out_dir, add_history=not args.no_history)
    print_summary(stations, profiles)
    print(f"{len(written)} ODF files written to {args.out_dir}")


if __name__ == "__main__":
    main()
