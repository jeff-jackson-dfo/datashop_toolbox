from __future__ import annotations

import re
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any, get_type_hints

import pandas as pd
from pydantic import BaseModel, ValidationInfo, field_validator

from datashop_toolbox.basehdr import BaseHeader


class ValidatedBase(BaseModel):
    """Base model providing validation/normalization similar to old check_* functions."""

    model_config = {"extra": "allow"}

    # --- Validators ---
    @field_validator("*", mode="before")
    @classmethod
    def normalize_values(cls, v, info: ValidationInfo):

        if not info.field_name:
            return v

        type_hints = get_type_hints(cls)
        annotation = type_hints.get(info.field_name)
        if v is None:
            if annotation is float:
                return BaseHeader.NULL_VALUE
            if annotation is int:
                return int(BaseHeader.NULL_VALUE)
            if annotation is str and "date" in info.field_name.lower():
                return BaseHeader.SYTM_NULL_VALUE
            if annotation in (list, list[Any]):
                return []
            return v

        if isinstance(v, str):
            v = v.strip("' ")
        return v

    @field_validator("*", mode="before")
    @classmethod
    def validate_datetime_format(cls, v, info: ValidationInfo):
        """Special handling for fields named *_date (must match SYTM_FORMAT)."""
        if not info.field_name:
            return v

        type_hints = get_type_hints(cls)
        annotation = type_hints.get(info.field_name)

        # Only validate if the field is a string and looks like a date
        if isinstance(v, str) and annotation is str and "date" in info.field_name.lower():
            try:
                dt = datetime.strptime(v, BaseHeader.SYTM_FORMAT)
                return dt.strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
            except ValueError:
                raise ValueError(
                    f"Invalid date format for {info.field_name}: {v}. "
                    f"Expected {BaseHeader.SYTM_FORMAT}"
                )
        return v


# ---------------------------
# Helpers still useful
# ---------------------------
def list_to_dict(lst: list[Any]) -> dict[Any, Any]:
    """Convert alternating list elements into a dictionary."""
    if not isinstance(lst, list):
        raise TypeError(f"Expected list, got {type(lst)}")
    return {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)}


def clean_strings(lst: list[str]) -> list[str]:
    """Strip trailing commas and whitespace from each list element."""
    return [item.rstrip(", ").strip() for item in lst]


def check_string(value: str) -> str:
    """Ensure value is a string. Convert Fortran-style exponents (D to E) only in numbers."""
    if not value:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value)}: {value}")
    # Only replace D with E in scientific notation, not everywhere
    return re.sub(r"([+-]?\d*\.\d+)D([+-]?\d+)", r"\1E\2", value)


def check_datetime(value: str | None) -> str:
    """Validate datetime string according to SYTM_FORMAT, or return NULL value."""
    if value is None or value == "":
        return BaseHeader.SYTM_NULL_VALUE
    try:
        dt = datetime.strptime(value, BaseHeader.SYTM_FORMAT)
        return datetime.strftime(dt, BaseHeader.SYTM_FORMAT)[:-4].upper()
    except ValueError:
        raise ValueError(f"Invalid date format: {value}. Expected {BaseHeader.SYTM_FORMAT}")


def is_valid_datetime(date_str: str) -> bool:
    try:
        if date_str[:2] == "%d":
            pd.to_datetime(date_str, errors="raise", dayfirst=True)
        else:
            pd.to_datetime(date_str, errors="raise", dayfirst=False)
        return True
    except (ValueError, TypeError):
        return False


def matches_datetime_format(date_str: str, fmt: str) -> bool:
    """Return True if date_str matches the datetime format fmt."""
    try:
        datetime.strptime(date_str, fmt)
        return True
    except ValueError:
        return False


def coerce_datetime(date_str: str, output_fmt: str = "%d-%b-%Y %H:%M:%S.%f") -> str:
    try:
        dt = pd.to_datetime(date_str, errors="raise", dayfirst=True)
        return dt.strftime(output_fmt).upper()
    except (ValueError, TypeError):
        return date_str


def split_string_with_quotes(input_string: str) -> list[str]:
    """Split a string into tokens, respecting quoted substrings."""
    if not isinstance(input_string, str):
        raise TypeError(f"Expected str, got {type(input_string)}")
    return shlex.split(input_string)


def convert_to_float(item: Any) -> Any:
    """Convert value to float if possible, otherwise return unchanged."""
    try:
        return float(item)
    except (ValueError, TypeError):
        return item


def convert_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame values to floats where possible."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas.DataFrame, got {type(df)}")
    # Use applymap with a safe conversion to float, fallback to original value if conversion fails
    if isinstance(df, pd.Series):
        return df[0].apply(convert_to_float)
    elif isinstance(df, pd.DataFrame):
        return df.map(convert_to_float)


def add_commas(lines: str, skip_last: bool = False) -> str:
    """Add commas at end of each line, skip last if requested."""
    if not isinstance(lines, str):
        raise TypeError(f"Expected str, got {type(lines)}")

    lines_out = lines.replace("\n", ",\n").replace("' ,", "',")
    if skip_last:
        return lines_out.rstrip(",\n") + "\n"
    return lines_out if lines_out.endswith("\n") else lines_out + "\n"


def get_current_date_time() -> str:
    """Return current date/time in SYTM_FORMAT (truncated)."""
    return datetime.now().strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()


# ---------------------------
# File handling
# ---------------------------
def read_file_lines(file_with_path: str) -> list[str]:
    """Read all lines from a file and strip whitespace. Print errors to console, always return a list."""
    if not isinstance(file_with_path, str):
        print(f"'file_with_path' must be str, got {type(file_with_path).__name__}")
        return []
    try:
        with Path.open(file_with_path, encoding="iso-8859-1") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"File not found: {file_with_path}")
        return []
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return []


def find_lines_with_text(odf_file_lines: list[str], substrings: list[str]) -> list[tuple[int, str]]:
    """
    Find all lines containing any of the given substrings.
    If a substring ends with 'HEADER', the line must also end with 'HEADER' or 'HEADER,'.
    Returns (index, cleaned_line).
    """
    if not isinstance(substrings, list) or not all(isinstance(s, str) for s in substrings):
        raise TypeError("substrings must be a list[str]")
    if not isinstance(odf_file_lines, list):
        raise TypeError(f"odf_file_lines must be list[str], got {type(odf_file_lines)}")

    result = []
    for i, line in enumerate(odf_file_lines):
        if not isinstance(line, str):
            continue

        for sub in substrings:
            if sub in line:
                if sub.endswith("HEADER"):
                    # Enforce HEADER rule
                    if line.rstrip().endswith(("HEADER", "HEADER,")):
                        cleaned = line.rstrip().rstrip(",")
                        result.append((i, cleaned))
                        break
                else:
                    # Just a normal substring match
                    result.append((i, line.rstrip()))
                    break
    return result


def split_lines_into_dict(lines: list) -> dict:
    assert isinstance(lines, list), f"Input argument 'lines' is not of type list: {lines}"
    return list_to_dict(lines)


def main():

    # Example usage of read_file_lines
    file_path = "example.txt"  # Replace with your file path

    lines = read_file_lines(file_path)
    print(f"Lines read from {file_path}:")
    for i, line in enumerate(lines, 1):
        print(f"{i}: {line}")


if __name__ == "__main__":
    main()
