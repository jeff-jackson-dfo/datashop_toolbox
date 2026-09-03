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
    """Base model providing validation/normalization similar to old check_* functions.

    Serves as a common Pydantic base class for the ODF header models,
    applying two blanket ``"before"`` validators to every field: one
    that fills in type-appropriate null sentinels and strips quoted
    strings, and one that enforces the ODF SYTM date/time format on
    any field whose name contains ``"date"``.
    """

    model_config = {"extra": "allow"}

    # --- Validators ---
    @field_validator("*", mode="before")
    @classmethod
    def normalize_values(cls, v, info: ValidationInfo):
        """Fill in null sentinels and strip quoted strings for any field.

        Args:
            v: Raw value assigned to the field named by ``info``.
            info: Pydantic validation info identifying the field being
                set and used to look up its type annotation.

        Returns:
            If ``v`` is ``None``, a type-appropriate null sentinel:
            :attr:`~datashop_toolbox.basehdr.BaseHeader.NULL_VALUE` for
            ``float`` fields, its ``int`` cast for ``int`` fields,
            :attr:`~datashop_toolbox.basehdr.BaseHeader.SYTM_NULL_VALUE`
            for ``str`` fields whose name contains ``"date"``, an empty
            list for list-typed fields, or ``v`` unchanged otherwise.
            If ``v`` is a string, the value with surrounding single
            quotes and whitespace stripped. Otherwise, ``v`` unchanged.
        """

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
        """Special handling for fields named *_date (must match SYTM_FORMAT).

        Args:
            v: Raw value assigned to the field named by ``info``.
            info: Pydantic validation info identifying the field being
                set and used to look up its type annotation.

        Returns:
            If ``v`` is a string, the field is ``str``-typed, and the
            field name contains ``"date"``, the value reformatted to
            the standard (upper-cased, microsecond-truncated) SYTM
            representation. Otherwise, ``v`` unchanged.

        Raises:
            ValueError: If the field qualifies for date validation but
                ``v`` does not match
                :attr:`~datashop_toolbox.basehdr.BaseHeader.SYTM_FORMAT`.
        """
        if not info.field_name:
            return v

        type_hints = get_type_hints(cls)
        annotation = type_hints.get(info.field_name)

        # Only validate if the field is a string and looks like a date
        if isinstance(v, str) and annotation is str and "date" in info.field_name.lower():
            try:
                dt = datetime.strptime(v, BaseHeader.SYTM_FORMAT)
                return dt.strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
            except ValueError as err:
                raise ValueError(
                    f"Invalid date format for {info.field_name}: {v}. "
                    f"Expected {BaseHeader.SYTM_FORMAT}"
                ) from err
        return v


# ---------------------------
# Helpers still useful
# ---------------------------
def list_to_dict(lst: list[Any]) -> dict[Any, Any]:
    """Convert alternating list elements into a dictionary.

    Args:
        lst: List of alternating key/value elements, e.g.
            ``[key1, value1, key2, value2, ...]``.

    Returns:
        A dictionary pairing each even-indexed element with the
        odd-indexed element that follows it.

    Raises:
        TypeError: If ``lst`` is not a list.
    """
    if not isinstance(lst, list):
        raise TypeError(f"Expected list, got {type(lst)}")
    return {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)}


def clean_strings(lst: list[str]) -> list[str]:
    """Strip trailing commas and whitespace from each list element.

    Args:
        lst: List of strings to clean.

    Returns:
        A new list with each element right-stripped of commas and
        whitespace, then fully stripped.
    """
    return [item.rstrip(", ").strip() for item in lst]


def check_string(value: str) -> str:
    """Ensure value is a string. Convert Fortran-style exponents (D to E) only in numbers.

    Args:
        value: Value to check and normalize.

    Returns:
        An empty string if ``value`` is falsy; otherwise ``value``
        with any Fortran-style ``D`` exponent in a decimal number
        (e.g. ``"1.5D+02"``) converted to ``E`` notation.

    Raises:
        TypeError: If ``value`` is truthy but not a string.
    """
    if not value:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value)}: {value}")
    # Only replace D with E in scientific notation, not everywhere
    return re.sub(r"([+-]?\d*\.\d+)D([+-]?\d+)", r"\1E\2", value)


