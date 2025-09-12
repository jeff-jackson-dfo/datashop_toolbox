import io
import pandas as pd
from typing import List, Dict, Optional, Self
from pydantic import Field, field_validator
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict, check_string, split_string_with_quotes, convert_dataframe

class DataRecords(ValidatedBase, BaseHeader):
    """ Represents the data records stored within an ODF object. """

    data_frame: pd.DataFrame = Field(default_factory=pd.DataFrame)
    parameter_list: List[str] = Field(default_factory=list)
    print_formats: Dict[str, str] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True  # allow pandas DataFrame

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    # ------------------------
    # Validators
    # ------------------------
    @field_validator("data_frame")
    @classmethod
    def validate_dataframe(cls, v: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(v, pd.DataFrame):
            raise TypeError(f"Expected pandas DataFrame, got {type(v)}")
        return v

    @field_validator("parameter_list", mode="before")
    @classmethod
    def validate_parameters(cls, v: List[str]) -> List[str]:
        return [check_string(p) for p in v]

    @field_validator("print_formats", mode="before")
    @classmethod
    def validate_print_formats(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not isinstance(v, dict):
            raise TypeError(f"Expected dict, got {type(v)}")
        return {check_string(k): check_string(val) for k, val in v.items()}

    # ------------------------
    # Methods
    # ------------------------
    def __len__(self) -> int:
        return len(self.data_frame)

    def log_data_message(self, field: str, old_value, new_value) -> None:
        message = f"In DataRecords field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def populate_object(
        self,
        parameter_list: List[str],
        data_formats: Dict[str, str],
        data_lines_list: List[str],
    ) -> Self:
        data_record_list = [split_string_with_quotes(s) for s in data_lines_list]
        df = pd.DataFrame(columns=parameter_list, data=data_record_list)
        df = convert_dataframe(df)

        if "SYTM_01" in df.columns:
            df["SYTM_01"] = df["SYTM_01"].apply(lambda x: f"'{x}'")

        self.data_frame = df
        self.parameter_list = parameter_list
        self.print_formats = data_formats
        return self

    def print_object(self) -> str:
        """Return V3 style CSV representation of the data."""
        df = self.data_frame.copy()

        # Convert Q-parameters to integer
        q_params = [p for p in self.parameter_list if p.startswith("Q")]
        if q_params:
            df = df.astype({p: "int" for p in q_params})

        buffer = io.StringIO()
        df.to_csv(buffer, index=False, sep=",", lineterminator="\n")
        return buffer.getvalue()

    def print_object_old_style(self) -> str:
        # """Return V2 style formatted string representation of the data."""
        formatters = {}
        for key, value in self.print_formats.items():
            width = value
            if key[:5] == "SYTM":
                fmt = "{:>" + str(width) + "}"
                formatters[key] = lambda x, f=fmt: f"'{f.format(x)}'"
            else:
                formatters[key] = lambda x, w=width: f"{float(x):>{w}f}" if x is not None else ""

        return self.data_frame.to_string(
            columns = self.parameter_list,
            index = False,
            header = False,
            formatters = formatters,
        )

def main():

    records = DataRecords()
    records.config = BaseHeader._default_config
    records.logger = BaseHeader._default_logger

    df = pd.DataFrame(
        {
            "PRES_01": [1, 4, 7],
            "TEMP_01": [8.2, 5.6, 2.45],
            "PSAL_01": [31.5, 32.0, 32.88],
        }
    )
    records.data_frame = df
    records.parameter_list = ["PRES_01", "TEMP_01", "PSAL_01"]
    records.print_formats = {"PRES_01": "10.1", "TEMP_01": "10.4", "PSAL_01": "10.4"}

    print(records.print_object())
    print(records.print_object_old_style())

    # Example log usage
    records.log_data_message('TEMP_01', 8.2, 9.1)
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)

if __name__ == "__main__":
    main()
