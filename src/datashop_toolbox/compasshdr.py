from pydantic import ConfigDict, Field, field_validator

import datashop_toolbox.validated_base as odfutils
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase


class CompassCalHeader(ValidatedBase, BaseHeader):
    """A class to represent a Compass Cal Header in an ODF object.

    Stores a compass calibration for a single parameter as paired lists
    of directions and their corresponding corrections, along with when
    the calibration was performed and applied, and provides methods for
    populating the header from parsed ODF text, logging field changes,
    managing directions and corrections, and rendering the header back
    to ODF-formatted text.

    Attributes:
        parameter_code: Code of the parameter the calibration applies
            to, e.g. ``"SOG_01"``.
        calibration_date: Date/time the calibration was performed, in
            ODF SYTM format.
        application_date: Date/time the calibration was applied, in ODF
            SYTM format.
        directions: Compass directions, in degrees, at which
            corrections were determined.
        corrections: Corrections, in degrees, corresponding to each
            entry in ``directions``.
    """

    model_config = ConfigDict(validate_assignment=True)

    parameter_code: str = ""
    calibration_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    application_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    directions: list[float] = Field(default_factory=list)
    corrections: list[float] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        """Initialize the compass calibration header.

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

    @field_validator("parameter_code", mode="before")
    @classmethod
    def strip_param_code(cls, v):
        """Strip surrounding quotes and whitespace from the parameter code.

        Args:
            v: Raw value assigned to ``parameter_code``.

        Returns:
            The stripped string if ``v`` is a string, otherwise ``v``
            unchanged.
        """
        if isinstance(v, str):
            return v.strip("' ")
        return v

    @field_validator("calibration_date", "application_date", mode="before")
    @classmethod
    def validate_dates(cls, v):
        """Validate and normalize a calibration or application date.

        Args:
            v: Raw value assigned to ``calibration_date`` or
                ``application_date``.

        Returns:
            The value converted to a validated, stripped, upper-cased
            ODF SYTM date/time string if ``v`` is a string, otherwise
            ``v`` unchanged.
        """
        if isinstance(v, str):
            v = odfutils.check_datetime(v)
            return v.strip("' ").upper()
        return v

    @field_validator("directions", "corrections", mode="before")
    @classmethod
    def validate_float_lists(cls, v):
        """Normalize ``directions``/``corrections`` to a list of floats.

        Args:
            v: Raw value assigned to ``directions`` or ``corrections``.
                Accepts ``None``, a whitespace-separated string of
                numbers, or an iterable of values convertible to
                ``float``.

        Returns:
            An empty list if ``v`` is ``None`` or an empty/whitespace
            string; otherwise a list of ``float`` values.
        """
        if v is None:
            return []
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            return [float(x) for x in v.split()]
        return [float(x) for x in v]

    def log_compass_message(self, field: str, old_value, new_value) -> None:
        """Log a change made to a compass calibration header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.
        """
        message = f"In Compass Cal Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_direction(self, direction: float, direction_number: int = 0) -> None:
        """Add or replace an entry in ``directions``.

        Args:
            direction: Compass direction, in degrees, to store. Must
                satisfy ``0 <= direction < 360``.
            direction_number: One-based position of the direction to
                replace. If ``0`` (the default) or greater than the
                current number of directions, ``direction`` is
                appended as a new entry instead of replacing one.

        Raises:
            AssertionError: If ``direction`` is not a float or is
                outside the range ``[0, 360)``.
        """
        assert isinstance(direction, float), "direction must be a float."
        assert 0 <= direction < 360, "direction must be >= 0 and < 360."
        if direction_number == 0 or direction_number > len(self.directions):
            self.directions.append(direction)
        else:
            self.directions[direction_number - 1] = direction

    def set_correction(self, correction: float, correction_number: int = 0) -> None:
        """Add or replace an entry in ``corrections``.

        Args:
            correction: Correction, in degrees, to store. Must satisfy
                ``0 <= correction < 360``.
            correction_number: One-based position of the correction to
                replace. If ``0`` (the default) or greater than the
                current number of corrections, ``correction`` is
                appended as a new entry instead of replacing one.

        Raises:
            AssertionError: If ``correction`` is not a float or is
                outside the range ``[0, 360)``.
        """
        assert isinstance(correction, float), "correction must be a float."
        assert 0 <= correction < 360, "correction must be >= 0 and < 360."
        if correction_number == 0 or correction_number > len(self.corrections):
            self.corrections.append(correction)
        else:
            self.corrections[correction_number - 1] = correction

    def populate_object(self, compass_cal_fields: list) -> "CompassCalHeader":
        """Populate fields from parsed ODF compass calibration header lines.

        Args:
            compass_cal_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from a ``COMPASS_CAL_HEADER``
                section of an ODF file.

        Returns:
            This :class:`CompassCalHeader` instance.

        Raises:
            AssertionError: If ``compass_cal_fields`` is not a list.
            ValueError: If ``CALIBRATION_DATE`` or ``APPLICATION_DATE``
                does not match the expected ODF SYTM format.
        """
        assert isinstance(compass_cal_fields, list), "compass_cal_fields must be a list."
        for header_line in compass_cal_fields:
            tokens = header_line.split("=", maxsplit=1)
            compass_dict = odfutils.list_to_dict(tokens)
            for key, value in compass_dict.items():
                key = key.strip().upper()
                value = value.strip()
                match key:
                    case "PARAMETER_NAME" | "PARAMETER_CODE":
                        self.parameter_code = value
                    case "CALIBRATION_DATE":
                        try:
                            if BaseHeader.matches_sytm_format(value):
                                self.calibration_date = value
                        except ValueError as ve:
                            raise ValueError(
                                f"Invalid date format: {value}. Expected {BaseHeader.SYTM_FORMAT}"
                            ) from ve
                    case "APPLICATION_DATE":
                        try:
                            if BaseHeader.matches_sytm_format(value):
                                self.application_date = value
                        except ValueError as ve:
                            raise ValueError(
                                f"Invalid date format: {value}. Expected {BaseHeader.SYTM_FORMAT}"
                            ) from ve
                    case "DIRECTIONS":
                        self.directions = [float(x) for x in value.split()]
                    case "CORRECTIONS":
                        self.corrections = [float(x) for x in value.split()]
        return self

    def print_object(self) -> str:
        """Serialize the compass calibration header to ODF-formatted text.

        Returns:
            The ``COMPASS_CAL_HEADER`` section as ODF-formatted text,
            with directions and corrections rendered in scientific
            notation.
        """
        lines = [
            "COMPASS_CAL_HEADER",
            f"  PARAMETER_CODE = '{self.parameter_code}'",
            f"  CALIBRATION_DATE = '{self.calibration_date}'",
            f"  APPLICATION_DATE = '{self.application_date}'",
            "  DIRECTIONS = " + " ".join(f"{d:.8e}" for d in self.directions),
            "  CORRECTIONS = " + " ".join(f"{c:.8e}" for c in self.corrections),
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
        "CORRECTIONS = 70.0 0.0 0.0 0.0",
    ]
    compass_cal_header.populate_object(compass_cal_fields)
    print(compass_cal_header.print_object())
    print()


if __name__ == "__main__":
    main()
