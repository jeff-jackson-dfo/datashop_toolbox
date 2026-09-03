import enum
import logging
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, Field


class LogLevel(enum.StrEnum):
    """Enumeration of the logging levels supported by :class:`LoggerConfig`.

    Attributes:
        DEBUG: Detailed diagnostic information.
        INFO: General informational messages confirming normal operation.
        WARNING: An indication of a potential problem that does not stop execution.
        ERROR: A more serious problem that prevented an operation from completing.
        CRITICAL: A severe error indicating the program itself may be unable to continue.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggerConfig(BaseModel):
    """Configuration model for logging settings.

    Attributes:
        log_level: Logging level applied when the logger is configured.
    """

    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")

    def configure_logger(self) -> logging.Logger:
        """Configure and return a root logger instance.

        Clears any handlers already attached to the root logger, then
        attaches a single :class:`~logging.StreamHandler` using this
        config's ``log_level`` and a ``"[LEVEL] message"`` format.

        Returns:
            The configured root logger.
        """
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, self.log_level.value))

        # Reset handlers safely
        logger.handlers.clear()

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(handler)

        return logger


class BaseHeader:
    """Base class providing shared logging + constants for ODF headers.

    Subclasses (typically Pydantic models representing individual ODF
    header sections) inherit a per-instance logger plus a set of
    class-level constants used throughout the ODF header hierarchy, such
    as the standard SYTM date/time format and the sentinel value used to
    represent missing numeric data.

    Attributes:
        shared_log_list: Log messages shared and accumulated across all
            header instances and subclasses.
        SYTM_FORMAT: ``strptime``/``strftime`` format string for ODF
            SYTM date/time values.
        NULL_VALUE: Sentinel used to represent a missing numeric value.
        SYTM_NULL_VALUE: Sentinel used to represent a missing SYTM
            date/time value.
        config: Logger configuration used to build ``logger``.
        logger: Logger instance configured from ``config``.
    """

    shared_log_list: ClassVar[list[str]] = []

    SYTM_FORMAT: ClassVar[str] = "%d-%b-%Y %H:%M:%S.%f"
    NULL_VALUE: ClassVar[float] = -999.0
    SYTM_NULL_VALUE: ClassVar[str] = "17-NOV-1858 00:00:00.000000"

    _default_config: ClassVar[LoggerConfig] = LoggerConfig()
    _default_logger: ClassVar[logging.Logger] = _default_config.configure_logger()

    def __init__(self, config: LoggerConfig | None = None):
        """Initialize the header with a logger configuration.

        Args:
            config: Logger configuration to use. If ``None``, the
                class-level default configuration is used.
        """
        # Pydantic will call __init__, so we allow both normal + Pydantic init
        self.config = config or self._default_config
        self.logger = self.config.configure_logger()

    # ---------------------------
    # Logging helpers
    # ---------------------------
    def log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Log a message with the specified level.

        Args:
            message: Message to log.
            level: Severity level to log the message at. Defaults to
                :attr:`LogLevel.INFO`.
        """
        log_method = getattr(self.logger, level.value.lower())
        log_method(message)

    def log_message(self, message: str) -> None:
        """Log a message and store it in the shared log list.

        Args:
            message: Message to append to :attr:`shared_log_list`.
        """
        entry = f"{message}"
        self.shared_log_list.append(entry)

    def reset_logging(self) -> None:
        """Reconfigure logger using the stored config."""
        self.logger = self.config.configure_logger()

    @classmethod
    def reset_log_list(cls) -> None:
        """Clear the shared log list."""
        cls.shared_log_list.clear()

    @staticmethod
    def matches_sytm_format(date_str: str) -> bool:
        """Check whether a string matches the standard ODF SYTM format.

        Args:
            date_str: Date/time string to validate, e.g.
                ``"17-NOV-1858 00:00:00.000000"``.

        Returns:
            ``True`` if ``date_str`` matches :attr:`SYTM_FORMAT`,
            ``False`` otherwise.
        """
        fmt = BaseHeader.SYTM_FORMAT
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            return False


def main():

    # Create a config object using Pydantic
    config = LoggerConfig(log_level=LogLevel.INFO)

    class SubClassA(BaseHeader):
        def log_message(self, message):
            super().log_message(f"SubClassA: {message}")

    class SubClassB(BaseHeader):
        def log_message(self, message):
            super().log_message(f"SubClassB: {message}")

    # Example usage
    subclass_a = SubClassA(config)
    subclass_b = SubClassB(config)

    subclass_a.log_message("Message from SubClassA")
    subclass_b.log_message("Message from SubClassB")

    # Access the shared log messages before resetting
    print("Shared log messages before resetting:")
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)

    # Reset the shared log list
    BaseHeader.reset_log_list()

    # Access the shared log messages after resetting
    print("Shared log messages after resetting:")
    print(BaseHeader.shared_log_list)

    subclass_a.log_message("New message from SubClassA after reset")
    subclass_b.log_message("New message from SubClassB after reset")

    # Access the shared log messages after new log entries
    print("Shared log messages after new entries:")
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)


if __name__ == "__main__":
    main()
