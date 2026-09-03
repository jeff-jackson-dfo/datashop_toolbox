import numpy as np
from pydantic import ConfigDict, Field, ValidationInfo, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict


class EventHeader(ValidatedBase, BaseHeader):
    """A class to represent an Event Header in an ODF object.

    Stores the metadata describing a single sampling event (e.g. a CTD
    cast) within a cruise, and provides methods for populating the
    header from parsed ODF text, logging field changes, managing event
    comments, and rendering the header back to ODF-formatted text.

    Attributes:
        data_type: Type of data collected for the event, e.g. ``"CTD"``.
        event_number: Identifier assigned to the event.
        event_qualifier1: First event qualifier.
        event_qualifier2: Second event qualifier.
        creation_date: Date/time the event record was created, in ODF
            SYTM format.
        orig_creation_date: Date/time the event record was originally
            created, in ODF SYTM format.
        start_date_time: Event start date/time in ODF SYTM format.
        end_date_time: Event end date/time in ODF SYTM format.
        initial_latitude: Latitude at the start of the event, in decimal
            degrees.
        initial_longitude: Longitude at the start of the event, in
            decimal degrees.
        end_latitude: Latitude at the end of the event, in decimal
            degrees.
        end_longitude: Longitude at the end of the event, in decimal
            degrees.
        min_depth: Minimum sampling depth, in metres.
        max_depth: Maximum sampling depth, in metres.
        sampling_interval: Interval between samples.
        sounding: Water depth (sounding) at the event location, in
            metres.
        depth_off_bottom: Height of the instrument off the bottom, in
            metres.
        station_name: Name of the station at which the event occurred.
        set_number: Identifier of the set to which the event belongs.
        event_comments: Free-text comments about the event.
    """

    model_config = ConfigDict(validate_assignment=True)

    data_type: str = ""
    event_number: str = ""
    event_qualifier1: str = ""
    event_qualifier2: str = ""
    creation_date: str = BaseHeader.SYTM_NULL_VALUE
    orig_creation_date: str = BaseHeader.SYTM_NULL_VALUE
    start_date_time: str = BaseHeader.SYTM_NULL_VALUE
    end_date_time: str = BaseHeader.SYTM_NULL_VALUE
    initial_latitude: float = BaseHeader.NULL_VALUE
    initial_longitude: float = BaseHeader.NULL_VALUE
    end_latitude: float = BaseHeader.NULL_VALUE
    end_longitude: float = BaseHeader.NULL_VALUE
    min_depth: float = BaseHeader.NULL_VALUE
    max_depth: float = BaseHeader.NULL_VALUE
    sampling_interval: float = BaseHeader.NULL_VALUE
    sounding: float = BaseHeader.NULL_VALUE
    depth_off_bottom: float = BaseHeader.NULL_VALUE
    station_name: str = ""
    set_number: str = ""
    event_comments: list[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        """Initialize the event header.

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

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v):
        """Strip surrounding quotes, asterisks, and whitespace from strings.

        Args:
            v: Raw value assigned to any field on this model.

        Returns:
            The stripped string if ``v`` is a string, otherwise ``v``
            unchanged.
        """
        if isinstance(v, str):
            return v.strip("' *").strip()
        return v

    @field_validator(
        "initial_latitude",
        "initial_longitude",
        "end_latitude",
        "end_longitude",
        "min_depth",
        "max_depth",
        "sampling_interval",
        "sounding",
        "depth_off_bottom",
        mode="before",
    )
    @classmethod
    def validate_floats(cls, v, info: ValidationInfo):
        """Coerce a numeric field to a native Python float.

        Args:
            v: Raw value assigned to one of the event's numeric fields
                (e.g. ``initial_latitude``, ``sounding``). Accepts a
                numpy scalar, a float, or a string representation of a
                float.
            info: Pydantic validation info for the field being set,
                used to name the field in error messages.

        Returns:
            The value converted to a native Python ``float``.

        Raises:
            ValueError: If ``v`` is a string that cannot be converted
                to a float.
            TypeError: If ``v`` is not a numpy scalar, float, or string.
        """
        # Coerce numpy scalars to native Python float
        if isinstance(v, np.generic):
            v = v.item()
        if isinstance(v, float):
            return v
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError as err:
                raise ValueError(f"{info.field_name} string value '{v}' cannot be converted to float") from err
        raise TypeError(
            f"{info.field_name} must be a float or string representing a float, got {type(v)}"
        )

    def log_event_message(self, field: str, old_value, new_value) -> None:
        """Log a change made to an event header field.

        Args:
            field: Name of the field that was changed. If
                ``"EVENT_COMMENTS"``, no change is logged and the caller
                is directed to :meth:`set_event_comment` instead.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.
        """
        field = field.upper()
        if field == "EVENT_COMMENTS":
            self.logger.info("Use method 'set_event_comment' to modify EVENT_COMMENTS.")
            return
        if field in {
            "DATA_TYPE",
            "EVENT_NUMBER",
            "EVENT_QUALIFIER1",
            "EVENT_QUALIFIER2",
            "CREATION_DATE",
            "ORIG_CREATION_DATE",
            "START_DATE_TIME",
            "END_DATE_TIME",
            "STATION_NAME",
            "SET_NUMBER",
        }:
            message = (
                f'In Event Header field {field} was changed from "{old_value}" to "{new_value}"'
            )
        else:
            message = f"In Event Header field {field} was changed from {old_value} to {new_value}"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_event_comment(self, event_comment: str, comment_number: int = 0) -> None:
        """Add or replace an entry in ``event_comments``.

        Args:
            event_comment: Comment text to store. Surrounding single
                quotes and whitespace are stripped.
            comment_number: One-based position of the comment to
                replace. If ``0`` (the default) or greater than the
                current number of comments, ``event_comment`` is
                appended as a new comment instead of replacing one.

        Raises:
            AssertionError: If ``event_comment`` is not a string or
                ``comment_number`` is not an integer.
        """
        assert isinstance(event_comment, str), "event_comment must be a string."
        assert isinstance(comment_number, int), "comment_number must be an integer."
        event_comment = event_comment.strip("' ")
        if comment_number == 0 or comment_number > len(self.event_comments):
            self.event_comments.append(event_comment)
        else:
            self.event_comments[comment_number - 1] = event_comment

    def populate_object(self, event_fields: list):
        """Populate fields from parsed ODF event header lines.

        Args:
            event_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from the ``EVENT_HEADER``
                section of an ODF file. Repeated ``EVENT_COMMENTS``
                lines are accumulated into the ``event_comments`` list.

        Returns:
            This :class:`EventHeader` instance.

        Raises:
            AssertionError: If ``event_fields`` is not a list.
        """
        assert isinstance(event_fields, list), "event_fields must be a list."
        for header_line in event_fields:
            tokens = header_line.split("=", maxsplit=1)
            event_dict = list_to_dict(tokens)
            for key, value in event_dict.items():
                key = key.strip().lower()
                if hasattr(self, key):
                    # If event_comments is a string then make it a list with one string.
                    if key == "event_comments":
                        if isinstance(value, str):
                            value = [value]
                    # Handle list values
                    if isinstance(value, list):
                        # If the attribute is also a list, extend or assign
                        attr = getattr(self, key, None)
                        if isinstance(attr, list):
                            attr.extend(v.strip("' ") if isinstance(v, str) else v for v in value)
                            setattr(self, key, attr)
                        else:
                            # Try to convert single-item list to scalar if possible
                            if len(value) == 1:
                                v = value[0]
                                setattr(self, key, v.strip("' ") if isinstance(v, str) else v)
                            else:
                                setattr(self, key, value)
                    else:
                        setattr(self, key, value.strip("' ") if isinstance(value, str) else value)
        return self

    def print_object(self) -> str:
        """Serialize the event header to ODF-formatted text.

        Returns:
            The ``EVENT_HEADER`` section as ODF-formatted text. Numeric
            fields that are set to :attr:`BaseHeader.NULL_VALUE` are
            printed unformatted; other numeric fields are printed with
            fixed decimal precision.
        """
        lines = [
            "EVENT_HEADER",
            f"  DATA_TYPE = '{self.data_type}'",
            f"  EVENT_NUMBER = '{self.event_number}'",
            f"  EVENT_QUALIFIER1 = '{self.event_qualifier1}'",
            f"  EVENT_QUALIFIER2 = '{self.event_qualifier2}'",
            f"  CREATION_DATE = '{self.creation_date}'",
            f"  ORIG_CREATION_DATE = '{self.orig_creation_date}'",
            f"  START_DATE_TIME = '{self.start_date_time}'",
            f"  END_DATE_TIME = '{self.end_date_time}'",
            f"  INITIAL_LATITUDE = {self.initial_latitude:.6f}"
            if self.initial_latitude != BaseHeader.NULL_VALUE
            else f"  INITIAL_LATITUDE = {self.initial_latitude}",
            f"  INITIAL_LONGITUDE = {float(self.initial_longitude):.6f}"
            if self.initial_longitude != BaseHeader.NULL_VALUE
            else f"  INITIAL_LONGITUDE = {self.initial_longitude}",
            f"  END_LATITUDE = {float(self.end_latitude):.6f}"
            if self.end_latitude != BaseHeader.NULL_VALUE
            else f"  END_LATITUDE = {self.end_latitude}",
            f"  END_LONGITUDE = {float(self.end_longitude):.6f}"
            if self.end_longitude != BaseHeader.NULL_VALUE
            else f"  END_LONGITUDE = {self.end_longitude}",
            f"  MIN_DEPTH = {float(self.min_depth):.2f}"
            if self.min_depth != BaseHeader.NULL_VALUE
            else f"  MIN_DEPTH = {self.min_depth}",
            f"  MAX_DEPTH = {self.max_depth:.2f}"
            if self.max_depth != BaseHeader.NULL_VALUE
            else f"  MAX_DEPTH = {self.max_depth}",
            f"  SAMPLING_INTERVAL = {self.sampling_interval}",
            f"  SOUNDING = {self.sounding:.2f}"
            if self.sounding != BaseHeader.NULL_VALUE
            else f"  SOUNDING = {self.sounding}",
            f"  DEPTH_OFF_BOTTOM = {self.depth_off_bottom:.2f}"
            if self.depth_off_bottom != BaseHeader.NULL_VALUE
            else f"  DEPTH_OFF_BOTTOM = {self.depth_off_bottom}",
            f"  STATION_NAME = '{self.station_name}'",
            f"  SET_NUMBER = '{self.set_number}'",
        ]
        if self.event_comments:
            for comment in self.event_comments:
                lines.append(f"  EVENT_COMMENTS = '{comment}'")
        else:
            lines.append("  EVENT_COMMENTS = ''")
        return "\n".join(lines)


def main():
    event = EventHeader()
    event.config = BaseHeader._default_config
    event.logger = BaseHeader._default_logger
    print(event.print_object())
    event.log_event_message("station_name", event.station_name, "STN_01")
    event.station_name = "STN_01"
    event.set_event_comment("Good cast!")
    print(event.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)


if __name__ == "__main__":
    main()
