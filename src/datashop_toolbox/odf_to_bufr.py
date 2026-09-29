#!/usr/bin/env python3
"""
odf_to_bufr.py
==============

Convert a DFO Ocean Data Format (ODF) CTD file into a WMO BUFR (FM-94)
message, using **BUFR template 315007** -- "Representation of data
derived from a ship-based lowered instrument measuring subsurface
seawater temperature, salinity and current profiles" (the operational
CTD / TESAC template, in force since May 2014).

This script depends on two libraries:

* ``datashop_toolbox`` (https://github.com/jeff-jackson-dfo/datashop_toolbox)
  -- used only to read/parse the ODF file (``OdfHeader.read_odf``).
* ``pybufrkit`` (pure-Python, pip-installable: ``pip install pybufrkit``)
  -- used to encode the BUFR message. It ships its own copy of the WMO
  BUFR tables, so no ecCodes / BUFRDC C library is required.
  [pybufrkit](https://pybufrkit.readthedocs.io/en/latest/)

Usage
-----
    python odf_to_bufr.py CTD_LAT2025146_013_1_DN.ODF

    python odf_to_bufr.py CTD_LAT2025146_013_1_DN.ODF \\
        --output out.bufr --originating-centre 54 --agency 124001

What gets populated
--------------------
Template 315007 also carries sections for surface pressure, waves,
air temperature/humidity, wind, a single "surface" T/S/current value,
and a current profile. None of that is present in a CTD downcast, so
those sections are encoded as *present but empty* (delayed-replication
counts of zero), which is valid BUFR and is how those optional blocks
are meant to be skipped. What IS populated:

* Identification: station/site name, cruise number, agency, date/time,
  lat/lon, a profile ID, event (station) number, and total water depth.
* The temperature/salinity profile block (one level per row of the
  ODF data table): depth, pressure, temperature, salinity, each with
  its own GTSPP qualifier + quality-flag pair, using the ODF file's
  own quality flags directly (033050, "Global GTSPP quality flag",
  uses the same 0-9 scale as DFO's ODF quality flags).
* The dissolved-oxygen profile block, if the ODF file has usable DOXY
  data, converted from mL/L to the umol/kg BUFR requires.

Please read the "REVIEW BEFORE USE" notes in ``build_flat_values()``
below -- a few codes (instrument-type code tables 022067/022068, the
originating centre, the agency code) are placeholders you should
confirm against your own reporting requirements before treating the
output as GTS-ready. This script has NOT been validated against a
live WMO BUFR validator; it has only been round-tripped through
pybufrkit's own decoder as a sanity check (see the bottom of the
script).
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from pybufrkit.decoder import Decoder
from pybufrkit.encoder import Encoder

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.odfhdr import OdfHeader

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

BUFR_TEMPLATE = 315007          # ship-based CTD / TESAC template
MASTER_TABLE_VERSION = 41       # version bundled with pybufrkit that defines 315007
DEFAULT_ORIGINATING_CENTRE = 54       # WMO Common Table C-11: 54 = Montreal (CMC), Canada
DEFAULT_AGENCY_CODE = 124001          # Code table 001036: Canada, MEDS
O2_ML_PER_L_TO_UMOL_PER_L = 44.6596   # standard factor: 1 mL/L O2 = 44.6596 umol/L
DEFAULT_SEAWATER_DENSITY = 1025.0     # kg/m^3, used only if SIGP_01 is unavailable


def missing():
    """A value of None tells pybufrkit to encode this field as BUFR 'missing'."""
    return None


# ----------------------------------------------------------------------
# Reading the ODF file
# ----------------------------------------------------------------------

def read_odf(odf_path: Path) -> OdfHeader:
    odf = OdfHeader()
    odf.read_odf(odf_path)
    return odf


# ----------------------------------------------------------------------
# Building the flat BUFR data-section value list for template 315007
# ----------------------------------------------------------------------

def build_flat_values(
    odf: OdfHeader,
    agency_code: int = DEFAULT_AGENCY_CODE,
) -> list:
    """
    Build the flat, positionally-ordered list of values pybufrkit expects
    for one subset encoded with unexpanded descriptor [315007].

    The order below was derived by expanding 315007 (and its nested
    Table D sequences 301003, 301011, 301012, 301021, 302090, 306033,
    306034, 306035/112000, 306036, 306037/109000) against pybufrkit's
    bundled WMO master-table-version-41 tables, and cross-checked
    against the public documentation of BUFR template 315007
    (WMO template registry; metocean/moana-bufrtools reference
    implementation). It is NOT a generic template walker -- it is
    specific to 315007's fixed structure, which makes it easy to
    read/audit line-by-line but means it would need to be re-derived
    if you ever wanted to encode a different template.

    REVIEW BEFORE USE:
      * ``agency_code`` (001036) defaults to 124001 "Canada, Marine
        Environmental Data Service (MEDS)" since DFO/BIO is not listed
        individually in Code Table 001036 -- adjust if a more specific
        code applies to your reporting chain.
      * 022067 (instrument type) and 022068 (recorder type) code
        tables were not populated in pybufrkit's bundled tables at the
        time this script was written, so they are left as BUFR missing
        values below. If your reporting requirements need them filled
        in, look up the current values in the WMO Manual on Codes and
        set ``instrument_type_code`` / ``recorder_type_code`` accordingly.
    """
    cruise = odf.cruise_header
    event = odf.event_header
    instrument = odf.instrument_header
    df = odf.data.data_frame
    params = odf.data.parameter_list

    # --- instrument-type / recorder-type codes (see REVIEW BEFORE USE) ---
    instrument_type_code = missing()   # BUFR code table 022067
    recorder_type_code = missing()     # BUFR code table 022068
    o2_instrument_code = missing()     # BUFR code table 003012

    # --- date/time (event start) ---
    dt = datetime.strptime(event.start_date_time, BaseHeader.SYTM_FORMAT)

    # --- direction of profile: 0=upwards, 1=downwards, from the ODF
    #     EVENT_QUALIFIER2 (DN/UP) recorded in the file name / header ---
    qualifier2 = (event.event_qualifier2 or "").strip().upper()
    direction_of_profile = 1 if qualifier2 == "DN" else (0 if qualifier2 == "UP" else missing())

    # --- station / instrument identification strings ---
    station_id = (cruise.platform or "")[:9]           # 001011, 9 bytes (72 bits)
    site_name = (event.station_name or "")[:32]         # 001019, 32 bytes (256 bits)
    cruise_mission_id = (cruise.cruise_number or "")[:20]  # 001115, 20 bytes (160 bits)
    profile_id = f"{cruise.cruise_number}_{event.event_number}"[:8]  # 001079, 8 bytes (64 bits)
    try:
        obs_seq_number = int(event.event_number)         # 001023
    except (TypeError, ValueError):
        obs_seq_number = missing()

    instrument_serial = (instrument.serial_number or "").strip()[:8] or missing()  # 002171

    values: list = []

    # ---------------- Identification ----------------
    # 301003: Ship's call sign and motion
    values += [station_id, missing(), missing()]        # 001011, 001012, 001013
    # Extended identification
    values += [site_name, missing(), missing()]          # 001019, 001103, 001087
    values += [agency_code, cruise_mission_id, missing(), missing()]  # 001036, 001115, 001080, 005036
    # 301011: Year, month, day / 301012: Hour, minute
    values += [dt.year, dt.month, dt.day, dt.hour, dt.minute]
    # 301021: Latitude/longitude (high accuracy)
    values += [event.initial_latitude, event.initial_longitude]
    # Profile information
    values += [profile_id, obs_seq_number, event.sounding if event.sounding not in 
               (None, BaseHeader.NULL_VALUE) else missing()]

    # ---------------- Surface pressure / waves / air temp-humidity / wind ----------------
    # None of this applies to a CTD cast -- each block's delayed
    # replication factor is simply set to 0 (i.e. present, empty).
    values += [0]   # 101000 -> 031000 surface pressure block, factor = 0
    values += [0]   # 101000 -> 031000 waves block, factor = 0
    values += [0]   # 101000 -> 031000 air temperature/humidity block, factor = 0
    values += [0]   # 101000 -> 031000 wind block, factor = 0

    # ---------------- Surface temperature/salinity/current (single value) ----------------
    # Not populated -- the full profile (including the surface-most
    # scan) is carried in the temperature/salinity profile block below.
    values += [missing()]                     # 022067 instrument type (surface block)
    values += [missing()]                     # 002171 instrument serial (surface block)
    values += [missing(), missing(), missing()]   # 302090: 002038, 007063, 022045
    values += [missing(), missing(), missing()]   # 306033: 002033, 007063, 022064
    values += [missing(), missing(), missing(), missing(), missing()]  # 306034
    values += [missing()]                     # 002171 (cancel)
    values += [missing()]                     # 022067 (cancel)

    # ---------------- Temperature and salinity profile data ----------------
    values += [4]                              # 002038 method = STD/CTD sensor
    values += [instrument_type_code]            # 022067 (see REVIEW BEFORE USE)
    values += [recorder_type_code]               # 022068 (see REVIEW BEFORE USE)
    values += [instrument_serial]                # 002171
    values += [1]                               # 002033 method of salinity/depth = in-situ sensor, better than 0.02 per mille  # noqa: E501
    values += [0]                               # 002032 indicator for digitization = values at selected depths
    values += [direction_of_profile]             # 022056
    values += [1]                               # 003011 method of depth calc = from water pressure / equation of state

    ts_rows = _profile_rows(df, params)
    values += [len(ts_rows)]                     # 031002 delayed replication factor
    for depth_m, pres_pa, temp_k, psal, qdeph, qpres, qte90, qpsal in ts_rows:
        values += [depth_m, 13, qdeph]
        values += [pres_pa, 10, qpres]
        values += [temp_k, 11, qte90]
        values += [psal, 12, qpsal]

    # ---------------- Current profile data ----------------
    # No current-meter data on a standard CTD cast.
    values += [0]                                # 107000 -> 031000, factor = 0

    # ---------------- Dissolved oxygen profile data ----------------
    o2_rows = _oxygen_rows(df, params)
    if o2_rows:
        values += [1]                            # 104000 -> 031000, factor = 1 (one execution of the wrapper)
        values += [0]                            # 002032 indicator for digitization
        values += [o2_instrument_code]            # 003012 (see REVIEW BEFORE USE)
        values += [1]                            # 003011 method of depth calc
        values += [len(o2_rows)]                  # 031002 delayed replication factor
        for depth_m, pres_pa, doxy_umol_kg, qdeph, qpres, qdoxy in o2_rows:
            values += [depth_m, 13, qdeph]
            values += [pres_pa, 10, qpres]
            values += [doxy_umol_kg, 16, qdoxy]
    else:
        values += [0]                            # 104000 -> 031000, factor = 0 (no oxygen data)

    return values


def _col(df, params, code):
    return df[code] if code in params else None


def _qflag(row_val):
    """Pass an ODF quality flag straight through; blank/NaN -> missing."""
    if row_val is None:
        return missing()
    try:
        if row_val != row_val:  # NaN check without importing pandas/numpy here
            return missing()
    except TypeError:
        pass
    return int(row_val)


def _profile_rows(df, params):
    """
    Build (depth_m, pressure_Pa, temperature_K, salinity_permille,
    Qdepth, Qpres, Qtemp, Qsal) tuples, one per ODF data row.
    """
    depth_col = "DEPH_01" if "DEPH_01" in params else None
    pres_col = "PRES_01" if "PRES_01" in params else None
    temp_col = "TE90_01" if "TE90_01" in params else None
    psal_col = "PSAL_01" if "PSAL_01" in params else None
    if not (depth_col and pres_col and temp_col and psal_col):
        raise ValueError(
            "ODF file is missing one of DEPH_01/PRES_01/TE90_01/PSAL_01 "
            "needed to build the temperature/salinity profile block."
        )

    qdeph_col = "QDEPH_01" if "QDEPH_01" in params else None
    qpres_col = "QPRES_01" if "QPRES_01" in params else None
    qte90_col = "QTE90_01" if "QTE90_01" in params else None
    qpsal_col = "QPSAL_01" if "QPSAL_01" in params else None

    rows = []
    for i in range(len(df)):
        depth_m = float(df[depth_col].iloc[i])
        pres_pa = float(df[pres_col].iloc[i]) * 10000.0   # dbar -> Pa
        temp_k = float(df[temp_col].iloc[i]) + 273.15      # degC (ITS-90) -> K
        psal = float(df[psal_col].iloc[i])                 # PSU used directly as BUFR "0/00"

        qdeph = _qflag(df[qdeph_col].iloc[i]) if qdeph_col else missing()
        qpres = _qflag(df[qpres_col].iloc[i]) if qpres_col else missing()
        qte90 = _qflag(df[qte90_col].iloc[i]) if qte90_col else missing()
        qpsal = _qflag(df[qpsal_col].iloc[i]) if qpsal_col else missing()

        rows.append((depth_m, pres_pa, temp_k, psal, qdeph, qpres, qte90, qpsal))
    return rows


def _oxygen_rows(df, params):
    """
    Build (depth_m, pressure_Pa, dissolved_oxygen_umol_per_kg,
    Qdepth, Qpres, Qoxygen) tuples, one per ODF data row -- only if
    DOXY_01 is present in the file.
    """
    if "DOXY_01" not in params:
        return []

    depth_col = "DEPH_01" if "DEPH_01" in params else None
    pres_col = "PRES_01" if "PRES_01" in params else None
    if not (depth_col and pres_col):
        return []

    sigp_col = "SIGP_01" if "SIGP_01" in params else None
    qdeph_col = "QDEPH_01" if "QDEPH_01" in params else None
    qpres_col = "QPRES_01" if "QPRES_01" in params else None
    qdoxy_col = "QDOXY_01" if "QDOXY_01" in params else None

    rows = []
    for i in range(len(df)):
        doxy_ml_l = df["DOXY_01"].iloc[i]
        if doxy_ml_l is None or doxy_ml_l != doxy_ml_l:  # NaN
            continue
        depth_m = float(df[depth_col].iloc[i])
        pres_pa = float(df[pres_col].iloc[i]) * 10000.0

        if sigp_col is not None:
            sigma_theta = float(df[sigp_col].iloc[i])
            density = 1000.0 + sigma_theta if sigma_theta == sigma_theta else DEFAULT_SEAWATER_DENSITY
        else:
            density = DEFAULT_SEAWATER_DENSITY

        o2_umol_l = float(doxy_ml_l) * O2_ML_PER_L_TO_UMOL_PER_L
        o2_umol_kg = o2_umol_l * 1000.0 / density

        qdeph = _qflag(df[qdeph_col].iloc[i]) if qdeph_col else missing()
        qpres = _qflag(df[qpres_col].iloc[i]) if qpres_col else missing()
        qdoxy = _qflag(df[qdoxy_col].iloc[i]) if qdoxy_col else missing()

        rows.append((depth_m, pres_pa, o2_umol_kg, qdeph, qpres, qdoxy))

    return rows


# ----------------------------------------------------------------------
# Assembling and encoding the full BUFR message
# ----------------------------------------------------------------------

def build_bufr_json(odf: OdfHeader, originating_centre: int, agency_code: int) -> list:
    event = odf.event_header
    dt = datetime.strptime(event.start_date_time, BaseHeader.SYTM_FORMAT)

    section0 = ["BUFR", 0, 4]  # length auto-calculated, edition 4

    section1 = [
        0,                       # section_length (auto)
        0,                       # master_table_number (0 = WMO standard)
        originating_centre,      # originating_centre (Table C-11)
        0,                       # originating_subcentre
        0,                       # update_sequence_number
        False,                   # is_section2_presents
        "0000000",               # flag_bits
        31,                      # data_category: Table A, 31 = Oceanographic data
        0,                       # data_i18n_subcategory
        0,                       # data_local_subcategory
        MASTER_TABLE_VERSION,    # master_table_version
        0,                       # local_table_version
        dt.year, dt.month, dt.day, dt.hour, dt.minute,
        0,                       # second
        # 'local_bytes' omitted: it is the section's optional trailing field
    ]

    section3 = [
        0,                        # section_length (auto)
        "00000000",               # reserved_bits
        1,                        # n_subsets
        True,                     # is_observation
        False,                    # is_compressed
        "000000",                 # flag_bits
        [BUFR_TEMPLATE],          # unexpanded_descriptors
    ]

    flat_values = build_flat_values(odf, agency_code=agency_code)

    section4 = [
        0,                        # section_length (auto)
        "00000000",               # reserved_bits
        [flat_values],            # template_data: one flat value list per subset
    ]

    section5 = ["7777"]

    return [section0, section1, section3, section4, section5]


def odf_to_bufr(
    odf_path: Path,
    output_path: Path | None = None,
    originating_centre: int = DEFAULT_ORIGINATING_CENTRE,
    agency_code: int = DEFAULT_AGENCY_CODE,
    verify: bool = True,
) -> Path:
    odf = read_odf(odf_path)

    bufr_json = build_bufr_json(odf, originating_centre, agency_code)

    encoder = Encoder()
    bufr_message = encoder.process(bufr_json)

    if output_path is None:
        output_path = odf_path.with_suffix(".bufr")

    with open(output_path, "wb") as f:
        f.write(bufr_message.serialized_bytes)

    print(f"Wrote {output_path} ({len(bufr_message.serialized_bytes)} bytes)")

    if verify:
        decoder = Decoder()
        decoded = decoder.process(bufr_message.serialized_bytes)
        n_values = len(decoded.template_data.value.decoded_values_all_subsets[0])
        print(
            f"Round-trip check OK: decoded {n_values} values from 1 subset, "
            f"template {decoded.template_data.value.template.original_descriptor_ids}."
        )

    return output_path


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert a DFO ODF CTD file to a WMO BUFR message (template 315007)."
    )
    parser.add_argument("odf_file", type=Path, help="Path to the input .ODF file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output .bufr path")
    parser.add_argument(
        "--originating-centre", type=int, default=DEFAULT_ORIGINATING_CENTRE,
        help=f"WMO Common Table C-11 originating centre code (default: {DEFAULT_ORIGINATING_CENTRE} = Montreal/CMC)",
    )
    parser.add_argument(
        "--agency", type=int, default=DEFAULT_AGENCY_CODE,
        help=f"BUFR code table 001036 agency code (default: {DEFAULT_AGENCY_CODE} = Canada, MEDS)",
    )
    parser.add_argument("--no-verify", action="store_true", help="Skip the round-trip decode check")
    args = parser.parse_args()

    odf_to_bufr(
        args.odf_file,
        output_path=args.output,
        originating_centre=args.originating_centre,
        agency_code=args.agency,
        verify=not args.no_verify,
    )


if __name__ == "__main__":
    main()
