import pandas as pd

from datashop_toolbox.validated_base import (
    ValidatedBase,
    add_commas,
    clean_strings,
    convert_dataframe,
    get_current_date_time,
    list_to_dict,
    split_string_with_quotes,
)


# Example subclass of ValidatedBase
class SampleHeader(ValidatedBase):
    cruise_date: str | None = None
    temperature: float | None = None
    station_id: int | None = None
    notes: str | None = None


def demo_validated_base():
    print("=== Demo: ValidatedBase ===")
    sample = SampleHeader(
        cruise_date="09-OCT-2025 10:45:43.000",
        temperature=None,
        station_id=None,
        notes="  'Some note with D-style exponent: 1.23D4'  ",
    )
    print(sample.model_dump())

    print("\n=== Demo: list_to_dict ===")
    lst = ["KEY1", "VALUE1", "KEY2", "VALUE2"]
    print(list_to_dict(lst))

    print("\n=== Demo: clean_strings ===")
    raw_strings = ["  value1, ", "value2 ", " value3,"]
    print(clean_strings(raw_strings))

    print("\n=== Demo: split_string_with_quotes ===")
    quoted_string = 'KEY1="Value with spaces" KEY2=123'
    print(split_string_with_quotes(quoted_string))

    print("\n=== Demo: convert_dataframe ===")
    df = pd.DataFrame({"A": ["1", "2", "three"], "B": ["4.0", "5.5", "six"]})
    print(convert_dataframe(df))

    print("\n=== Demo: add_commas ===")
    multiline = "line1\nline2\nline3"
    print(add_commas(multiline, skip_last=True))

    print("\n=== Demo: get_current_date_time ===")
    print(get_current_date_time())


if __name__ == "__main__":
    demo_validated_base()
