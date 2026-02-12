from pydantic import ConfigDict, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict


class InstrumentHeader(ValidatedBase, BaseHeader):
    """A class to represent an Instrument Header in an ODF object."""

    model_config = ConfigDict(validate_assignment=True)

    instrument_type: str = ""
    model: str = ""
    serial_number: str = ""
    description: str = ""

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

    def log_instrument_message(self, field: str, old_value: str, new_value: str) -> None:
        assert isinstance(field, str), "Input argument 'field' must be a string."
        if old_value == "":
            old_value = "''"
        message = f"In Instrument Header field {field.upper()} was changed from {old_value} to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def populate_object(self, instrument_fields: list):
        assert isinstance(instrument_fields, list), (
            "Input argument 'instrument_fields' must be a list."
        )
        for header_line in instrument_fields:
            tokens = header_line.split("=", maxsplit=1)
            instrument_dict = list_to_dict(tokens)
            for key, value in instrument_dict.items():
                key = key.strip().lower()
                value = value.strip("' ")
                match key:
                    case "inst_type":
                        self.instrument_type = value
                    case "model":
                        self.model = value
                    case "serial_number":
                        self.serial_number = value
                    case "description":
                        self.description = value
        return self

    def print_object(self) -> str:
        lines = [
            "INSTRUMENT_HEADER",
            f"  INST_TYPE = '{self.instrument_type}'",
            f"  MODEL = '{self.model}'",
            f"  SERIAL_NUMBER = '{self.serial_number}'",
            f"  DESCRIPTION = '{self.description}'",
        ]
        return "\n".join(lines)


def main():
    instrument_header = InstrumentHeader()
    instrument_header.config = BaseHeader._default_config
    instrument_header.logger = BaseHeader._default_logger

    # Set logger/config if needed, e.g.:
    # instrument_header.set_logger_and_config(BaseHeader._default_logger, BaseHeader._default_config)
    print(instrument_header.print_object())
    instrument_header.instrument_type = "CTD"
    instrument_header.model = "SBE 9"
    instrument_header.serial_number = "12345"
    instrument_header.log_instrument_message(
        "description", instrument_header.description, "SeaBird CTD"
    )
    instrument_header.description = "SeaBird CTD"
    print(instrument_header.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)


if __name__ == "__main__":
    main()
