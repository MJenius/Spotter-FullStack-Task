from datetime import UTC, datetime

import httpx
import pytest
import respx

from apps.providers_errors import (
    ProviderError,
    ProviderNotConfigured,
    ProviderRateLimited,
    ProviderTimeout,
)
from apps.routing.domain import RouteRequest
from apps.routing.providers.google_routes import COMPUTE_ROUTES_URL, GoogleRoutesProvider
from apps.weather.providers.open_meteo import OpenMeteoProvider, normalize_response
from apps.weather.timematch import ceil_to_hour, match_forecast

REQ = RouteRequest("Chicago, IL", "Denver, CO", "2026-10-11T13:00:00Z")
ROUTE = {
    "distanceMeters": 160934,
    "duration": "7200s",
    "polyline": {"encodedPolyline": "_p~iF~ps|U_ulLnnqC"},
    "routeLabels": ["DEFAULT_ROUTE"],
    "description": "I-80",
    "legs": [{"steps": [{"distanceMeters": 160934, "staticDuration": "6000s"}]}],
}


@respx.mock
def test_google_normalizes_and_dedupes():
    alt = {
        **ROUTE,
        "polyline": {"encodedPolyline": "_ulLnnqC_mqNvxq`@"},
        "routeLabels": ["DEFAULT_ROUTE_ALTERNATE"],
    }
    route = respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE, ROUTE, alt]})
    )
    result = GoogleRoutesProvider("k").compute_routes(REQ)
    sent = route.calls[0].request
    assert sent.headers["X-Goog-Api-Key"] == "k"
    assert b'"computeAlternativeRoutes":true' in sent.content.replace(b" ", b"")
    assert [r.id for r in result.routes] == ["route-0", "route-1"]
    r0 = result.routes[0]
    assert r0.distance_miles == pytest.approx(100, abs=0.01)
    assert r0.duration_seconds == 7200 and r0.steps[0].duration_seconds == 6000
    assert r0.polyline[0] == (38.5, -120.2)
    assert result.warnings[0]["code"] == "FEWER_THAN_THREE_ROUTES"


def test_google_requires_key():
    with pytest.raises(ProviderNotConfigured):
        GoogleRoutesProvider("")


@respx.mock
@pytest.mark.parametrize(
    "response,exc",
    [
        (httpx.Response(429), ProviderRateLimited),
        (httpx.Response(500, json={"error": {"status": "INTERNAL"}}), ProviderError),
        (httpx.TimeoutException("t"), ProviderTimeout),
    ],
)
def test_google_errors_are_sanitized(response, exc):
    mock = respx.post(COMPUTE_ROUTES_URL)
    if isinstance(response, Exception):
        mock.mock(side_effect=response)
    else:
        mock.mock(return_value=response)
    with pytest.raises(exc) as info:
        GoogleRoutesProvider("secret-key").compute_routes(REQ)
    assert "secret-key" not in str(info.value)


OM_PAYLOAD = {
    "latitude": 41.0,
    "longitude": -90.0,
    "hourly_units": {"time": "iso8601", "wind_speed_10m": "km/h", "rain": "mm", "snowfall": "cm"},
    "hourly": {
        "time": ["2026-10-11T13:00", "2026-10-11T14:00"],
        "wind_speed_10m": [40.2335, None],
        "rain": [2.54, 0.0],
        "snowfall": [2.54, 0.0],
    },
}


def test_open_meteo_unit_normalization():
    [loc] = normalize_response(OM_PAYLOAD)
    h = loc.hours[datetime(2026, 10, 11, 13, tzinfo=UTC)]
    assert h.wind_mph == pytest.approx(25.0, abs=0.001)
    assert h.rain_in_per_hr == pytest.approx(0.1)
    assert h.snow_in_per_hr == pytest.approx(1.0)
    assert loc.hours[datetime(2026, 10, 11, 14, tzinfo=UTC)].wind_mph is None

    # Test 'mp/h' unit format returned by Open-Meteo
    mph_payload = {
        **OM_PAYLOAD,
        "hourly_units": {**OM_PAYLOAD["hourly_units"], "wind_speed_10m": "mp/h"},
        "hourly": {**OM_PAYLOAD["hourly"], "wind_speed_10m": [32.5, None]},
    }
    [loc_mph] = normalize_response(mph_payload)
    assert loc_mph.hours[datetime(2026, 10, 11, 13, tzinfo=UTC)].wind_mph == pytest.approx(32.5)


def test_open_meteo_unknown_unit_is_unavailable():
    payload = {**OM_PAYLOAD, "hourly_units": {**OM_PAYLOAD["hourly_units"], "rain": "furlong"}}
    [loc] = normalize_response(payload)
    assert loc.hours[datetime(2026, 10, 11, 13, tzinfo=UTC)].rain_in_per_hr is None


def test_time_matching_uses_hour_containing_eta():
    [loc] = normalize_response(OM_PAYLOAD)
    eta = datetime(2026, 10, 11, 13, 20, tzinfo=UTC)
    assert ceil_to_hour(eta) == datetime(2026, 10, 11, 14, tzinfo=UTC)
    assert match_forecast(loc, eta).time.hour == 14
    assert match_forecast(loc, datetime(2026, 10, 11, 13, tzinfo=UTC)).time.hour == 13
    assert match_forecast(loc, datetime(2026, 10, 20, tzinfo=UTC)) is None  # beyond horizon


@respx.mock
def test_open_meteo_batches_and_caches():
    base = "https://weather.test/v1/forecast"
    route = respx.get(base).mock(return_value=httpx.Response(200, json=[OM_PAYLOAD, OM_PAYLOAD]))
    p = OpenMeteoProvider(base)
    start = datetime(2026, 10, 11, 13, tzinfo=UTC)
    pts = [(41.0, -90.0), (41.5, -91.0)]
    assert len(p.hourly_forecasts(pts, start, start)) == 2
    p.hourly_forecasts(pts, start, start)
    assert route.call_count == 1
    params = route.calls[0].request.url.params
    assert params["latitude"] == "41.000,41.500" and params["wind_speed_unit"] == "mph"