def check_datetime(value: str | None) -> str:
    """Validate datetime string according to SYTM_FORMAT, or return NULL value.

    Args:
        value: Date/time string to validate, or ``None``/empty.

    Returns:
        :attr:`~datashop_toolbox.basehdr.BaseHeader.SYTM_NULL_VALUE` if
        ``value`` is ``None`` or empty; otherwise ``value`` reformatted
        to the standard (upper-cased, microsecond-truncated) SYTM
        representation.

    Raises:
        ValueError: If ``value`` does not match
            :attr:`~datashop_toolbox.basehdr.BaseHeader.SYTM_FORMAT`.
    """
    if value is None or value == "":
        return BaseHeader.SYTM_NULL_VALUE
    try:
        dt = datetime.strptime(value, BaseHeader.SYTM_FORMAT)
        return datetime.strftime(dt, BaseHeader.SYTM_FORMAT)[:-4].upper()
    except ValueError as err:
        raise ValueError(f"Invalid date format: {value}. Expected {BaseHeader.SYTM_FORMAT}") from err


def is_valid_datetime(date_str: str) -> bool:
    """Check whether a string can be parsed as a date/time.

    Args:
        date_str: Date/time string to check. If it begins with the
            literal characters ``"%d"``, parsing is attempted with
            ``dayfirst=True``; otherwise ``dayfirst=False``.

    Returns:
        ``True`` if ``date_str`` can be parsed by
        :func:`pandas.to_datetime`, ``False`` otherwise.
    """
    try:
        if date_str[:2] == "%d":
            pd.to_datetime(date_str, errors="raise", dayfirst=True)
        else:
            pd.to_datetime(date_str, errors="raise", dayfirst=False)
        return True
    except (ValueError, TypeError):
        return False


def matches_datetime_format(date_str: str, fmt: str) -> bool:
    """Return True if date_str matches the datetime format fmt.

    Args:
        date_str: Date/time string to check.
        fmt: ``strptime``-style format string to check against.

    Returns:
        ``True`` if ``date_str`` matches ``fmt``, ``False`` otherwise.
    """
    try:
        datetime.strptime(date_str, fmt)
        return True
    except ValueError:
        return False


def coerce_datetime(date_str: str, output_fmt: str = "%d-%b-%Y %H:%M:%S.%f") -> str:
    """Reformat a date/time string to a target format, best-effort.

    Args:
        date_str: Date/time string to parse, with day-first parsing.
        output_fmt: ``strftime``-style format to render the parsed
            date/time into. Defaults to the ODF SYTM format.

    Returns:
        ``date_str`` reformatted to ``output_fmt`` and upper-cased if
        it can be parsed by :func:`pandas.to_datetime`; otherwise
        ``date_str`` unchanged.
    """
    try:
        dt = pd.to_datetime(date_str, errors="raise", dayfirst=True)
        return dt.strftime(output_fmt).upper()
    except (ValueError, TypeError):
        return date_str


def split_string_with_quotes(input_string: str) -> list[str]:
    """Split a string into tokens, respecting quoted substrings.

    Args:
        input_string: String to split, using shell-style quoting
            rules.

    Returns:
        The list of tokens produced by :func:`shlex.split`.

    Raises:
        TypeError: If ``input_string`` is not a string.
    """
    if not isinstance(input_string, str):
        raise TypeError(f"Expected str, got {type(input_string)}")
    return shlex.split(input_string)


def convert_to_float(item: Any) -> Any:
    """Convert value to float if possible, otherwise return unchanged.

    Args:
        item: Value to attempt to convert.

    Returns:
        ``item`` converted to a ``float`` if possible, otherwise
        ``item`` unchanged.
    """
    try:
        return float(item)
    except (ValueError, TypeError):
        return item


