from pydantic import ConfigDict, Field, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict


class CruiseHeader(ValidatedBase, BaseHeader):
    """A class to represent a Cruise Header in an ODF object.

    Stores the metadata that identifies the cruise during which an ODF
    file's data were collected, and provides methods for populating the
    header from parsed ODF text, logging field changes, and rendering
    the header back to ODF-formatted text.

    Attributes:
        country_institute_code: Country/institute code of the organization
            that collected the data.
        cruise_number: Identifier assigned to the cruise.
        organization: Name of the organization that conducted the cruise.
        chief_scientist: Name of the cruise's chief scientist.
        start_date: Cruise start date/time in ODF SYTM format.
        end_date: Cruise end date/time in ODF SYTM format.
        platform: Name of the vessel or platform used for the cruise.
        area_of_operation: Geographic area in which the cruise took place.
            Only written for ODF file version 3.0 and later.
        cruise_name: Descriptive name of the cruise.
        cruise_description: Free-text description of the cruise.
    """

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
        """Initialize the cruise header.

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

    # --- Validators to handle empty dates
    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def handle_empty_dates(cls, v):
        """Replace an empty date string with the ODF SYTM null value.

        Args:
            v: Raw value assigned to ``start_date`` or ``end_date``.

        Returns:
            ``BaseHeader.SYTM_NULL_VALUE`` if ``v`` is an empty or
            whitespace-only string, otherwise ``v`` unchanged.
        """
        # If assigned an empty string, use the SYTM_NULL_VALUE
        if isinstance(v, str) and v.strip() == "":
            return BaseHeader.SYTM_NULL_VALUE
        return v

    # --- Validators to strip whitespace ---
    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v, info):
        """Strip surrounding quotes and whitespace from string fields.

        Args:
            v: Raw value assigned to any field on this model.
            info: Pydantic validation info for the field being set.

        Returns:
            The stripped string if ``v`` is a string, otherwise ``v``
            unchanged.
        """
        if isinstance(v, str):
            return v.strip("' ").strip()
        return v

    def log_cruise_message(self, field: str, old_value, new_value) -> None:
        """Log a change made to a cruise header field.

        Args:
            field: Name of the field that was changed. Matched
                case-insensitively against ``"COUNTRY_INSTITUTE_CODE"``
                to decide whether the logged values are quoted.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.
        """
        field = field.upper()
        if field == "COUNTRY_INSTITUTE_CODE":
            message = f"In Cruise Header field {field} was changed from {old_value} to {new_value}"
        else:
            message = (
                f'In Cruise Header field {field} was changed from "{old_value}" to "{new_value}"'
            )
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def populate_object(self, cruise_fields: list[str]):
        """Populate fields from parsed ODF cruise header lines.

        Args:
            cruise_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from the ``CRUISE_HEADER``
                section of an ODF file.

        Returns:
            This :class:`CruiseHeader` instance.
        """
        for header_line in cruise_fields:
            tokens = header_line.split("=", maxsplit=1)
            cruise_dict = list_to_dict(tokens)
            for key, value in cruise_dict.items():
                key_lower = key.strip().lower()
                if hasattr(self, key_lower):
                    setattr(self, key_lower, value.strip())
        return self

    def print_object(self, file_version: float = 2.0) -> str:
        """Serialize the cruise header to ODF-formatted text.

        Args:
            file_version: ODF output format version. ``AREA_OF_OPERATION``
                is only included in the output for version ``3.0`` and
                later.

        Returns:
            The ``CRUISE_HEADER`` section as ODF-formatted text.

        Raises:
            AssertionError: If ``file_version`` is not a float.
        """
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

        lines.extend(
            [
                f"  CRUISE_NAME = '{self.cruise_name}'",
                f"  CRUISE_DESCRIPTION = '{self.cruise_description}'",
            ]
        )

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
