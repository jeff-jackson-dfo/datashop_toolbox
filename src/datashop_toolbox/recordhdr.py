from typing import Any

from pydantic import ConfigDict, Field, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict


class RecordHeader(ValidatedBase, BaseHeader):
    """A class to represent a Record Header in an ODF object.

    Stores counts of the various header sections and data cycles
    contained in an ODF file, and provides methods for populating the
    header from parsed ODF text, logging field changes, and rendering
    the header back to ODF-formatted text.

    Attributes:
        num_calibration: Number of calibration headers in the file.
        num_swing: Number of compass swing (calibration) headers in the
            file.
        num_history: Number of history headers in the file.
        num_cycle: Number of data cycles (records) in the file.
        num_param: Number of parameter headers in the file.
    """

    model_config = ConfigDict(validate_assignment=True)

    num_calibration: int = Field(default=0)
    num_swing: int = Field(default=0)
    num_history: int = Field(default=0)
    num_cycle: int = Field(default=0)
    num_param: int = Field(default=0)

    def __init__(self, config=None, **data):
        """Initialize the record header.

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

    @field_validator(
        "num_calibration", "num_swing", "num_history", "num_cycle", "num_param", mode="before"
    )
    @classmethod
    def validate_ints(cls, v):
        """Coerce a count field to a native Python int.

        Args:
            v: Raw value assigned to one of the record count fields.
                Accepts ``None``, a string representation of a number,
                or any value convertible via ``int()``.

        Returns:
            ``0`` if ``v`` is ``None``; otherwise ``v`` converted to an
            ``int`` (via ``float`` first when ``v`` is a string, to
            tolerate values like ``"5.0"``).
        """
        if v is None:
            return 0
        if isinstance(v, str):
            return int(float(v.strip()))
        return int(v)

    def log_record_message(self, field: str, old_value: Any, new_value: Any) -> None:
        """Log a change made to a record header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.

        Raises:
            AssertionError: If ``field`` is not a string.
        """
        assert isinstance(field, str), "Input argument 'field' must be a string."
        message = (
            f"In Record Header field {field.upper()} was changed from {old_value} to {new_value}"
        )
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def populate_object(self, record_fields: list) -> "RecordHeader":
        """Populate fields from parsed ODF record header lines.

        Args:
            record_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from the ``RECORD_HEADER``
                section of an ODF file.

        Returns:
            This :class:`RecordHeader` instance.

        Raises:
            AssertionError: If ``record_fields`` is not a list.
        """
        assert isinstance(record_fields, list), "Input argument 'record_fields' must be a list."
        for record_line in record_fields:
            tokens = record_line.split("=", maxsplit=1)
            record_dict = list_to_dict(tokens)
            for key, value in record_dict.items():
                key = key.strip().lower()
                value = int(float(value))
                match key:
                    case "num_calibration":
                        self.num_calibration = value
                    case "num_swing":
                        self.num_swing = value
                    case "num_history":
                        self.num_history = value
                    case "num_cycle":
                        self.num_cycle = value
                    case "num_param":
                        self.num_param = value
        return self

    def print_object(self) -> str:
        """Serialize the record header to ODF-formatted text.

        Returns:
            The ``RECORD_HEADER`` section as ODF-formatted text.
        """
        lines = [
            "RECORD_HEADER",
            f"  NUM_CALIBRATION = {self.num_calibration}",
            f"  NUM_HISTORY = {self.num_history}",
            f"  NUM_SWING = {self.num_swing}",
            f"  NUM_PARAM = {self.num_param}",
            f"  NUM_CYCLE = {self.num_cycle}",
        ]
        return "\n".join(lines)


def main():
    record_header = RecordHeader()
    record_header.config = BaseHeader._default_config
    record_header.logger = BaseHeader._default_logger

    print(record_header.print_object())
    record_fields = [
        "NUM_CALIBRATION = 1",
        "NUM_HISTORY = 3",
        "NUM_SWING = 0",
        "NUM_PARAM = 5",
        "NUM_CYCLE = 1000",
    ]
    record_header.populate_object(record_fields)
    print(record_header.print_object())
    record_header.log_record_message("num_param", record_header.num_param, 17)
    record_header.num_param = 17
    print(record_header.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)


if __name__ == "__main__":
    main()
