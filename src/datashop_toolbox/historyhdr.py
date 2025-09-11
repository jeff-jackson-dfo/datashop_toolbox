from typing import List
from pydantic import Field, field_validator, ConfigDict
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict

class HistoryHeader(ValidatedBase, BaseHeader):
    """ A class to represent a History Header in an ODF object. """

    model_config = ConfigDict(validate_assignment=True)

    creation_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    processes: List[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    @field_validator("creation_date", mode="before")
    @classmethod
    def validate_creation_date(cls, v):
        if isinstance(v, str):
            return v.strip("' ").upper()
        return v

    @field_validator("processes", mode="before")
    @classmethod
    def validate_processes(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip("' ")]
        return [str(item).strip("' ") for item in v]

    def log_history_message(self, field: str, old_value: str, new_value: str) -> None:
        message = f'In History Header field {field.upper()} was changed from "{old_value}" to "{new_value}"'
        self.logger.info(message)
        self.shared_log_list.append(message)

    def set_process(self, process: str, process_number: int = 0) -> None:
        process = process.strip("' ")
        if process_number == 0 or process_number > len(self.processes):
            self.processes.append(process)
        else:
            self.processes[process_number - 1] = process

    def add_process(self, process: str) -> None:
        process = process.strip("' ")
        self.processes.append(process)

    def find_process(self, search_string: str) -> List[int]:
        return [i for i, process in enumerate(self.processes) if search_string in process]

    def populate_object(self, history_fields: list) -> "HistoryHeader":
        assert isinstance(history_fields, list), "Input argument 'history_fields' must be a list."
        for header_line in history_fields:
            tokens = header_line.split('=', maxsplit=1)
            history_dict = list_to_dict(tokens)
            for key, value in history_dict.items():
                key = key.strip().upper()
                value = value.strip("' ")
                match key:
                    case 'CREATION_DATE':
                        self.creation_date = value
                    case 'PROCESS':
                        self.add_process(value)
        return self

    def print_object(self) -> str:
        lines = [
            "HISTORY_HEADER",
            f"  CREATION_DATE = '{self.creation_date}'"
        ]
        if self.processes:
            for process in self.processes:
                lines.append(f"  PROCESS = '{process}'")
        else:
            lines.append("  PROCESS = ''")
        return "\n".join(lines)

def main():
    print()
    history_header = HistoryHeader()
    history_header.config = BaseHeader._default_config
    history_header.logger = BaseHeader._default_logger
    print(history_header.print_object())
    history_fields = [
        "CREATION_DATE = '01-jun-2021 00:00:00.00'",
        "PROCESS = First process",
        "PROCESS = Second process",
        "PROCESS = Blank process",
        "PROCESS = Fourth process",
        "PROCESS = Last process"
    ]
    history_header.populate_object(history_fields)
    print(history_header.print_object())
    history_header.log_history_message('process', history_header.processes[1], 'Bad Cast')
    history_header.set_process('Bad Cast', 2)
    print(history_header.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)
    print()

if __name__ == '__main__':
    main()
