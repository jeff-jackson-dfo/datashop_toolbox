from pydantic import ConfigDict, Field, field_validator

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase, check_string, list_to_dict


class MeteoHeader(ValidatedBase, BaseHeader):
    """A class to represent a Meteo Header in an ODF object.

    Records meteorological observations taken during a sampling event
    and provides methods for populating the header from parsed ODF
    text, logging field changes, managing comments, converting between
    common meteorological units and WMO codes, and rendering the header
    back to ODF-formatted text.

    Attributes:
        air_temperature: Air temperature, in degrees Celsius.
        atmospheric_pressure: Atmospheric pressure.
        wind_speed: Wind speed, in metres per second.
        wind_direction: Wind direction, in degrees.
        sea_state: Sea state, as a WMO sea-state code.
        cloud_cover: Cloud cover, as a WMO cloud-cover code.
        ice_thickness: Ice thickness, in metres.
        meteo_comments: Free-text comments about the meteorological
            observations.
    """

    model_config = ConfigDict(validate_assignment=True)

    air_temperature: float = Field(default=BaseHeader.NULL_VALUE)
    atmospheric_pressure: float = Field(default=BaseHeader.NULL_VALUE)
    wind_speed: float = Field(default=BaseHeader.NULL_VALUE)
    wind_direction: float = Field(default=BaseHeader.NULL_VALUE)
    sea_state: int = Field(default=int(BaseHeader.NULL_VALUE))
    cloud_cover: int = Field(default=int(BaseHeader.NULL_VALUE))
    ice_thickness: float = Field(default=BaseHeader.NULL_VALUE)
    meteo_comments: list[str] = Field(default_factory=list)

    def __init__(self, config=None, **data):
        """Initialize the meteo header.

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

    @field_validator("meteo_comments", mode="before")
    @classmethod
    def validate_comments(cls, v):
        """Normalize ``meteo_comments`` to a list of stripped strings.

        Args:
            v: Raw value assigned to ``meteo_comments``. Accepts
                ``None``, a single string, or an iterable of values.

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

    def log_meteo_message(self, field: str, old_value, new_value) -> None:
        """Log a change made to a meteo header field.

        Args:
            field: Name of the field that was changed.
            old_value: Value of the field before the change.
            new_value: Value of the field after the change.

        Raises:
            AssertionError: If ``field`` is not a string.
        """
        assert isinstance(field, str), "Input argument 'field' must be a string."
        message = (
            f"In Meteo Header field {field.upper()} was changed from '{old_value}' to '{new_value}'"
        )
        # self.logger.info(message)
        self.shared_log_list.append(message)

    def set_meteo_comment(self, meteo_comment: str, comment_number: int = 0) -> None:
        """Add or replace an entry in ``meteo_comments``.

        Args:
            meteo_comment: Comment text to store.
            comment_number: One-based position of the comment to
                replace. If ``0`` (the default) or greater than the
                current number of comments, ``meteo_comment`` is
                appended as a new entry instead of replacing one.
        """
        meteo_comment = check_string(meteo_comment)
        if comment_number == 0 or comment_number > len(self.meteo_comments):
            self.meteo_comments.append(meteo_comment)
        else:
            self.meteo_comments[comment_number - 1] = meteo_comment

    def add_meteo_comment(self, meteo_comment: str) -> None:
        """Append a comment to ``meteo_comments``.

        Args:
            meteo_comment: Comment text to append.
        """
        meteo_comment = check_string(meteo_comment)
        self.meteo_comments.append(meteo_comment)

    def populate_object(self, meteo_fields: list) -> "MeteoHeader":
        """Populate fields from parsed ODF meteo header lines.

        Args:
            meteo_fields: Raw header lines of the form
                ``"KEY = VALUE"`` taken from the ``METEO_HEADER``
                section of an ODF file. Repeated ``METEO_COMMENTS``
                lines are accumulated into ``meteo_comments``.

        Returns:
            This :class:`MeteoHeader` instance.

        Raises:
            AssertionError: If ``meteo_fields`` is not a list.
        """
        assert isinstance(meteo_fields, list), "Input argument 'meteo_fields' must be a list."
        for header_line in meteo_fields:
            tokens = header_line.split("=", maxsplit=1)
            meteo_dict = list_to_dict(tokens)
            for key, value in meteo_dict.items():
                key = key.strip().upper()
                value = value.strip()
                match key:
                    case "AIR_TEMPERATURE":
                        self.air_temperature = float(value)
                    case "ATMOSPHERIC_PRESSURE":
                        self.atmospheric_pressure = float(value)
                    case "WIND_SPEED":
                        self.wind_speed = float(value)
                    case "WIND_DIRECTION":
                        self.wind_direction = float(value)
                    case "SEA_STATE":
                        self.sea_state = int(float(value))
                    case "CLOUD_COVER":
                        self.cloud_cover = int(float(value))
                    case "ICE_THICKNESS":
                        self.ice_thickness = float(value)
                    case "METEO_COMMENTS":
                        self.add_meteo_comment(value)
        return self

    def print_object(self) -> str:
        """Serialize the meteo header to ODF-formatted text.

        Returns:
            The ``METEO_HEADER`` section as ODF-formatted text.
            Numeric fields that are set to :attr:`BaseHeader.NULL_VALUE`
            are printed unformatted; other numeric fields are printed
            with fixed decimal precision.
        """
        lines = [
            "METEO_HEADER",
            f"  AIR_TEMPERATURE = " \
            f"{self.air_temperature if self.air_temperature == BaseHeader.NULL_VALUE else f'{self.air_temperature:.1f}'}",  # noqa: E501
            f"  ATMOSPHERIC_PRESSURE = " \
            f"{self.atmospheric_pressure if self.atmospheric_pressure == BaseHeader.NULL_VALUE else f'{self.atmospheric_pressure:.1f}'}",  # noqa: E501
            f"  WIND_SPEED = " \
            f"{self.wind_speed if self.wind_speed == BaseHeader.NULL_VALUE else f'{self.wind_speed:.1f}'}",
            f"  WIND_DIRECTION = " \
            f"{self.wind_direction if self.wind_direction == BaseHeader.NULL_VALUE else f'{self.wind_direction:.1f}'}",
            f"  SEA_STATE = " \
            f"{self.sea_state if self.sea_state == BaseHeader.NULL_VALUE else f'{self.sea_state:.0f}'}",
            f"  CLOUD_COVER = " \
            f"{self.cloud_cover if self.cloud_cover == BaseHeader.NULL_VALUE else f'{self.cloud_cover:.0f}'}",
            f"  ICE_THICKNESS = " \
            f"{self.ice_thickness if self.ice_thickness == BaseHeader.NULL_VALUE else f'{self.ice_thickness:.3f}'}",
        ]
        if self.meteo_comments:
            for meteo_comment in self.meteo_comments:
                lines.append(f"  METEO_COMMENTS = '{meteo_comment}'")
        else:
            lines.append("  METEO_COMMENTS = ''")
        return "\n".join(lines)

    @staticmethod
    def wind_speed_knots_to_ms(wind_speed_knots: float) -> float:
        """Convert wind speed from knots to metres per second.

        Args:
            wind_speed_knots: Wind speed, in knots.

        Returns:
            The wind speed in metres per second, or
            :attr:`BaseHeader.NULL_VALUE` if ``wind_speed_knots`` is
            negative.

        Raises:
            AssertionError: If ``wind_speed_knots`` is not a float.
        """
        assert isinstance(wind_speed_knots, float), "Input argument 'wind_speed_knots' must be a float."
        if wind_speed_knots < 0:
            return BaseHeader.NULL_VALUE
        return wind_speed_knots / 1.94384

    @staticmethod
    def cloud_cover_percentage_to_wmo_code(cloud_cover_percentage: float) -> int:
        """Convert a cloud-cover fraction to its WMO cloud-cover code.

        Args:
            cloud_cover_percentage: Cloud cover as a fraction between
                ``0.0`` (clear) and ``1.0`` (fully overcast).

        Returns:
            The corresponding WMO cloud-cover code (``0``-``9``), or
            ``int(BaseHeader.NULL_VALUE)`` if ``cloud_cover_percentage``
            is negative.

        Raises:
            AssertionError: If ``cloud_cover_percentage`` is not a
                float.
        """
        assert isinstance(cloud_cover_percentage, float), (
            "Input argument 'cloud_cover_percentage' must be a float."
        )
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
        """Convert a wave height to its WMO wave-height (sea-state) code.

        Args:
            wave_height_meters: Wave height, in metres.

        Returns:
            The corresponding WMO wave-height code (``0``-``9``), or
            ``int(BaseHeader.NULL_VALUE)`` if ``wave_height_meters`` is
            negative.

        Raises:
            AssertionError: If ``wave_height_meters`` is not a float.
        """
        assert isinstance(wave_height_meters, float), (
            "Input argument 'wave_height_meters' must be a float."
        )
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
    meteo_header.set_meteo_comment("This is a test comment")
    meteo_header.set_meteo_comment("This is another test comment")
    print(meteo_header.print_object())
    mc = meteo_header.meteo_comments[0]
    meteo_header.log_meteo_message("meteo_comments, comment 1", mc, "Replace comment one")
    meteo_header.set_meteo_comment("Replace comment one", 1)
    print(meteo_header.print_object())
    for log_entry in BaseHeader.shared_log_list:
        print(log_entry)


if __name__ == "__main__":
    main()
