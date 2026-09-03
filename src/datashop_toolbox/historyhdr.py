from pydantic import ConfigDict, Field, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict


class HistoryHeader(ValidatedBase, BaseHeader):
    """A class to represent a History Header in an ODF object.

    Records when an ODF file's data were most recently modified and the
    sequence of processing steps applied to them, and provides methods
    for populating the header from parsed ODF text, logging field
    changes, managing the list of processes, and rendering the header
    back to ODF-formatted text.

    Attributes:
        creation_date: Date/time the history record was created, in ODF
            SYTM format.
        processes: Ordered list of processing steps applied to the data.
    """

    model_config = ConfigDict(validate_assignment=True)

    creation_date: str = Field(default=BaseHeader.SYTM_NULL_VALUE)
    processes: list[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        """Initialize the history header.

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

    @field_validator("creation_date", mode="before")
    @classmethod
    def validate_creation_date(cls, v):
        """Normalize the creation date to a stripped, upper-case string.

        Args:
            v: Raw value assigned to ``creation_date``.

        Returns:
            The stripped, upper-cased string if ``v`` is a string,
            otherwise ``v`` unchanged.
        """
        if isinstance(v, str):
            return v.strip("' ").upper()
        return v

    @field_validator("processes", mode="before")
    @classmethod
    def validate_processes(cls, v):
        """Normalize the ``processes`` field to a list of stripped strings.

        Args:
            v: Raw value assigned to ``processes``. Accepts ``None``, a
                single string, or an iterable of values.

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

    def log_history_message(self, field: str, old_value: str, new_value: str) -> None:
        """Log a change made to a history header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.
        """
        message = f'In History Header field {field.upper()} was changed from "{old_value}" to "{new_value}"'
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_process(self, process: str, process_number: int = 0) -> None:
        """Add or replace an entry in ``processes``.

        Args:
            process: Process description to store. Surrounding single
                quotes and whitespace are stripped.
            process_number: One-based position of the process to
                replace. If ``0`` (the default) or greater than the
                current number of processes, ``process`` is appended
                as a new entry instead of replacing one.
        """
        process = process.strip("' ")
        if process_number == 0 or process_number > len(self.processes):
            self.processes.append(process)
        else:
            self.processes[process_number - 1] = process

    def add_process(self, process: str) -> None:
        """Append a processing step to ``processes``.

        Args:
            process: Process description to append. Surrounding single
                quotes and whitespace are stripped.
        """
        process = process.strip("' ")
        self.processes.append(process)

    def find_process(self, search_string: str) -> list[int]:
        """Find the indices of processes containing a search string.

        Args:
            search_string: Substring to search for within each entry
                of ``processes``.

        Returns:
            The list of indices into ``processes`` whose entries
            contain ``search_string``.
        """
        return [i for i, process in enumerate(self.processes) if search_string in process]

    def populate_object(self, history_fields: list) -> "HistoryHeader":
        """Populate fields from parsed ODF history header lines.

        Args:
            history_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from the ``HISTORY_HEADER``
                section of an ODF file. Repeated ``PROCESS`` lines are
                accumulated into the ``processes`` list.

        Returns:
            This :class:`HistoryHeader` instance.

        Raises:
            AssertionError: If ``history_fields`` is not a list.
        """
        assert isinstance(history_fields, list), "Input argument 'history_fields' must be a list."
        for header_line in history_fields:
            tokens = header_line.split("=", maxsplit=1)
            history_dict = list_to_dict(tokens)
            for key, value in history_dict.items():
                key = key.strip().upper()
                value = value.strip("' ")
                match key:
                    case "CREATION_DATE":
                        self.creation_date = value
                    case "PROCESS":
                        self.add_process(value)
        return self

    def print_object(self) -> str:
        """Serialize the history header to ODF-formatted text.

        Returns:
            The ``HISTORY_HEADER`` section as ODF-formatted text, with
            one ``PROCESS`` line per entry in ``processes`` (or a single
            empty ``PROCESS`` line if there are none).
        """
        lines = ["HISTORY_HEADER", f"  CREATION_DATE = '{self.creation_date}'"]
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
        "PROCESS = Last process",
    ]
    history_header.populate_object(history_fields)
    print(history_header.print_object())
    history_header.log_history_message("process", history_header.processes[1], "Bad Cast")
    history_header.set_process("Bad Cast", 2)
    print(history_header.print_object())

    history_header.set_process("CONSTANT, RESULT=CRAT_1, VALUE=0.0, TYPE=DOUB, FORMAT=10:6,")
    history_header.set_process("NEVER_NULL=NO")
    history_header.set_process("SELECT_FILE,")
    history_header.set_process("FILE_SPEC=D3:[DATA.MARION]M*.ODF")
    history_header.set_process("OPEN_ASCII_FILE")
    history_header.set_process("READ_ASCII_HEADERS")
    history_header.set_process("READ_ASCII_DATA,FILE_FORMAT=ODF")
    history_header.set_process("EDIT_VARIABLE,VARIABLE=CRAT_1,FORMAT=10:6")
    history_header.set_process("***EXPORT_ASCII,EVENT_FILTER=Y,FILE_FORMAT=ODF,EXTENSION=ODF,")
    history_header.set_process("PATH=D3:[DATA.TEMP1]")
    history_header.set_process("$")
    history_header.set_process("END")

    print(history_header.print_object())

    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)
    print()


if __name__ == "__main__":
    main()
