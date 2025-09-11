from pydantic import Field, field_validator, ConfigDict
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict
from datashop_toolbox.basehdr import BaseHeader


class CruiseHeader(ValidatedBase, BaseHeader):
    """A class to represent a Cruise Header in an ODF object."""

    model_config = ConfigDict(validate_assignment=True)

    country_institute_code: int = Field(default=0, description="Country/Institute code")
    cruise_number: str = ""
    organization: str = ""
    chief_scientist: str = ""
    start_date: str = BaseHeader.SYTM_NULL_VALUE
    end_date: str = BaseHeader.SYTM_NULL_VALUE
    platform: str = ""
    area_of_operation: str = ""
    cruise_name: str = ""
    cruise_description: str = ""

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    # --- Validators to strip whitespace ---
    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip("' ").strip()
        return v

    def log_cruise_message(self, field: str, old_value, new_value) -> None:
        """Log field changes."""
        field = field.upper()
        if field == "COUNTRY_INSTITUTE_CODE":
            message = f"In Cruise Header field {field} was changed from {old_value} to {new_value}"
        else:
            message = f'In Cruise Header field {field} was changed from "{old_value}" to "{new_value}"'
        self.logger.info(message)
        self.shared_log_list.append(message)

    def populate_object(self, cruise_fields: list[str]):
        """Populate fields from header lines like 'KEY = VALUE'."""
        for header_line in cruise_fields:
            tokens = header_line.split("=", maxsplit=1)
            cruise_dict = list_to_dict(tokens)
            for key, value in cruise_dict.items():
                key_lower = key.strip().lower()
                if hasattr(self, key_lower):
                    setattr(self, key_lower, value.strip())
        return self

    def print_object(self, file_version: float = 2.0) -> str:
        """Render cruise header as text."""
        assert isinstance(file_version, float), "file_version must be a float."

        lines = [
            "CRUISE_HEADER",
            f"  COUNTRY_INSTITUTE_CODE = {self.country_institute_code}",
            f"  CRUISE_NUMBER = '{self.cruise_number}'",
            f"  ORGANIZATION = '{self.organization}'",
            f"  CHIEF_SCIENTIST = '{self.chief_scientist}'",
            f"  START_DATE = '{self.start_date}'",
            f"  END_DATE = '{self.end_date}'",
            f"  PLATFORM = '{self.platform}'",
        ]

        if file_version == 3.0:
            lines.append(f"  AREA_OF_OPERATION = '{self.area_of_operation}'")

        lines.extend([
            f"  CRUISE_NAME = '{self.cruise_name}'",
            f"  CRUISE_DESCRIPTION = '{self.cruise_description}'",
        ])

        return "\n".join(lines)


def main():

    cruise = CruiseHeader()

    cruise.config = BaseHeader._default_config
    cruise.logger = BaseHeader._default_logger

    print(cruise.print_object())

    cruise.log_cruise_message("COUNTRY_INSTITUTE_CODE", cruise.country_institute_code, 1805)
    cruise.country_institute_code = 1805

    cruise.log_cruise_message("CHIEF_SCIENTIST", cruise.chief_scientist, "Jeff Jackson")
    cruise.chief_scientist = "Jeff Jackson"

    cruise.log_cruise_message("organization", cruise.organization, "DFO BIO")
    cruise.organization = "DFO BIO"

    print(cruise.print_object())

    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)


if __name__ == "__main__":
    main()
