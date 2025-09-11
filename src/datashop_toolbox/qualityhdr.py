from typing import List
from pydantic import Field, field_validator, ConfigDict
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, check_string, check_datetime, list_to_dict

class QualityHeader(ValidatedBase, BaseHeader):
    """ A class to represent a Quality Header in an ODF object. """

    model_config = ConfigDict(validate_assignment=True)

    quality_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    quality_tests: List[str] = Field(default_factory=list)
    quality_comments: List[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    @field_validator("quality_date", mode="before")
    @classmethod
    def validate_quality_date(cls, v):
        v = check_string(v)
        v = check_datetime(v)
        return v.upper()

    @field_validator("quality_tests", "quality_comments", mode="before")
    @classmethod
    def validate_lists(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [check_string(v)]
        return [check_string(item) for item in v]

    def log_quality_message(self, field: str, old_value: str, new_value: str) -> None:
        message = f"In Quality Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_quality_test(self, quality_test: str, test_number: int = 0) -> None:
        quality_test = check_string(quality_test)
        if test_number == 0 or test_number > len(self.quality_tests):
            self.quality_tests.append(quality_test)
        else:
            self.quality_tests[test_number - 1] = quality_test

    def add_quality_test(self, quality_test: str) -> None:
        quality_test = check_string(quality_test)
        self.quality_tests.append(quality_test)

    def set_quality_comment(self, quality_comment: str, comment_number: int = 0) -> None:
        quality_comment = check_string(quality_comment)
        if comment_number == 0 or comment_number > len(self.quality_comments):
            self.quality_comments.append(quality_comment)
        else:
            self.quality_comments[comment_number - 1] = quality_comment

    def add_quality_comment(self, quality_comment: str) -> None:
        quality_comment = check_string(quality_comment)
        self.quality_comments.append(quality_comment)

    def populate_object(self, quality_fields: list) -> "QualityHeader":
        for header_line in quality_fields:
            tokens = header_line.split('=', maxsplit=1)
            quality_dict = list_to_dict(tokens)
            for key, value in quality_dict.items():
                key = key.strip("' ").upper()
                value = value.strip("' ")
                match key:
                    case 'QUALITY_DATE':
                        self.quality_date = value
                    case 'QUALITY_TESTS':
                        self.add_quality_test(value)
                    case 'QUALITY_COMMENTS':
                        self.add_quality_comment(value)
        return self

    def print_object(self) -> str:
        lines = [
            "QUALITY_HEADER",
            f"  QUALITY_DATE = '{check_string(self.quality_date)}'"
        ]
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
    qd = quality_header.quality_date
    quality_header.log_quality_message("QUALITY_DATE", qd, '01-JUL-2017 10:45:19.00')
    quality_header.quality_date = '01-JUL-2017 10:45:19.00'
    quality_header.set_quality_test('Test 1')
    quality_header.set_quality_test('Test 2')
    quality_header.quality_comments = ['Comment 1', 'Comment 2']
    print(quality_header.print_object())

if __name__ == '__main__':
    main()
