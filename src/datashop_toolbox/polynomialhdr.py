from pydantic import ConfigDict, Field, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import (
    ValidatedBase,
    check_datetime,
    check_string,
    list_to_dict,
)


class PolynomialCalHeader(ValidatedBase, BaseHeader):
    """A class to represent a Polynomial Calibration Header in an ODF object.

    Stores the coefficients of a polynomial calibration applied to a
    single parameter, along with when the calibration was performed and
    applied, and provides methods for populating the header from parsed
    ODF text, logging field changes, managing coefficients, and
    rendering the header back to ODF-formatted text.

    Attributes:
        parameter_code: Code of the parameter the calibration applies
            to, e.g. ``"PRES_01"``.
        calibration_date: Date/time the calibration was performed, in
            ODF SYTM format.
        application_date: Date/time the calibration was applied, in ODF
            SYTM format.
        number_coefficients: Number of polynomial coefficients.
        coefficients: Polynomial coefficients, in ascending order of
            power.
    """

    model_config = ConfigDict(validate_assignment=True)

    parameter_code: str = ""
    calibration_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    application_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    number_coefficients: int = 0
    coefficients: list[float] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        """Initialize the polynomial calibration header.

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
            The value converted to a validated, stripped ODF SYTM
            date/time string if ``v`` is a string, otherwise ``v``
            unchanged.
        """
        if isinstance(v, str):
            return check_datetime(v).strip("' ")
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
            return [float(check_string(x)) for x in v.split()]
        return [float(x) for x in v]

    def log_poly_message(self, field: str, old_value, new_value) -> None:
        """Log a change made to a polynomial calibration header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.
        """
        message = f"In Polynomial Cal Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_coefficient(self, coefficient: float, coefficient_number: int = 0) -> None:
        """Add or replace a coefficient and update ``number_coefficients``.

        Args:
            coefficient: Coefficient value to store.
            coefficient_number: One-based position of the coefficient
                to replace. If ``0`` (the default) or greater than the
                current number of coefficients, ``coefficient`` is
                appended as a new entry instead of replacing one.

        Raises:
            AssertionError: If ``coefficient`` is not a float,
                ``coefficient_number`` is not an integer, or
                ``coefficient_number`` is negative.
        """
        assert isinstance(coefficient, float), "coefficient must be a float."
        assert isinstance(coefficient_number, int), "coefficient_number must be an integer."
        assert coefficient_number >= 0, "coefficient_number must be >= 0."
        if coefficient_number == 0 or coefficient_number > len(self.coefficients):
            self.coefficients.append(coefficient)
        else:
            self.coefficients[coefficient_number - 1] = coefficient
        self.number_coefficients = len(self.coefficients)

    def populate_object(self, polynomial_cal_fields: list) -> "PolynomialCalHeader":
        """Populate fields from parsed ODF polynomial calibration header lines.

        Args:
            polynomial_cal_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from a ``POLYNOMIAL_CAL_HEADER``
                section of an ODF file.

        Returns:
            This :class:`PolynomialCalHeader` instance.

        Raises:
            AssertionError: If ``polynomial_cal_fields`` is not a list.
        """
        assert isinstance(polynomial_cal_fields, list), "polynomial_cal_fields must be a list."
        for header_line in polynomial_cal_fields:
            tokens = header_line.split("=", maxsplit=1)
            poly_dict = list_to_dict(tokens)
            for key, value in poly_dict.items():
                key = key.strip().upper()
                value = value.strip("' ")
                match key:
                    case "PARAMETER_NAME" | "PARAMETER_CODE":
                        self.parameter_code = value
                    case "CALIBRATION_DATE":
                        self.calibration_date = value
                    case "APPLICATION_DATE":
                        self.application_date = value
                    case "NUMBER_OF_COEFFICIENTS" | "NUMBER_COEFFICIENTS":
                        self.number_coefficients = int(float(value))
                    case "COEFFICIENTS":
                        coefficient_list = value.split()
                        self.coefficients = [float(check_string(coef)) for coef in coefficient_list]
                        self.number_coefficients = len(self.coefficients)
        return self

    def print_object(self) -> str:
        """Serialize the polynomial calibration header to ODF-formatted text.

        Returns:
            The ``POLYNOMIAL_CAL_HEADER`` section as ODF-formatted
            text, with coefficients rendered in scientific notation.
        """
        lines = [
            "POLYNOMIAL_CAL_HEADER",
            f"  PARAMETER_CODE = '{self.parameter_code}'",
            f"  CALIBRATION_DATE = '{check_datetime(self.calibration_date)}'",
            f"  APPLICATION_DATE = '{check_datetime(self.application_date)}'",
            f"  NUMBER_COEFFICIENTS = {self.number_coefficients}",
            "  COEFFICIENTS = " + " ".join(f"{float(coef):.8e}" for coef in self.coefficients),
        ]
        return "\n".join(lines)


def main():

    print()
    poly1 = PolynomialCalHeader()
    poly1.config = BaseHeader._default_config
    poly1.logger = BaseHeader._default_logger

    print(poly1.print_object())
    poly1.parameter_code = "PRES_01"
    poly1.calibration_date = "11-JUN-1995 05:35:46.82"
    poly1.application_date = "11-JUN-1995 05:35:46.82"
    poly1.number_coefficients = 2
    poly1.coefficients = [0.60000000e01, 0.15000001e00]
    print(poly1.print_object())

    poly2 = PolynomialCalHeader()
    poly2.config = BaseHeader._default_config
    poly2.logger = BaseHeader._default_logger
    poly2.parameter_code = "TEMP_01"
    poly2.calibration_date = "11-JUN-1995 05:35:46.83"
    poly2.application_date = "11-JUN-1995 05:35:46.83"
    poly2.number_coefficients = 4
    poly2.coefficients = [0.0, 80.0, 0.60000000e01, 0.15000001e00]
    poly2.log_poly_message("coefficient 2", poly2.coefficients[1], 9.750)
    poly2.set_coefficient(9.750, 2)
    print(poly2.print_object())

    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)
    print()


if __name__ == "__main__":
    main()