def convert_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame values to floats where possible.

    Args:
        df: DataFrame (or Series) whose values should be converted.

    Returns:
        A new object of the same kind as ``df`` with every value
        passed through :func:`convert_to_float`.

    Raises:
        TypeError: If ``df`` is not a ``pandas.DataFrame``.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas.DataFrame, got {type(df)}")
    # Use applymap with a safe conversion to float, fallback to original value if conversion fails
    if isinstance(df, pd.Series):
        return df[0].apply(convert_to_float)
    elif isinstance(df, pd.DataFrame):
        return df.map(convert_to_float)


def add_commas(lines: str, skip_last: bool = False) -> str:
    """Add commas at end of each line, skip last if requested.

    Args:
        lines: Newline-separated text to append commas to.
        skip_last: If ``True``, the final line is left without a
            trailing comma.

    Returns:
        ``lines`` with a comma appended to the end of each line
        (except the last, if ``skip_last`` is ``True``), always ending
        in a single trailing newline.

    Raises:
        TypeError: If ``lines`` is not a string.
    """
    if not isinstance(lines, str):
        raise TypeError(f"Expected str, got {type(lines)}")

    lines_out = lines.replace("\n", ",\n").replace("' ,", "',")
    if skip_last:
        return lines_out.rstrip(",\n") + "\n"
    return lines_out if lines_out.endswith("\n") else lines_out + "\n"


def get_current_date_time() -> str:
    """Return current date/time in SYTM_FORMAT (truncated).

    Returns:
        The current local date/time formatted per
        :attr:`~datashop_toolbox.basehdr.BaseHeader.SYTM_FORMAT`,
        truncated to hundredths of a second and upper-cased.
    """
    return datetime.now().strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()


# ---------------------------
# File handling
# ---------------------------
def read_file_lines(file_with_path: Path) -> list[str]:
    """Read all lines from a file and strip whitespace. Print errors to console, always return a list.

    Args:
        file_with_path: Path to the file to read, decoded as
            ``iso-8859-1``.

    Returns:
        The file's non-blank lines with surrounding whitespace
        stripped. Returns an empty list if ``file_with_path`` is not a
        string, the file does not exist, or any other error occurs
        while reading (an explanatory message is printed in each
        case).
    """
    if not isinstance(file_with_path, Path):
        print(f"'file_with_path' must be Path, got {type(file_with_path).__name__}")
        return []
    try:
        with Path.open(file_with_path, encoding="utf-8") as file:
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

    Args:
        odf_file_lines: Lines of an ODF file to search.
        substrings: Substrings to search for in each line. A
            substring ending in ``"HEADER"`` only matches lines that
            themselves end with ``"HEADER"`` or ``"HEADER,"``.

    Returns:
        A list of ``(index, cleaned_line)`` tuples for each matching
        line, in the order they appear in ``odf_file_lines``, with
        trailing whitespace (and, for ``HEADER`` matches, a trailing
        comma) removed from ``cleaned_line``.

    Raises:
        TypeError: If ``substrings`` is not a list of strings, or if
            ``odf_file_lines`` is not a list.
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
    """Convert alternating header lines into a dictionary.

    Args:
        lines: List of alternating key/value elements, e.g.
            ``[key1, value1, key2, value2, ...]``.

    Returns:
        The result of :func:`list_to_dict` applied to ``lines``.

    Raises:
        AssertionError: If ``lines`` is not a list.
    """
    assert isinstance(lines, list), f"Input argument 'lines' is not of type list: {lines}"
    return list_to_dict(lines)


def main():

    # Example usage of read_file_lines
    file_path = Path(Path.cwd(), "example.txt")  # Replace with your file path
    lines = read_file_lines(file_path)
    print(f"Lines read from {file_path}:")
    for i, line in enumerate(lines, 1):
        print(f"{i}: {line}")


if __name__ == "__main__":
    main()
