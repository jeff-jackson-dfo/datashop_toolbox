from pydantic import ConfigDict, Field, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, check_datetime, list_to_dict


class GeneralCalHeader(ValidatedBase, BaseHeader):
    """A class to represent a General Cal Header in an ODF object.

    Stores a general (non-polynomial) calibration applied to a single
    parameter — its coefficients, the equation they feed into, and
    related dates and comments — and provides methods for populating
    the header from parsed ODF text, logging field changes, managing
    coefficients and comments, and rendering the header back to
    ODF-formatted text.

    Attributes:
        parameter_code: Code of the parameter the calibration applies
            to, e.g. ``"PSAR_01"``.
        calibration_type: Type of calibration, e.g. ``"Linear"``.
        calibration_date: Date/time the calibration was performed, in
            ODF SYTM format.
        application_date: Date/time the calibration was applied, in ODF
            SYTM format.
        number_coefficients: Number of calibration coefficients.
        coefficients: Calibration coefficients.
        calibration_equation: Equation the coefficients are used in,
            e.g. ``"y = mx + b"``.
        calibration_comments: Free-text comments about the calibration.
    """

    model_config = ConfigDict(validate_assignment=True)

    parameter_code: str = ""
    calibration_type: str = ""
    calibration_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    application_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    number_coefficients: int = 0
    coefficients: list[float] = Field(default_factory=list)
    calibration_equation: str = ""
    calibration_comments: list[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        """Initialize the general calibration header.

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
        """Normalize the parameter code to a stripped, upper-case string.

        Args:
            v: Raw value assigned to ``parameter_code``.

        Returns:
            The stripped, upper-cased string if ``v`` is a string,
            otherwise ``v`` unchanged.
        """
        if isinstance(v, str):
            return v.strip("' ").upper()
        return v

    @field_validator("calibration_type", mode="before")
    @classmethod
    def strip_cal_type(cls, v):
        """Strip surrounding quotes and whitespace from the calibration type.

        Args:
            v: Raw value assigned to ``calibration_type``.

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
            v = check_datetime(v)
            return v.strip("' ").upper()
        return v

    @field_validator("number_coefficients", mode="before")
    @classmethod
    def validate_num_coeffs(cls, v):
        """Coerce ``number_coefficients`` to a native Python int.

        Args:
            v: Raw value assigned to ``number_coefficients``. Accepts
                ``None``, a string representation of a number, or any
                value convertible via ``int()``.

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

    @field_validator("coefficients", mode="before")
    @classmethod
    def validate_coefficients(cls, v):
        """Normalize ``coefficients`` to a list of floats.

        Args:
            v: Raw value assigned to ``coefficients``. Accepts
                ``None``, a whitespace-separated string of numbers, or
                an iterable of values convertible to ``float``.

        Returns:
            An empty list if ``v`` is ``None`` or an empty/whitespace
            string; otherwise a list of ``float`` coefficients.
        """
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
        """Strip surrounding quotes and whitespace from the calibration equation.

        Args:
            v: Raw value assigned to ``calibration_equation``.

        Returns:
            The stripped string if ``v`` is a string, otherwise ``v``
            unchanged.
        """
        if isinstance(v, str):
            return v.strip("' ")
        return v

    @field_validator("calibration_comments", mode="before")
    @classmethod
    def validate_comments(cls, v):
        """Normalize ``calibration_comments`` to a list of stripped strings.

        Args:
            v: Raw value assigned to ``calibration_comments``. Accepts
                ``None``, a single string, or an iterable of values.

        Returns:
            An empty list if ``v`` is ``None``; a single-item list if
            ``v`` is a string; otherwise a list with each item
            converted to a stripped string.
        """
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip("' ")]
        return [str(item).strip("' ") for item in v]

    def log_general_message(self, field: str, old_value, new_value) -> None:
        """Log a change made to a general calibration header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.
        """
        message = f"In General Cal Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_coefficient(
        self, general_coefficient: float, general_coefficient_number: int = 0
    ) -> None:
        """Add or replace a coefficient and update ``number_coefficients``.

        Args:
            general_coefficient: Coefficient value to store.
            general_coefficient_number: One-based position of the
                coefficient to replace. If ``0`` (the default) or
                greater than the current number of coefficients,
                ``general_coefficient`` is appended as a new entry
                instead of replacing one.

        Raises:
            AssertionError: If ``general_coefficient`` is not a float,
                ``general_coefficient_number`` is not an integer, or
                ``general_coefficient_number`` is negative.
        """
        assert isinstance(general_coefficient, float), "general_coefficient must be a float."
        assert isinstance(general_coefficient_number, int), (
            "general_coefficient_number must be an integer."
        )
        assert general_coefficient_number >= 0, "general_coefficient_number must be >= 0."
        if general_coefficient_number == 0 or general_coefficient_number > len(self.coefficients):
            self.coefficients.append(general_coefficient)
        else:
            self.coefficients[general_coefficient_number - 1] = general_coefficient
        self.number_coefficients = len(self.coefficients)

    def set_calibration_comment(self, calibration_comment: str, comment_number: int = 0) -> None:
        """Add or replace an entry in ``calibration_comments``.

        Args:
            calibration_comment: Comment text to store. Surrounding
                single quotes and whitespace are stripped.
            comment_number: One-based position of the comment to
                replace. If ``0`` (the default) or greater than the
                current number of comments, ``calibration_comment`` is
                appended as a new entry instead of replacing one.
        """
        calibration_comment = calibration_comment.strip("' ")
        if comment_number == 0 or comment_number > len(self.calibration_comments):
            self.calibration_comments.append(calibration_comment)
        else:
            self.calibration_comments[comment_number - 1] = calibration_comment

    def add_calibration_comment(self, calibration_comment: str) -> None:
        """Append a comment to ``calibration_comments``.

        Args:
            calibration_comment: Comment text to append. Surrounding
                single quotes and whitespace are stripped.
        """
        calibration_comment = calibration_comment.strip("' ")
        self.calibration_comments.append(calibration_comment)

    def populate_object(self, general_cal_fields: list) -> "GeneralCalHeader":
        """Populate fields from parsed ODF general calibration header lines.

        Args:
            general_cal_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from a ``GENERAL_CAL_HEADER``
                section of an ODF file. Repeated ``CALIBRATION_COMMENTS``
                lines are accumulated into ``calibration_comments``.

        Returns:
            This :class:`GeneralCalHeader` instance.

        Raises:
            AssertionError: If ``general_cal_fields`` is not a list.
        """
        assert isinstance(general_cal_fields, list), "general_cal_fields must be a list."
        for header_line in general_cal_fields:
            tokens = header_line.split("=", maxsplit=1)
            general_dict = list_to_dict(tokens)
            for key, value in general_dict.items():
                key = key.strip().upper()
                value = value.strip()
                match key:
                    case "PARAMETER_CODE":
                        self.parameter_code = value
                    case "CALIBRATION_TYPE":
                        self.calibration_type = value
                    case "CALIBRATION_DATE":
                        self.calibration_date = value
                    case "APPLICATION_DATE":
                        self.application_date = value
                    case "NUMBER_OF_COEFFICIENTS":
                        self.number_coefficients = int(float(value))
                    case "COEFFICIENTS":
                        coefficient_list = value.split()
                        coefficient_floats = [
                            float(coefficient) for coefficient in coefficient_list
                        ]
                        self.coefficients = coefficient_floats
                        self.number_coefficients = len(coefficient_floats)
                    case "CALIBRATION_EQUATION":
                        self.calibration_equation = value
                    case "CALIBRATION_COMMENTS":
                        self.add_calibration_comment(value)
        return self

    def print_object(self) -> str:
        """Serialize the general calibration header to ODF-formatted text.

        Returns:
            The ``GENERAL_CAL_HEADER`` section as ODF-formatted text,
            with coefficients rendered in scientific notation and one
            ``CALIBRATION_COMMENTS`` line per entry in
            ``calibration_comments``.
        """
        lines = [
            "GENERAL_CAL_HEADER",
            f"  PARAMETER_CODE = '{self.parameter_code}'",
            f"  CALIBRATION_TYPE = '{self.calibration_type}'",
            f"  CALIBRATION_DATE = '{self.calibration_date}'",
            f"  APPLICATION_DATE = '{self.application_date}'",
            f"  NUMBER_OF_COEFFICIENTS = {self.number_coefficients}",
            "  COEFFICIENTS = " + " ".join(f"{coef:.8e}" for coef in self.coefficients),
            f"  CALIBRATION_EQUATION = '{self.calibration_equation}'",
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
    general_header.parameter_code = "PSAR_01"
    general_header.calibration_type = "Linear"
    general_header.calibration_date = "28-May-2020 00:00:00.00"
    general_header.application_date = "14-Oct-2020 23:59:59.99"
    general_header.number_coefficients = 2
    general_header.coefficients = [0.75, 1.05834]
    general_header.calibration_equation = "y = mx + b"
    general_header.set_calibration_comment("This is a comment")
    general_header.log_general_message(
        "calibration_equation", general_header.calibration_equation, "Y = X^2 + MX + B"
    )
    general_header.set_coefficient(3.5, 1)
    print(general_header.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)
    print()


if __name__ == "__main__":
    main()
