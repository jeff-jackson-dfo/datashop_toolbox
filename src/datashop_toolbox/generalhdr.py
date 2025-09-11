from typing import List
from pydantic import Field, field_validator, ConfigDict
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict, check_datetime

class GeneralCalHeader(ValidatedBase, BaseHeader):
    """ A class to represent a General Cal Header in an ODF object. """

    model_config = ConfigDict(validate_assignment=True)

    parameter_code: str = ""
    calibration_type: str = ""
    calibration_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    application_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    number_coefficients: int = 0
    coefficients: List[float] = Field(default_factory=list)
    calibration_equation: str = ""
    calibration_comments: List[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    @field_validator("parameter_code", mode="before")
    @classmethod
    def strip_param_code(cls, v):
        if isinstance(v, str):
            return v.strip("' ").upper()
        return v

    @field_validator("calibration_type", mode="before")
    @classmethod
    def strip_cal_type(cls, v):
        if isinstance(v, str):
            return v.strip("' ")
        return v

    @field_validator("calibration_date", "application_date", mode="before")
    @classmethod
    def validate_dates(cls, v):
        if isinstance(v, str):
            v = check_datetime(v)
            return v.strip("' ").upper()
        return v

    @field_validator("number_coefficients", mode="before")
    @classmethod
    def validate_num_coeffs(cls, v):
        if v is None:
            return 0
        if isinstance(v, str):
            return int(float(v.strip()))
        return int(v)

    @field_validator("coefficients", mode="before")
    @classmethod
    def validate_coefficients(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            return [float(x) for x in v.split()]
        return [float(x) for x in v]

    @field_validator("calibration_equation", mode="before")
    @classmethod
    def strip_cal_eqn(cls, v):
        if isinstance(v, str):
            return v.strip("' ")
        return v

    @field_validator("calibration_comments", mode="before")
    @classmethod
    def validate_comments(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip("' ")]
        return [str(item).strip("' ") for item in v]

    def log_general_message(self, field: str, old_value, new_value) -> None:
        message = f"In General Cal Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        self.logger.info(message)
        self.shared_log_list.append(message)

    def set_coefficient(self, general_coefficient: float, general_coefficient_number: int = 0) -> None:
        assert isinstance(general_coefficient, float), "general_coefficient must be a float."
        assert isinstance(general_coefficient_number, int), "general_coefficient_number must be an integer."
        assert general_coefficient_number >= 0, "general_coefficient_number must be >= 0."
        if general_coefficient_number == 0 or general_coefficient_number > len(self.coefficients):
            self.coefficients.append(general_coefficient)
        else:
            self.coefficients[general_coefficient_number - 1] = general_coefficient
        self.number_coefficients = len(self.coefficients)

    def set_calibration_comment(self, calibration_comment: str, comment_number: int = 0) -> None:
        calibration_comment = calibration_comment.strip("' ")
        if comment_number == 0 or comment_number > len(self.calibration_comments):
            self.calibration_comments.append(calibration_comment)
        else:
            self.calibration_comments[comment_number - 1] = calibration_comment

    def add_calibration_comment(self, calibration_comment: str) -> None:
        calibration_comment = calibration_comment.strip("' ")
        self.calibration_comments.append(calibration_comment)

    def populate_object(self, general_cal_fields: list) -> "GeneralCalHeader":
        assert isinstance(general_cal_fields, list), "general_cal_fields must be a list."
        for header_line in general_cal_fields:
            tokens = header_line.split('=', maxsplit=1)
            general_dict = list_to_dict(tokens)
            for key, value in general_dict.items():
                key = key.strip().upper()
                value = value.strip()
                match key:
                    case 'PARAMETER_CODE':
                        self.parameter_code = value
                    case 'CALIBRATION_TYPE':
                        self.calibration_type = value
                    case 'CALIBRATION_DATE':
                        self.calibration_date = value
                    case 'APPLICATION_DATE':
                        self.application_date = value
                    case 'NUMBER_OF_COEFFICIENTS':
                        self.number_coefficients = int(float(value))
                    case 'COEFFICIENTS':
                        coefficient_list = value.split()
                        coefficient_floats = [float(coefficient) for coefficient in coefficient_list]
                        self.coefficients = coefficient_floats
                        self.number_coefficients = len(coefficient_floats)
                    case 'CALIBRATION_EQUATION':
                        self.calibration_equation = value
                    case 'CALIBRATION_COMMENTS':
                        self.add_calibration_comment(value)
        return self

    def print_object(self) -> str:
        lines = [
            "GENERAL_CAL_HEADER",
            f"  PARAMETER_CODE = '{self.parameter_code}'",
            f"  CALIBRATION_TYPE = '{self.calibration_type}'",
            f"  CALIBRATION_DATE = '{self.calibration_date}'",
            f"  APPLICATION_DATE = '{self.application_date}'",
            f"  NUMBER_OF_COEFFICIENTS = {self.number_coefficients}",
            "  COEFFICIENTS = " + " ".join("{:.8e}".format(coef) for coef in self.coefficients),
            f"  CALIBRATION_EQUATION = '{self.calibration_equation}'"
        ]
        for comment in self.calibration_comments:
            lines.append(f"  CALIBRATION_COMMENTS = '{comment}'")
        return "\n".join(lines)

def main():
    print()
    general_header = GeneralCalHeader()
    general_header.config = BaseHeader._default_config
    general_header.logger = BaseHeader._default_logger
    print(general_header.print_object())
    general_header.parameter_code = 'PSAR_01'
    general_header.calibration_type = 'Linear'
    general_header.calibration_date = '28-May-2020 00:00:00.00'
    general_header.application_date = '14-Oct-2020 23:59:59.99'
    general_header.number_coefficients = 2
    general_header.coefficients = [0.75, 1.05834]
    general_header.calibration_equation = 'y = mx + b'
    general_header.set_calibration_comment('This is a comment')
    general_header.log_general_message('calibration_equation', general_header.calibration_equation, 'Y = X^2 + MX + B')
    general_header.set_coefficient(3.5, 1)
    print(general_header.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)
    print()

if __name__ == "__main__":
    main()
