from typing import List
from pydantic import Field, field_validator, ConfigDict
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, list_to_dict, check_string

class MeteoHeader(ValidatedBase, BaseHeader):
    """ A class to represent a Meteo Header in an ODF object. """

    model_config = ConfigDict(validate_assignment=True)

    air_temperature: float = Field(default=BaseHeader.NULL_VALUE)
    atmospheric_pressure: float = Field(default=BaseHeader.NULL_VALUE)
    wind_speed: float = Field(default=BaseHeader.NULL_VALUE)
    wind_direction: float = Field(default=BaseHeader.NULL_VALUE)
    sea_state: int = Field(default=int(BaseHeader.NULL_VALUE))
    cloud_cover: int = Field(default=int(BaseHeader.NULL_VALUE))
    ice_thickness: float = Field(default=BaseHeader.NULL_VALUE)
    meteo_comments: List[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        super().__init__(**data)  # Calls Pydantic's __init__

    def set_logger_and_config(self, logger, config):
        self.logger = logger
        self.config = config

    @field_validator("meteo_comments", mode="before")
    @classmethod
    def validate_comments(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [check_string(v)]
        return [check_string(item) for item in v]

    def log_meteo_message(self, field: str, old_value, new_value) -> None:
        assert isinstance(field, str), "Input argument 'field' must be a string."
        message = f"In Meteo Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_meteo_comment(self, meteo_comment: str, comment_number: int = 0) -> None:
        meteo_comment = check_string(meteo_comment)
        if comment_number == 0 or comment_number > len(self.meteo_comments):
            self.meteo_comments.append(meteo_comment)
        else:
            self.meteo_comments[comment_number - 1] = meteo_comment

    def add_meteo_comment(self, meteo_comment: str) -> None:
        meteo_comment = check_string(meteo_comment)
        self.meteo_comments.append(meteo_comment)

    def populate_object(self, meteo_fields: list) -> "MeteoHeader":
        assert isinstance(meteo_fields, list), "Input argument 'meteo_fields' must be a list."
        for header_line in meteo_fields:
            tokens = header_line.split('=', maxsplit=1)
            meteo_dict = list_to_dict(tokens)
            for key, value in meteo_dict.items():
                key = key.strip().upper()
                value = value.strip()
                print(f"Value is {value} with type {type(value)}")
                match key:
                    case 'AIR_TEMPERATURE':
                        self.air_temperature = float(value)
                    case 'ATMOSPHERIC_PRESSURE':
                        self.atmospheric_pressure = float(value)
                    case 'WIND_SPEED':
                        self.wind_speed = float(value)
                    case 'WIND_DIRECTION':
                        self.wind_direction = float(value)
                    case 'SEA_STATE':
                        self.sea_state = int(float(value))
                    case 'CLOUD_COVER':
                        self.cloud_cover = int(float(value))
                    case 'ICE_THICKNESS':
                        self.ice_thickness = float(value)
                    case 'METEO_COMMENTS':
                        self.add_meteo_comment(value)
        return self

    def print_object(self) -> str:
        lines = [
            "METEO_HEADER",
            f"  AIR_TEMPERATURE = {self.air_temperature if self.air_temperature == BaseHeader.NULL_VALUE else f'{self.air_temperature:.1f}'}",
            f"  ATMOSPHERIC_PRESSURE = {self.atmospheric_pressure if self.atmospheric_pressure == BaseHeader.NULL_VALUE else f'{self.atmospheric_pressure:.1f}'}",
            f"  WIND_SPEED = {self.wind_speed if self.wind_speed == BaseHeader.NULL_VALUE else f'{self.wind_speed:.1f}'}",
            f"  WIND_DIRECTION = {self.wind_direction if self.wind_direction == BaseHeader.NULL_VALUE else f'{self.wind_direction:.1f}'}",
            f"  SEA_STATE = {self.sea_state if self.sea_state == BaseHeader.NULL_VALUE else f'{self.sea_state:.0f}'}",
            f"  CLOUD_COVER = {self.cloud_cover if self.cloud_cover == BaseHeader.NULL_VALUE else f'{self.cloud_cover:.0f}'}",
            f"  ICE_THICKNESS = {self.ice_thickness if self.ice_thickness == BaseHeader.NULL_VALUE else f'{self.ice_thickness:.3f}'}"
        ]
        if self.meteo_comments:
            for meteo_comment in self.meteo_comments:
                lines.append(f"  METEO_COMMENTS = '{meteo_comment}'")
        else:
            lines.append("  METEO_COMMENTS = ''")
        return "\n".join(lines)

    @staticmethod
    def wind_speed_knots_to_ms(wsKnots: float) -> float:
        assert isinstance(wsKnots, float), "Input argument 'wsKnots' must be a float."
        if wsKnots < 0:
            return BaseHeader.NULL_VALUE
        return wsKnots / 1.94384

    @staticmethod
    def cloud_cover_percentage_to_wmo_code(cloud_cover_percentage: float) -> int:
        assert isinstance(cloud_cover_percentage, float), "Input argument 'cloud_cover_percentage' must be a float."
        if cloud_cover_percentage < 0.0:
            return int(BaseHeader.NULL_VALUE)
        elif cloud_cover_percentage == 0.0:
            return 0
        elif cloud_cover_percentage < 0.15:
            return 1
        elif cloud_cover_percentage < 0.35:
            return 2
        elif cloud_cover_percentage < 0.45:
            return 3
        elif cloud_cover_percentage < 0.55:
            return 4
        elif cloud_cover_percentage < 0.65:
            return 5
        elif cloud_cover_percentage < 0.85:
            return 6
        elif cloud_cover_percentage < 0.95:
            return 7
        elif cloud_cover_percentage < 1.0:
            return 8
        else:
            return 9

    @staticmethod
    def wave_height_meters_to_wmo_code(wave_height_meters: float) -> int:
        assert isinstance(wave_height_meters, float), "Input argument 'wave_height_meters' must be a float."
        if wave_height_meters < 0.0:
            return int(BaseHeader.NULL_VALUE)
        elif wave_height_meters == 0.0:
            return 0
        elif wave_height_meters < 0.1:
            return 1
        elif wave_height_meters < 0.5:
            return 2
        elif wave_height_meters < 1.25:
            return 3
        elif wave_height_meters < 2.5:
            return 4
        elif wave_height_meters < 4.0:
            return 5
        elif wave_height_meters < 6.0:
            return 6
        elif wave_height_meters < 9.0:
            return 7
        elif wave_height_meters < 14.0:
            return 8
        else:
            return 9

def main():
    
    meteo_header = MeteoHeader()
    meteo_header.config = BaseHeader._default_config
    meteo_header.logger = BaseHeader._default_logger

    print(meteo_header.print_object())
    meteo_header.air_temperature = 10.0
    meteo_header.atmospheric_pressure = 1000.0
    meteo_header.wind_speed = meteo_header.wind_speed_knots_to_ms(50.0)
    meteo_header.wind_direction = 180.0
    meteo_header.sea_state = meteo_header.wave_height_meters_to_wmo_code(3.0)
    meteo_header.cloud_cover = meteo_header.cloud_cover_percentage_to_wmo_code(0.5)
    meteo_header.ice_thickness = 0.5
    meteo_header.set_meteo_comment('This is a test comment')
    meteo_header.set_meteo_comment('This is another test comment')
    print(meteo_header.print_object())
    mc = meteo_header.meteo_comments[0]
    meteo_header.log_meteo_message('meteo_comments, comment 1', mc, 'Replace comment one')
    meteo_header.set_meteo_comment('Replace comment one', 1)
    print(meteo_header.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)

if __name__ == "__main__":
    main()
