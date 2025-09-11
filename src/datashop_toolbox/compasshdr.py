from typing import List
from pydantic import Field, field_validator
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase
import datashop_toolbox.validated_base as odfutils

class CompassCalHeader(ValidatedBase, BaseHeader):
    """ A class to represent a Compass Cal Header in an ODF object. """
    
    parameter_code: str = ""
    calibration_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    application_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    directions: List[float] = Field(default_factory=list)
    corrections: List[float] = Field(default_factory=list)

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
            v = odfutils.check_datetime(v)
            return v.strip("' ").upper()
        return v

    @field_validator("directions", "corrections", mode="before")
    @classmethod
    def validate_float_lists(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            return [float(x) for x in v.split()]
        return [float(x) for x in v]

    def log_compass_message(self, field: str, old_value, new_value) -> None:
        message = f"In Compass Cal Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        self.logger.info(message)
        self.shared_log_list.append(message)

    def set_direction(self, direction: float, direction_number: int = 0) -> None:
        assert isinstance(direction, float), "direction must be a float."
        assert 0 <= direction < 360, "direction must be >= 0 and < 360."
        if direction_number == 0 or direction_number > len(self.directions):
            self.directions.append(direction)
        else:
            self.directions[direction_number - 1] = direction

    def set_correction(self, correction: float, correction_number: int = 0) -> None:
        assert isinstance(correction, float), "correction must be a float."
        assert 0 <= correction < 360, "correction must be >= 0 and < 360."
        if correction_number == 0 or correction_number > len(self.corrections):
            self.corrections.append(correction)
        else:
            self.corrections[correction_number - 1] = correction

    def populate_object(self, compass_cal_fields: list) -> "CompassCalHeader":
        assert isinstance(compass_cal_fields, list), "compass_cal_fields must be a list."
        for header_line in compass_cal_fields:
            tokens = header_line.split('=', maxsplit=1)
            compass_dict = odfutils.list_to_dict(tokens)
            for key, value in compass_dict.items():
                key = key.strip().upper()
                value = value.strip()
                match key:
                    case 'PARAMETER_NAME' | 'PARAMETER_CODE':
                        self.parameter_code = value
                    case 'CALIBRATION_DATE':
                        self.calibration_date = value
                    case 'APPLICATION_DATE':
                        self.application_date = value
                    case 'DIRECTIONS':
                        self.directions = [float(x) for x in value.split()]
                    case 'CORRECTIONS':
                        self.corrections = [float(x) for x in value.split()]
        return self

    def print_object(self) -> str:
        lines = [
            "COMPASS_CAL_HEADER",
            f"  PARAMETER_CODE = '{self.parameter_code}'",
            f"  CALIBRATION_DATE = '{self.calibration_date}'",
            f"  APPLICATION_DATE = '{self.application_date}'",
            "  DIRECTIONS = " + " ".join(f"{d:.8e}" for d in self.directions),
            "  CORRECTIONS = " + " ".join(f"{c:.8e}" for c in self.corrections)
        ]
        return "\n".join(lines)

def main():
    print()
    compass_cal_header = CompassCalHeader()
    print(compass_cal_header.print_object())
    compass_cal_fields = [
        "PARAMETER_NAME = PARAMETER_CODE",
        "PARAMETER_CODE = SOG_01",
        "CALIBRATION_DATE = 25-mar-2021 00:00:00.00",
        "APPLICATION_DATE = 31-jan-2022 00:00:00.00",
        "DIRECTIONS = 0.0 90.0 180.0 270.0",
        "CORRECTIONS = 70.0 0.0 0.0 0.0"
    ]
    compass_cal_header.populate_object(compass_cal_fields)
    print(compass_cal_header.print_object())
    print()

if __name__ == "__main__":
    main()
