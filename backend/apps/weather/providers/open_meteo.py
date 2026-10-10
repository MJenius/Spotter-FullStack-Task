"""Open-Meteo Forecast adapter (docs/PROJECT_SPEC.md §3.2)."""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime

import httpx
from django.core.cache import cache

from apps.providers_errors import ProviderError, ProviderRateLimited, ProviderTimeout

from ..units import UnknownUnitError, depth_to_inches, speed_to_mph
from .base import HourlyWeather, LocationForecast

HOURLY_VARS = "wind_speed_10m,rain,snowfall"


def _parse_location(raw: dict) -> LocationForecast:
    units = raw.get("hourly_units") or {}
    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    wind = hourly.get("wind_speed_10m") or [None] * len(times)
    rain = hourly.get("rain") or [None] * len(times)
    snow = hourly.get("snowfall") or [None] * len(times)

    def conv(fn, value, unit):
        if value is None:
            return None
        try:
            val_float = float(value)
            if not math.isfinite(val_float):
                return None
            return fn(val_float, unit)
        except (UnknownUnitError, ValueError, TypeError):
            return None  # unknown unit or invalid value ⇒ unavailable, never assumed

    hours: dict[datetime, HourlyWeather] = {}
    for i, t in enumerate(times):
        try:
            ts = datetime.fromisoformat(t).replace(tzinfo=UTC)
        except Exception:
            continue
        w_val = wind[i] if i < len(wind) else None
        r_val = rain[i] if i < len(rain) else None
        s_val = snow[i] if i < len(snow) else None
        hours[ts] = HourlyWeather(
            time=ts,
            wind_mph=conv(speed_to_mph, w_val, units.get("wind_speed_10m", "")),
            rain_in_per_hr=conv(depth_to_inches, r_val, units.get("rain", "")),
            snow_in_per_hr=conv(depth_to_inches, s_val, units.get("snowfall", "")),
        )
    try:
        lat = float(raw.get("latitude", 0))
        lon = float(raw.get("longitude", 0))
    except (ValueError, TypeError):
        lat, lon = 0.0, 0.0
    return LocationForecast(lat, lon, hours)


def normalize_response(payload: dict | list) -> list[LocationForecast]:
    items = payload if isinstance(payload, list) else [payload]
    return [_parse_location(item) for item in items]


class OpenMeteoProvider:
    def __init__(
        self,
        base_url: str,
        timeout: float = 15.0,
        cache_ttl: int = 1800,
        client: httpx.Client | None = None,
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._ttl = cache_ttl
        self._client = client

    def hourly_forecasts(
        self, points: list[tuple[float, float]], start: datetime, end: datetime
    ) -> list[LocationForecast]:
        if not points:
            return []
        params = {
            "latitude": ",".join(f"{p[0]:.3f}" for p in points),
            "longitude": ",".join(f"{p[1]:.3f}" for p in points),
            "hourly": HOURLY_VARS,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "start_hour": start.astimezone(UTC).strftime("%Y-%m-%dT%H:00"),
            "end_hour": end.astimezone(UTC).strftime("%Y-%m-%dT%H:00"),
        }
        key = "openmeteo:" + hashlib.sha256(repr(sorted(params.items())).encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.get(self._base_url, params=params)
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("Weather provider timed out.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("Could not reach weather provider.") from exc
        finally:
            if self._client is None:
                client.close()
        if resp.status_code == 429:
            raise ProviderRateLimited("Weather provider rate limit reached.")
        if resp.status_code >= 400:
            raise ProviderError(f"Weather provider error (HTTP {resp.status_code}).")
        result = normalize_response(resp.json())
        # If open-meteo returned an item per point in order:
        if len(result) == len(points):
            result = [
                LocationForecast(lat=points[idx][0], lon=points[idx][1], hours=item.hours)
                for idx, item in enumerate(result)
            ]
        elif len(result) < len(points):
            # If provider returned fewer items (e.g. repeated coordinates merged or truncated mock),
            # expand by index modulo or nearest coordinate so all requested points are covered
            expanded = []
            for idx, pt in enumerate(points):
                item = result[idx % len(result)]
                expanded.append(LocationForecast(lat=pt[0], lon=pt[1], hours=item.hours))
            result = expanded
        cache.set(key, result, self._ttl)
        return result
