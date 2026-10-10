from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class HourlyWeather:
    """One normalised hourly record. Times are UTC; value = sum/mean over the preceding hour."""

    time: datetime
    wind_mph: float | None
    rain_in_per_hr: float | None
    snow_in_per_hr: float | None


@dataclass(frozen=True)
class LocationForecast:
    lat: float
    lon: float
    hours: dict[datetime, HourlyWeather]


class WeatherProvider(Protocol):
    def hourly_forecasts(
        self, points: list[tuple[float, float]], start: datetime, end: datetime
    ) -> list[LocationForecast]: ...
