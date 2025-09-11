from typing import List
from pydantic import Field, field_validator, ConfigDict
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict, check_string, check_datetime

class PolynomialCalHeader(ValidatedBase, BaseHeader):
    """ A class to represent a Polynomial Calibration Header in an ODF object. """

    model_config = ConfigDict(validate_assignment=True)

    parameter_code: str = ""
    calibration_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    application_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    number_coefficients: int = 0
    coefficients: List[float] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    @field_validator("parameter_code", mode="before")
    @classmethod
    def strip_param_code(cls, v):
        if isinstance(v, str):
            return v.strip("' ")
        return v

    @field_validator("calibration_date", "application_date", mode="before")
    @classmethod
    def validate_dates(cls, v):
        if isinstance(v, str):
            return check_datetime(v).strip("' ")
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
            return [float(check_string(x)) for x in v.split()]
        return [float(x) for x in v]

    def log_poly_message(self, field: str, old_value, new_value) -> None:
        message = f"In Polynomial Cal Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        self.logger.info(message)
        self.shared_log_list.append(message)

    def set_coefficient(self, coefficient: float, coefficient_number: int = 0) -> None:
        assert isinstance(coefficient, float), "coefficient must be a float."
        assert isinstance(coefficient_number, int), "coefficient_number must be an integer."
        assert coefficient_number >= 0, "coefficient_number must be >= 0."
        if coefficient_number == 0 or coefficient_number > len(self.coefficients):
            self.coefficients.append(coefficient)
        else:
            self.coefficients[coefficient_number - 1] = coefficient
        self.number_coefficients = len(self.coefficients)

    def populate_object(self, polynomial_cal_fields: list) -> "PolynomialCalHeader":
        assert isinstance(polynomial_cal_fields, list), "polynomial_cal_fields must be a list."
        for header_line in polynomial_cal_fields:
            tokens = header_line.split('=', maxsplit=1)
            poly_dict = list_to_dict(tokens)
            for key, value in poly_dict.items():
                key = key.strip().upper()
                value = value.strip("' ")
                match key:
                    case 'PARAMETER_NAME' | 'PARAMETER_CODE':
                        self.parameter_code = value
                    case 'CALIBRATION_DATE':
                        self.calibration_date = value
                    case 'APPLICATION_DATE':
                        self.application_date = value
                    case 'NUMBER_OF_COEFFICIENTS' | 'NUMBER_COEFFICIENTS':
                        self.number_coefficients = int(float(value))
                    case 'COEFFICIENTS':
                        coefficient_list = value.split()
                        self.coefficients = [float(check_string(coef)) for coef in coefficient_list]
                        self.number_coefficients = len(self.coefficients)
        return self

    def print_object(self) -> str:
        lines = [
            "POLYNOMIAL_CAL_HEADER",
            f"  PARAMETER_CODE = '{self.parameter_code}'",
            f"  CALIBRATION_DATE = '{check_datetime(self.calibration_date)}'",
            f"  APPLICATION_DATE = '{check_datetime(self.application_date)}'",
            f"  NUMBER_COEFFICIENTS = {self.number_coefficients}",
            "  COEFFICIENTS = " + " ".join(f"{float(coef):.8e}" for coef in self.coefficients)
        ]
        return "\n".join(lines)

def main():

    print()
    poly1 = PolynomialCalHeader()
    poly1.config = BaseHeader._default_config
    poly1.logger = BaseHeader._default_logger

    print(poly1.print_object())
    poly1.parameter_code = 'PRES_01'
    poly1.calibration_date = '11-JUN-1995 05:35:46.82'
    poly1.application_date = '11-JUN-1995 05:35:46.82'
    poly1.number_coefficients = 2
    poly1.coefficients = [0.60000000e+01, 0.15000001e+00]
    print(poly1.print_object())

    poly2 = PolynomialCalHeader()
    poly2.config = BaseHeader._default_config
    poly2.logger = BaseHeader._default_logger
    poly2.parameter_code = 'TEMP_01'
    poly2.calibration_date = '11-JUN-1995 05:35:46.83'
    poly2.application_date = '11-JUN-1995 05:35:46.83'
    poly2.number_coefficients = 4
    poly2.coefficients = [0.0, 80.0, 0.60000000e+01, 0.15000001e+00]
    poly2.log_poly_message('coefficient 2', poly2.coefficients[1], 9.750)
    poly2.set_coefficient(9.750, 2)
    print(poly2.print_object())

    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)
    print()

if __name__ == "__main__":
    main()
