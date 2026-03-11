from enum import Enum
from typing import Dict, List, Any, Mapping, Iterable, Optional
import math

# Given widths
print_widths = dict(
    Bottle=10,
    Bottle_SN=11,
    Date_Time=12,
    parameter=16,
)

class columns(Enum):
    """Bottle data to export BTL file (header labels / order)."""
    bottle = "Bottle"  # name for header only (not used as parameter)
    oxygen = "Sbeox0ML/L"
    salinity = "Sal00"
    potential_temperature = "Potemp090C"
    sigma_theta = u"Sigma-é00"
    scan = "Scan"
    pressure = "PrdM"
    conductivity = "C0S/m"
    par = "Par"
    turbidity = "Par1TurbWETntu0"
    fluorescence = "FlECO-AFL"
    cdom = "WetCDOM"

def _fmt_value(val: Any) -> str:
    """Format values similarly to the example: integers as-is, floats right-aligned,
    using scientific notation for very large/small magnitudes, 4 decimal places otherwise."""
    if val is None:
        return ""
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if math.isnan(val):
            return ""
        a = abs(val)
        if a != 0 and (a < 1e-2 or a >= 1e2):
            return f"{val:.4e}"
        return f"{val:.4f}"
    return str(val)

def _pad_left(text: str, width: int) -> str:
    return f"{text:<{width}}"

def _pad_right(text: str, width: int) -> str:
    return f"{text:>{width}}"

def print_btl_table(
    rows: Iterable[Mapping[str, Any]],
    param_enum: Iterable[columns] = (
        columns.oxygen,
        columns.salinity,
        columns.potential_temperature,
        columns.sigma_theta,
        columns.scan,
        columns.pressure,
        columns.conductivity,
        columns.par,
        columns.turbidity,
        columns.fluorescence,
        columns.cdom,
    ),
    widths: Mapping[str, int] = print_widths,
) -> None:
    """
    Print a BTL-style table with:
      - 2 header lines (Bottle/Bottle/Date) and (Position/S/N/Time)
      - For each bottle: an average line with date, and a sdev line with time.
    
    Each `row` should be a mapping with at least:
      {
        "bottle": int | str,
        "bottle_sn": int | str,
        "date": str,           # e.g. "Oct 14 2025"
        "time": str,           # e.g. "13:14:48"
        "avg":  { <param_label>: number, ... },   # using labels from param_enum.value
        "sdev": { <param_label>: number, ... },
      }
    """
    # Resolve fixed widths
    w_btl = int(widths.get("Bottle", 10))
    w_sn = int(widths.get("Bottle_SN", 11))
    w_dt = int(widths.get("Date_Time", 12))
    w_param_default = int(widths.get("parameter", 12))

    # Parameter labels (visible column headers)
    param_labels = [p.value for p in param_enum]
    # Per-parameter widths (at least header width)
    param_widths = [max(w_param_default, len(lbl)) for lbl in param_labels]

    # ---- Header lines ----
    # Line 1: Bottle | Bottle | Date | <param headers...>
    h1 = [
        _pad_left("Bottle", w_btl),
        _pad_left("Bottle", w_sn),
        _pad_left("Date", w_dt),
    ]
    h1.extend(_pad_left(lbl, w) for lbl, w in zip(param_labels, param_widths))
    print(" ".join(h1))

    # Line 2: Position | S/N | Time | (empty for parameters)
    h2 = [
        _pad_left("Position", w_btl),
        _pad_left("S/N", w_sn),
        _pad_left("Time", w_dt),
    ]
    h2.extend(_pad_left("", w) for w in param_widths)
    print(" ".join(h2))

    # ---- Data lines (two per bottle) ----
    for row in rows:
        bottle = row.get("bottle", "")
        bottle_sn = row.get("bottle_sn", "")
        date = row.get("date", "")
        time = row.get("time", "")
        avg = row.get("avg", {}) or {}
        sdev = row.get("sdev", {}) or {}

        # AVG line: bottle | sn | date | param avg ... | (avg)
        avg_cells = [
            _pad_left(_fmt_value(bottle), w_btl),
            _pad_left(_fmt_value(bottle_sn), w_sn),
            _pad_left(_fmt_value(date), w_dt),
        ]
        for lbl, w in zip(param_labels, param_widths):
            v = _fmt_value(avg.get(lbl, ""))
            # Right-align if it looks numeric, else left
            if v and all(c in "+-0123456789.eE" for c in v.strip()):
                avg_cells.append(_pad_right(v, w))
            else:
                avg_cells.append(_pad_left(v, w))
        print(" ".join(avg_cells) + " (avg)")

        # SDEV line: (empty) | (empty) | time | param sdev ... | (sdev)
        sdev_cells = [
            _pad_left("", w_btl),
            _pad_left("", w_sn),
            _pad_left(_fmt_value(time), w_dt),
        ]
        for lbl, w in zip(param_labels, param_widths):
            v = _fmt_value(sdev.get(lbl, ""))
            if v and all(c in "+-0123456789.eE" for c in v.strip()):
                sdev_cells.append(_pad_right(v, w))
            else:
                sdev_cells.append(_pad_left(v, w))
        print(" ".join(sdev_cells) + " (sdev)")


def main() -> None:
    """
    Build a few example rows (bottles) and print them in BTL layout.
    Replace these with your parsed CTD/BTL values.
    """
    rows = [
        {
            "bottle": 5,
            "bottle_sn": 486845,
            "date": "Oct 14 2025",
            "time": "13:14:48",
            "avg": {
                "Sbeox0ML/L": 6.4614,
                "Sal00": 32.4181,
                "Potemp090C": 12.3098,
                "Sigma-é00": 24.5263,
                "Scan": 1760,
                "PrdM": 1.605,
                "C0S/m": 3.762126,
                "Par": 2.1916e2,
                "Par1TurbWETntu0": 1.6258e2,
                "FlECO-AFL": 2.2541,
                "WetCDOM": 0.4805,
            },
            "sdev": {
                "Sbeox0ML/L": 0.604,
                "Sal00": 0.391,
                "Potemp090C": 0.0017,
                "Sigma-é00": 0.000282,
                "Scan": 10,
                "PrdM": 0.0230,
                "C0S/m": 0.4045,
                "Par": 7.1621,
                "Par1TurbWETntu0": 34.261,
                "FlECO-AFL": 3.3553,
                "WetCDOM": 0.0317,
            },
        },
        {
            "bottle": 4,
            "bottle_sn": 486844,
            "date": "Oct 14 2025",
            "time": "13:15:05",
            "avg": {
                "Sbeox0ML/L": 5.6583,
                "Sal00": 32.4407,
                "Potemp090C": 12.3039,
                "Sigma-é00": 24.5449,
                "Scan": 2022,
                "PrdM": 10.584,
                "C0S/m": 3.764441,
                "Par": 3.6979e1,
                "Par1TurbWETntu0": 2.0393e1,
                "FlECO-AFL": 0.5009,
                "WetCDOM": 0.5973,
            },
            "sdev": {
                "Sbeox0ML/L": 0.604,
                "Sal00": 0.383,
                "Potemp090C": 0.0003,
                "Sigma-é00": 0.000043,
                "Scan": 10,
                "PrdM": 0.0026,
                "C0S/m": 0.0060,
                "Par": 0.1318,
                "Par1TurbWETntu0": 2.4874,
                "FlECO-AFL": 0.0240,
                "WetCDOM": 0.0000,
            },
        },
        # Add more bottles (3,2,1) as needed...
    ]

    print_btl_table(rows)

if __name__ == "__main__":
    main()
