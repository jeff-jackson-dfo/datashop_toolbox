import enum
import logging
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, Field


class LogLevel(enum.StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggerConfig(BaseModel):
    """Configuration model for logging settings."""

    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")

    def configure_logger(self) -> logging.Logger:
        """Configure and return a root logger instance."""
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, self.log_level.value))

        # Reset handlers safely
        logger.handlers.clear()

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(handler)

        return logger


class BaseHeader:
    """Base class providing shared logging + constants for ODF headers."""

    shared_log_list: ClassVar[list[str]] = []

    SYTM_FORMAT: ClassVar[str] = "%d-%b-%Y %H:%M:%S.%f"
    NULL_VALUE: ClassVar[float] = -999.0
    SYTM_NULL_VALUE: ClassVar[str] = "17-NOV-1858 00:00:00.000000"

    _default_config: ClassVar[LoggerConfig] = LoggerConfig()
    _default_logger: ClassVar[logging.Logger] = _default_config.configure_logger()

    def __init__(self, config: LoggerConfig | None = None):
        # Pydantic will call __init__, so we allow both normal + Pydantic init
        self.config = config or self._default_config
        self.logger = self.config.configure_logger()

    # ---------------------------
    # Logging helpers
    # ---------------------------
    def log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Log a message with the specified level."""
        log_method = getattr(self.logger, level.value.lower())
        log_method(message)

    def log_message(self, message: str) -> None:
        """Log a message and store it in the shared log list."""
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
