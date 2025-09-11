from typing import Any
from pydantic import field_validator, ConfigDict
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict, check_datetime, check_string

class ParameterHeader(ValidatedBase, BaseHeader):
    """A class to represent a Parameter Header in an ODF object."""

    model_config = ConfigDict(validate_assignment=True)

    type: str = ""
    name: str = ""
    units: str = ""
    code: str = ""
    wmo_code: str = ""
    null_string: str = ""
    print_field_order: int = int(BaseHeader.NULL_VALUE)
    print_field_width: int = int(BaseHeader.NULL_VALUE)
    print_decimal_places: int = int(BaseHeader.NULL_VALUE)
    angle_of_section: float = BaseHeader.NULL_VALUE
    magnetic_variation: float= BaseHeader.NULL_VALUE
    depth: float = BaseHeader.NULL_VALUE
    minimum_value: Any = None
    maximum_value: Any = None
    number_valid: int = 0
    number_null: int = 0

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip("' ").strip()
        return v

    def log_parameter_message(self, field: str, old_value: str, new_value: str) -> None:
        assert isinstance(field, str), "Input argument 'field' must be a string."
        message = f"In Parameter Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        self.logger.info(message)
        self.shared_log_list.append(message)

    @staticmethod
    def is_float_and_int(value) -> bool:
        try:
            # Attempt to convert the string to a float
            f = float(value)
            # Check if the float is an integer (i.e., has no fractional part)
            return f.is_integer()
        except ValueError:
            # If conversion to float fails, it's not a valid number (int or float)
            return False

    def populate_object(self, parameter_fields: list) -> "ParameterHeader":
        assert isinstance(parameter_fields, list), "Input argument 'parameter_fields' must be a list."
        for header_line in parameter_fields:
            tokens = header_line.split('=', maxsplit=1)
            parameter_dict = list_to_dict(tokens)
            for key, value in parameter_dict.items():
                key = key.strip().lower()
                value = value.strip("' ")
                match key:
                    case 'type':
                        self.type = value
                    case 'name':
                        self.name = value
                    case 'units':
                        self.units = value
                    case 'code':
                        self.code = value
                    case 'wmo_code':
                        self.wmo_code = value
                        if self.code == "":
                            self.code = value
                    case 'null_value':
                        self.null_string = value
                    case 'print_field_order':
                        self.print_field_order = int(float(value))
                    case 'print_field_width':
                        self.print_field_width = int(float(value))
                    case 'print_decimal_places':
                        self.print_decimal_places = int(float(value))
                    case 'angle_of_section':
                        self.angle_of_section = float(value)
                    case 'magnetic_variation':
                        self.magnetic_variation = float(value)
                    case 'depth':
                        value = check_string(value)
                        self.depth = float(value)
                    case 'minimum_value':
                        if self.type == 'SYTM':
                            self.minimum_value = check_datetime(value) if value else BaseHeader.SYTM_NULL_VALUE
                        elif self.type == 'INTE':
                            if self.is_float_and_int(value):
                                self.minimum_value = int(float(value))
                            else:
                                raise ValueError(f"Invalid integer value: {value}")
                        elif self.type in ('SING', 'DOUB'):
                            self.minimum_value = float(value)
                        else:
                            self.minimum_value = BaseHeader.NULL_VALUE
                    case 'maximum_value':
                        if self.type == 'SYTM':
                            self.maximum_value = check_datetime(value) if value else BaseHeader.SYTM_NULL_VALUE
                        elif self.type == 'INTE':
                            if self.is_float_and_int(value):
                                self.maximum_value = int(float(value))
                            else:
                                raise ValueError(f"Invalid integer value: {value}")
                        elif self.type in ('SING', 'DOUB'):
                            self.maximum_value = float(value)
                        else:
                            self.maximum_value = BaseHeader.NULL_VALUE
                    case 'number_valid':
                        self.number_valid = int(float(value))
                    case 'number_null':
                        self.number_null = int(float(value))
        return self

    def print_object(self, file_version: float = 2.0) -> str:
        assert file_version >= 2.0, f"File version must be >= 2.0 but is: {file_version}"
        lines = [
            "PARAMETER_HEADER",
            f"  TYPE = '{self.type}'",
            f"  NAME = '{self.name}'",
            f"  UNITS = '{self.units}'",
            f"  CODE = '{self.code}'"
        ]
        if self.wmo_code:
            lines.append(f"  WMO_CODE = '{self.wmo_code}'")
        if self.type == "SYTM":
            lines.append(f"  NULL_VALUE = '{check_datetime(self.null_string)}'")
        else:
            lines.append(f"  NULL_VALUE = {self.null_string}")
        if file_version == 3 and self.print_field_order is not None:
            lines.append(f"  PRINT_FIELD_ORDER = {self.print_field_order}")
        if self.print_field_width is not None:
            lines.append(f"  PRINT_FIELD_WIDTH = {self.print_field_width}")
        if self.print_decimal_places is not None:
            lines.append(f"  PRINT_DECIMAL_PLACES = {self.print_decimal_places}")
        if self.angle_of_section is not None:
            lines.append(f"  ANGLE_OF_SECTION = {self.angle_of_section:.1f}")
        if self.magnetic_variation is not None:
            lines.append(f"  MAGNETIC_VARIATION = {self.magnetic_variation:.1f}")
        if self.depth is not None:
            lines.append(f"  DEPTH = {self.depth:.1f}")
        # Handle minimum/maximum values
        if self.units in ("GMT", "UTC") or self.type == "SYTM":
            lines.append(f"  MINIMUM_VALUE = '{check_datetime(self.minimum_value)}'")
            lines.append(f"  MAXIMUM_VALUE = '{check_datetime(self.maximum_value)}'")
        else:
            lines.append(f"  MINIMUM_VALUE = {self.minimum_value if self.minimum_value is not None else BaseHeader.NULL_VALUE}")
            lines.append(f"  MAXIMUM_VALUE = {self.maximum_value if self.maximum_value is not None else BaseHeader.NULL_VALUE}")
        if self.number_valid is not None:
            lines.append(f"  NUMBER_VALID = {self.number_valid}")
        if self.number_null is not None:
            lines.append(f"  NUMBER_NULL = {self.number_null}")
        return "\n".join(lines)

def main():

    param2 = ParameterHeader(
        type='SYTM',
        name='SYTM',
        units='UTC',
        code='SYTM_01',
        wmo_code='SYTM',
        null_string=f'{BaseHeader.SYTM_NULL_VALUE}',
        print_field_width=23,
        print_decimal_places=0,
        angle_of_section=0.0,
        magnetic_variation=0.0,
        depth=0.0,
        minimum_value='03-MAY-2025 00:47:41.73',
        maximum_value='03-MAY-2025 01:54:07.73',
        number_valid=1064,
        number_null=643
    )
    print(param2.print_object())

    param1 = ParameterHeader()
    param1.type="DOUB"
    param1.name='Pressure'
    param1.units='Decibars'
    param1.code='PRES_01'
    param1.wmo_code='PRES'
    param1.null_string=f'{BaseHeader.NULL_VALUE}'
    param1.print_field_width=10
    param1.print_decimal_places=3
    param1.angle_of_section=0.0
    param1.magnetic_variation=0.0
    # param1.depth = check_string('0.50000000D+02')
    param1.depth=0.50000000e+02
    param1.minimum_value=2.177
    param1.maximum_value=176.5
    param1.number_valid=1064
    param1.number_null=643
    print(param1.print_object())


if __name__ == "__main__":
    main()
