from pydantic import Field, field_validator, ConfigDict
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict

class EventHeader(ValidatedBase, BaseHeader):
    """A class to represent an Event Header in an ODF object."""

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
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip("' *").strip()
        return v

    @field_validator("initial_latitude", "initial_longitude", "end_latitude", "end_longitude",
                     "min_depth", "max_depth", "sampling_interval", "sounding", "depth_off_bottom", mode="before")
    @classmethod
    def validate_floats(cls, v, info):
        if isinstance(v, float):
            return v
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                raise ValueError(f"{info.field_name} string value '{v}' cannot be converted to float")
        raise TypeError(f"{info.field_name} must be a float or string representing a float, got {type(v)}")

    def log_event_message(self, field: str, old_value, new_value) -> None:
        field = field.upper()
        if field == 'EVENT_COMMENTS':
            self.logger.info("Use method 'set_event_comment' to modify EVENT_COMMENTS.")
            return
        if field in {
            'DATA_TYPE', 'EVENT_NUMBER', 'EVENT_QUALIFIER1', 'EVENT_QUALIFIER2',
            'CREATION_DATE', 'ORIG_CREATION_DATE', 'START_DATE_TIME', 'END_DATE_TIME',
            'STATION_NAME', 'SET_NUMBER'
        }:
            message = f'In Event Header field {field} was changed from "{old_value}" to "{new_value}"'
        else:
            message = f'In Event Header field {field} was changed from {old_value} to {new_value}'
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_event_comment(self, event_comment: str, comment_number: int = 0) -> None:
        assert isinstance(event_comment, str), "event_comment must be a string."
        assert isinstance(comment_number, int), "comment_number must be an integer."
        event_comment = event_comment.strip("' ")
        if comment_number == 0 or comment_number > len(self.event_comments):
            self.event_comments.append(event_comment)
        else:
            self.event_comments[comment_number - 1] = event_comment

    def populate_object(self, event_fields: list):
        assert isinstance(event_fields, list), "event_fields must be a list."
        for header_line in event_fields:
            tokens = header_line.split('=', maxsplit=1)
            event_dict = list_to_dict(tokens)
            for key, value in event_dict.items():
                key = key.strip().lower()
                if hasattr(self, key):
                    # If event_comments is a string then make it a list with one string.
                    if key == 'event_comments':
                        if isinstance(value, str):
                            value = [value]
                    # Handle list values
                    if isinstance(value, list):
                        # If the attribute is also a list, extend or assign
                        attr = getattr(self, key, None)
                        if isinstance(attr, list):
                            attr.extend(
                                v.strip("' ") if isinstance(v, str) else v for v in value
                            )
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
            f"  INITIAL_LATITUDE = {self.initial_latitude:.6f}" if self.initial_latitude != BaseHeader.NULL_VALUE else f"  INITIAL_LATITUDE = {self.initial_latitude}",
            f"  INITIAL_LONGITUDE = {float(self.initial_longitude):.6f}" if self.initial_longitude != BaseHeader.NULL_VALUE else f"  INITIAL_LONGITUDE = {self.initial_longitude}",
            f"  END_LATITUDE = {float(self.end_latitude):.6f}" if self.end_latitude != BaseHeader.NULL_VALUE else f"  END_LATITUDE = {self.end_latitude}",
            f"  END_LONGITUDE = {float(self.end_longitude):.6f}" if self.end_longitude != BaseHeader.NULL_VALUE else f"  END_LONGITUDE = {self.end_longitude}",
            f"  MIN_DEPTH = {float(self.min_depth):.2f}" if self.min_depth != BaseHeader.NULL_VALUE else f"  MIN_DEPTH = {self.min_depth}",
            f"  MAX_DEPTH = {self.max_depth:.2f}" if self.max_depth != BaseHeader.NULL_VALUE else f"  MAX_DEPTH = {self.max_depth}",
            f"  SAMPLING_INTERVAL = {self.sampling_interval}",
            f"  SOUNDING = {self.sounding:.2f}" if self.sounding != BaseHeader.NULL_VALUE else f"  SOUNDING = {self.sounding}",
            f"  DEPTH_OFF_BOTTOM = {self.depth_off_bottom:.2f}" if self.depth_off_bottom != BaseHeader.NULL_VALUE else f"  DEPTH_OFF_BOTTOM = {self.depth_off_bottom}",
            f"  STATION_NAME = '{self.station_name}'",
            f"  SET_NUMBER = '{self.set_number}'"
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
    event.log_event_message('station_name', event.station_name, 'STN_01')
    event.station_name = 'STN_01'
    event.set_event_comment('Good cast!')
    print(event.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)

if __name__ == "__main__":
    main()
