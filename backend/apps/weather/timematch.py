"""Forecast-hour matching (docs/PROJECT_SPEC.md §3.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .providers.base import HourlyWeather, LocationForecast


def ceil_to_hour(t: datetime) -> datetime:
    t = t.astimezone(UTC)
    floored = t.replace(minute=0, second=0, microsecond=0)
    return floored if floored == t else floored + timedelta(hours=1)


def match_forecast(forecast: LocationForecast, eta: datetime) -> HourlyWeather | None:
    """Open-Meteo values are preceding-hour sums, so the record at ceil(eta) covers eta.

    Returns None when the hour is outside the provider's horizon (caller ⇒ Unknown risk).
    """
    return forecast.hours.get(ceil_to_hour(eta))
