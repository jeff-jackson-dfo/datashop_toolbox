from pydantic import ConfigDict, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict


class InstrumentHeader(ValidatedBase, BaseHeader):
    """A class to represent an Instrument Header in an ODF object.

    Records identifying information about the instrument used to
    collect an ODF file's data, and provides methods for populating the
    header from parsed ODF text, logging field changes, and rendering
    the header back to ODF-formatted text.

    Attributes:
        instrument_type: Type of instrument, e.g. ``"CTD"``.
        model: Model name or number of the instrument.
        serial_number: Serial number of the instrument.
        description: Free-text description of the instrument.
    """

    model_config = ConfigDict(validate_assignment=True)

    instrument_type: str = ""
    model: str = ""
    serial_number: str = ""
    description: str = ""

    def __init__(self, config=None, **data):
        """Initialize the instrument header.

        Args:
            config: Unused; accepted for interface consistency with
                :class:`~datashop_toolbox.basehdr.BaseHeader`. Call
                :meth:`set_logger_and_config` to attach a logger and
                config after construction.
            **data: Field values used to initialize the Pydantic model.
        """
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        """Attach a shared logger and config to this header.

        Args:
            logger: Logger instance to use for this header.
            config: Logger configuration associated with ``logger``.
        """
        self.logger = logger
        self.config = config

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v):
        """Strip surrounding quotes and whitespace from string fields.

        Args:
            v: Raw value assigned to any field on this model.

        Returns:
            The stripped string if ``v`` is a string, otherwise ``v``
            unchanged.
        """
        if isinstance(v, str):
            return v.strip("' ").strip()
        return v

    def log_instrument_message(self, field: str, old_value: str, new_value: str) -> None:
        """Log a change made to an instrument header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change. An empty
                string is logged as ``''``.
            new_value: Value of the field after the change.

        Raises:
            AssertionError: If ``field`` is not a string.
        """
        assert isinstance(field, str), "Input argument 'field' must be a string."
        if old_value == "":
            old_value = "''"
        message = f"In Instrument Header field {field.upper()} was changed from {old_value} to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def populate_object(self, instrument_fields: list):
        """Populate fields from parsed ODF instrument header lines.

        Args:
            instrument_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from the ``INSTRUMENT_HEADER``
                section of an ODF file.

        Returns:
            This :class:`InstrumentHeader` instance.

        Raises:
            AssertionError: If ``instrument_fields`` is not a list.
        """
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
        """Serialize the instrument header to ODF-formatted text.

        Returns:
            The ``INSTRUMENT_HEADER`` section as ODF-formatted text.
        """
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
