from pydantic import ConfigDict, Field, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import (
    ValidatedBase,
    check_datetime,
    check_string,
    get_current_date_time,
    list_to_dict,
)


class QualityHeader(ValidatedBase, BaseHeader):
    """A class to represent a Quality Header in an ODF object.

    Records the quality-control tests applied to an ODF file's data and
    any related comments, and provides methods for populating the
    header from parsed ODF text, logging field changes, managing tests
    and comments (including standard boilerplate for quality codes and
    QCFF flag descriptions), and rendering the header back to
    ODF-formatted text.

    Attributes:
        quality_date: Date/time the quality control was performed, in
            ODF SYTM format.
        quality_tests: Descriptions of the quality-control tests that
            were applied.
        quality_comments: Free-text comments about the quality control.
    """

    model_config = ConfigDict(validate_assignment=True)

    quality_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    quality_tests: list[str] = Field(default_factory=list)
    quality_comments: list[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        """Initialize the quality header.

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

    @field_validator("quality_date", mode="before")
    @classmethod
    def validate_quality_date(cls, v):
        """Normalize and validate the quality date.

        Args:
            v: Raw value assigned to ``quality_date``.

        Returns:
            The value converted to a stripped, upper-case, validated
            ODF SYTM date/time string.
        """
        v = check_string(v)
        v = check_datetime(v)
        return v.upper()

    @field_validator("quality_tests", "quality_comments", mode="before")
    @classmethod
    def validate_lists(cls, v):
        """Normalize ``quality_tests``/``quality_comments`` to a list of strings.

        Args:
            v: Raw value assigned to ``quality_tests`` or
                ``quality_comments``. Accepts ``None``, a single
                string, or an iterable of values.

        Returns:
            An empty list if ``v`` is ``None``; a single-item list if
            ``v`` is a string; otherwise a list with each item passed
            through :func:`~datashop_toolbox.validated_base.check_string`.
        """
        if v is None:
            return []
        if isinstance(v, str):
            return [check_string(v)]
        return [check_string(item) for item in v]

    def log_quality_message(self, field: str, old_value: str, new_value: str) -> None:
        """Log a change made to a quality header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.
        """
        message = f"In Quality Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_quality_test(self, quality_test: str, test_number: int = 0) -> None:
        """Add or replace an entry in ``quality_tests``.

        Args:
            quality_test: Test description to store.
            test_number: One-based position of the test to replace. If
                ``0`` (the default) or greater than the current number
                of tests, ``quality_test`` is appended as a new entry
                instead of replacing one.
        """
        quality_test = check_string(quality_test)
        if test_number == 0 or test_number > len(self.quality_tests):
            self.quality_tests.append(quality_test)
        else:
            self.quality_tests[test_number - 1] = quality_test

    def add_quality_test(self, quality_test: str) -> None:
        """Append a quality-control test description to ``quality_tests``.

        Args:
            quality_test: Test description to append.
        """
        quality_test = check_string(quality_test)
        self.quality_tests.append(quality_test)

    def set_quality_comment(self, quality_comment: str, comment_number: int = 0) -> None:
        """Add or replace an entry in ``quality_comments``.

        Args:
            quality_comment: Comment text to store.
            comment_number: One-based position of the comment to
                replace. If ``0`` (the default) or greater than the
                current number of comments, ``quality_comment`` is
                appended as a new entry instead of replacing one.
        """
        quality_comment = check_string(quality_comment)
        if comment_number == 0 or comment_number > len(self.quality_comments):
            self.quality_comments.append(quality_comment)
        else:
            self.quality_comments[comment_number - 1] = quality_comment

    def add_quality_comment(self, quality_comment: str) -> None:
        """Append a comment to ``quality_comments``.

        Args:
            quality_comment: Comment text to append.
        """
        quality_comment = check_string(quality_comment)
        self.quality_comments.append(quality_comment)

    def add_quality_codes(self) -> None:
        """Append the standard quality-code definitions and set the date.

        Sets ``quality_date`` to the current date/time if it is still
        the null sentinel, ensures ``quality_tests`` is non-empty by
        adding a placeholder entry if needed, and appends the standard
        ``QUALITY CODES`` description to ``quality_comments`` for any
        line not already present.
        """
        defaults_comments = [
            "QUALITY CODES",
            "  0: Value has not been quality controlled",
            "  1: Value seems to be correct",
            "  2: Value appears inconsistent with other values",
            "  3: Value seems doubtful",
            "  4: Value seems erroneous",
            "  5: Value was modified",
            "  9: Value is missing",
        ]
        if self.quality_date == BaseHeader.SYTM_NULL_VALUE:
            self.quality_date = get_current_date_time()
        if not self.quality_tests:
            self.quality_tests.append("No quality tests performed")
        for comment in defaults_comments:
            if comment not in self.quality_comments:
                self.quality_comments.append(comment)

    def add_qcff_info(self) -> None:
        """Append the standard QCFF flag description and set the date.

        Sets ``quality_date`` to the current date/time if it is still
        the null sentinel, ensures ``quality_tests`` is non-empty by
        adding a placeholder entry if needed, and appends the standard
        ``QCFF CHANNEL`` description to ``quality_comments`` for any
        line not already present.
        """
        defaults_comments = [
            "QCFF CHANNEL",
            "  The QCFF flag allows one to determine from which test(s) the quality flag(s) originate.",
            "  It only applies to the stage 2 quality control tests.",
            "  Each test in this step is associated with a number 2x, where x is a whole positive number.",
            "  Before running the quality control, a QCFF value of 0 is attributed to each line of data.",
            "  When a test fails, the value of 2x that is associated with that test is added to the QCFF.",
            "  In this way one can easily identify which tests failed by analyzing the QCFF value.",
            "  If the QC flag of a record is modified by hand, a value of 1 is added to the QCFF.",
        ]
        if self.quality_date == BaseHeader.SYTM_NULL_VALUE:
            self.quality_date = get_current_date_time()
        if not self.quality_tests:
            self.quality_tests.append("No quality tests performed")
        for comment in defaults_comments:
            if comment not in self.quality_comments:
                self.quality_comments.append(comment)

    def populate_object(self, quality_fields: list) -> "QualityHeader":
        """Populate fields from parsed ODF quality header lines.

        Args:
            quality_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from the ``QUALITY_HEADER``
                section of an ODF file. Repeated ``QUALITY_TESTS`` and
                ``QUALITY_COMMENTS`` lines are accumulated into their
                respective lists.

        Returns:
            This :class:`QualityHeader` instance.
        """
        for header_line in quality_fields:
            tokens = header_line.split("=", maxsplit=1)
            quality_dict = list_to_dict(tokens)
            for key, value in quality_dict.items():
                key = key.strip("' ").upper()
                value = value.strip("' ")
                match key:
                    case "QUALITY_DATE":
                        self.quality_date = value
                    case "QUALITY_TESTS":
                        self.add_quality_test(value)
                    case "QUALITY_COMMENTS":
                        self.add_quality_comment(value)
        return self

    def print_object(self) -> str:
        """Serialize the quality header to ODF-formatted text.

        Returns:
            The ``QUALITY_HEADER`` section as ODF-formatted text, with
            one ``QUALITY_TESTS`` line per entry in ``quality_tests``
            and one ``QUALITY_COMMENTS`` line per entry in
            ``quality_comments`` (or a single empty line for each if
            there are none).
        """
        lines = ["QUALITY_HEADER", f"  QUALITY_DATE = '{check_string(self.quality_date)}'"]
        if not self.quality_tests:
            lines.append("  QUALITY_TESTS = ''")
        else:
            for quality_test in self.quality_tests:
                lines.append(f"  QUALITY_TESTS = '{quality_test}'")
        if not self.quality_comments:
            lines.append("  QUALITY_COMMENTS = ''")
        else:
            for quality_comment in self.quality_comments:
                lines.append(f"  QUALITY_COMMENTS = '{quality_comment}'")
        return "\n".join(lines)


def main():

    quality_header = QualityHeader()
    quality_header.config = BaseHeader._default_config
    quality_header.logger = BaseHeader._default_logger
    print(quality_header.print_object())
    quality_header.add_quality_codes()
    # quality_header.add_qcff_info()
    print(quality_header.print_object())

    qd = quality_header.quality_date
    quality_header.log_quality_message("QUALITY_DATE", qd, "01-JUL-2017 10:45:19.00")
    quality_header.quality_date = "01-JUL-2017 10:45:19.00"
    quality_header.set_quality_test("Test 1")
    quality_header.set_quality_test("Test 2")
    quality_header.quality_comments = ["Comment 1", "Comment 2"]
    quality_header.add_qcff_info()
    print(quality_header.print_object())

    print(BaseHeader.shared_log_list)


if __name__ == "__main__":
    main()
