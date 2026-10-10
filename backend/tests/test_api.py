import httpx
import pytest
import respx
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.routing.providers.google_routes import COMPUTE_ROUTES_URL

URL = "/api/v1/route-analysis/"
VALID = {
    "origin": "Chicago, IL",
    "destination": "Denver, CO",
    "departure_time": "2026-10-11T08:00:00-05:00",
    "load_weight_lbs": 35000,
    "checkpoint_interval_miles": 25,
    "forecast_offset_hours": 0,
}

# 100-mile mock route
ROUTE_PAYLOAD = {
    "distanceMeters": 160934,
    "duration": "7200s",
    "polyline": {"encodedPolyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"},
    "routeLabels": ["DEFAULT_ROUTE"],
    "description": "Route via I-80 W",
    "legs": [{"steps": [{"distanceMeters": 160934, "staticDuration": "7200s"}]}],
}

OM_PAYLOAD = {
    "latitude": 41.0,
    "longitude": -90.0,
    "hourly_units": {
        "time": "iso8601",
        "wind_speed_10m": "mph",
        "rain": "inch",
        "snowfall": "inch",
    },
    "hourly": {
        "time": [f"2026-10-11T{h:02d}:00" for h in range(24)],
        "wind_speed_10m": [15.0] * 24,
        "rain": [0.0] * 24,
        "snowfall": [0.0] * 24,
    },
}


@pytest.fixture
def client():
    cache.clear()
    return APIClient()


def test_health(client):
    r = client.get("/api/health/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["providers"]["routing_configured"] is True
    assert "test-key-not-real" not in r.content.decode()


@override_settings(GOOGLE_ROUTES_API_KEY="")
def test_missing_key_is_503(client):
    r = client.post(URL, VALID, format="json")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "ROUTING_NOT_CONFIGURED"


@pytest.mark.parametrize(
    "patch,field",
    [
        ({"checkpoint_interval_miles": 20}, "checkpoint_interval_miles"),
        ({"forecast_offset_hours": 49}, "forecast_offset_hours"),
        ({"forecast_offset_hours": -1}, "forecast_offset_hours"),
        ({"load_weight_lbs": 0}, "load_weight_lbs"),
        ({"load_weight_lbs": "heavy"}, "load_weight_lbs"),
        ({"departure_time": "2026-10-11T08:00:00"}, "departure_time"),
        ({"departure_time": "not-a-date"}, "departure_time"),
        ({"origin": ""}, "origin"),
        ({"destination": "chicago, il"}, "destination"),
    ],
)
def test_validation_errors(client, patch, field):
    r = client.post(URL, {**VALID, **patch}, format="json")
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR" and field in err["details"]


@respx.mock
def test_end_to_end_analysis_three_routes(client):
    # Setup 3 distinct mocked routes
    alt1 = {
        **ROUTE_PAYLOAD,
        "polyline": {"encodedPolyline": "_ulLnnqC_mqNvxq`@"},
        "routeLabels": ["ALT_ROUTE_1"],
        "description": "Route via I-90 W",
    }
    alt2 = {
        **ROUTE_PAYLOAD,
        "polyline": {"encodedPolyline": "_p~iF~ps|U_mqNvxq`@"},
        "routeLabels": ["ALT_ROUTE_2"],
        "description": "Route via I-70 W",
    }

    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE_PAYLOAD, alt1, alt2]})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=[OM_PAYLOAD] * 20)
    )

    r = client.post(URL, VALID, format="json")
    assert r.status_code == 200
    data = r.json()

    assert data["request"]["origin"] == "Chicago, IL"
    assert len(data["routes"]) == 3
    assert data["recommendation"]["status"] == "RECOMMENDED"
    assert data["recommendation"]["route_id"] is not None

    route0 = data["routes"][0]
    assert len(route0["checkpoints"]) > 0
    assert len(route0["segments"]) > 0
    assert route0["metrics"]["severe_miles"] == 0
    assert route0["eligible"] is True


@respx.mock
def test_fewer_than_three_routes_warning(client):
    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE_PAYLOAD]})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=[OM_PAYLOAD] * 10)
    )

    r = client.post(URL, VALID, format="json")
    assert r.status_code == 200
    data = r.json()
    assert len(data["routes"]) == 1
    codes = [w["code"] for w in data["warnings"]]
    assert "FEWER_THAN_THREE_ROUTES" in codes


@respx.mock
def test_zero_routes_from_provider(client):
    respx.post(COMPUTE_ROUTES_URL).mock(return_value=httpx.Response(200, json={"routes": []}))

    r = client.post(URL, VALID, format="json")
    assert r.status_code == 200
    data = r.json()
    assert len(data["routes"]) == 0
    assert data["recommendation"]["status"] == "NO_ROUTES"


@respx.mock
def test_weather_provider_outage_honestly_marks_unknown(client):
    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE_PAYLOAD]})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(return_value=httpx.Response(500))

    r = client.post(URL, VALID, format="json")
    assert r.status_code == 200
    data = r.json()
    route = data["routes"][0]
    assert route["weather_incomplete"] is True
    assert route["checkpoints"][0]["risk"]["overall"] == "Unknown"
    assert route["metrics"]["unknown_miles"] > 0
    warning_codes = [w["code"] for w in data["warnings"]]
    assert "WEATHER_PROVIDER_UNAVAILABLE" in warning_codes
    assert "FORECAST_INCOMPLETE" in warning_codes


@respx.mock
def test_no_travel_route_ineligible_and_all_unsafe(client):
    # Severe wind (55+ mph) => No Travel
    stormy_payload = {
        **OM_PAYLOAD,
        "hourly": {
            **OM_PAYLOAD["hourly"],
            "wind_speed_10m": [60.0] * 24,
        },
    }
    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE_PAYLOAD]})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=[stormy_payload] * 10)
    )

    r = client.post(URL, VALID, format="json")
    assert r.status_code == 200
    data = r.json()
    route = data["routes"][0]
    assert route["eligible"] is False
    assert len(route["unsafe_reasons"]) > 0
    assert data["recommendation"]["status"] == "NO_SAFE_ROUTE"
    assert data["recommendation"]["route_id"] is None


@respx.mock
def test_forecast_offset_hours_shifts_departure(client):
    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE_PAYLOAD]})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=[OM_PAYLOAD] * 10)
    )

    payload = {**VALID, "forecast_offset_hours": 12}
    r = client.post(URL, payload, format="json")
    assert r.status_code == 200
    data = r.json()
    # Entered departure: 08:00 -05:00 = 13:00 UTC. Offset +12h = 2026-10-12T01:00:00Z
    assert data["effective_departure_time"] == "2026-10-12T01:00:00Z"


@respx.mock
def test_weather_caching_avoids_duplicate_requests(client):
    cache.clear()
    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE_PAYLOAD]})
    )
    weather_route = respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=[OM_PAYLOAD] * 20)
    )

    r1 = client.post(URL, VALID, format="json")
    assert r1.status_code == 200
    call_count_first = weather_route.call_count

    # Repeat request with identical parameters
    r2 = client.post(URL, VALID, format="json")
    assert r2.status_code == 200
    # Weather provider call count must remain identical because cache was reused
    assert weather_route.call_count == call_count_first


@respx.mock
def test_routing_provider_timeout_handled(client):
    respx.post(COMPUTE_ROUTES_URL).mock(side_effect=httpx.TimeoutException("timeout"))
    r = client.post(URL, VALID, format="json")
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


@respx.mock
def test_routing_provider_rate_limited_handled(client):
    respx.post(COMPUTE_ROUTES_URL).mock(return_value=httpx.Response(429))
    r = client.post(URL, VALID, format="json")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "UPSTREAM_RATE_LIMITED"


@respx.mock
def test_routing_provider_error_handled(client):
    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(500, json={"error": {"status": "INTERNAL"}})
    )
    r = client.post(URL, VALID, format="json")
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "UPSTREAM_ERROR"


def test_find_closest_forecast_association_logic():
    from apps.api.services import find_closest_forecast
    from apps.weather.providers.base import LocationForecast

    fc1 = LocationForecast(lat=41.0, lon=-90.0, hours={})
    fc2 = LocationForecast(lat=42.0, lon=-91.0, hours={})

    # Exact match
    assert find_closest_forecast([fc1, fc2], 41.0, -90.0) == fc1

    # Close match within conservative 10-mile tolerance (~0.05 degrees is ~3.5 miles)
    assert find_closest_forecast([fc1, fc2], 41.03, -90.02) == fc1

    # Far away (> 10 miles) returns None
    assert find_closest_forecast([fc1, fc2], 41.5, -90.5) is None

    # Empty list
    assert find_closest_forecast([], 41.0, -90.0) is None

    # Ambiguous match (two distinct forecasts within 0.1 mi of target)
    fc_ambig1 = LocationForecast(lat=41.000, lon=-90.000, hours={})
    fc_ambig2 = LocationForecast(lat=41.001, lon=-90.000, hours={})
    # Target halfway between them
    assert find_closest_forecast([fc_ambig1, fc_ambig2], 41.0005, -90.000) is None


@respx.mock
def test_unexpected_runtime_bug_in_weather_bubbles_up(client):
    from unittest.mock import patch

    respx.post(COMPUTE_ROUTES_URL).mock(
        return_value=httpx.Response(200, json={"routes": [ROUTE_PAYLOAD]})
    )

    # RouteAnalysisService should NOT swallow unexpected Python programming bugs (like TypeError)
    with patch(
        "apps.weather.providers.open_meteo.OpenMeteoProvider.hourly_forecasts",
        side_effect=TypeError("Unexpected bug"),
    ):
        with pytest.raises(TypeError, match="Unexpected bug"):
            client.post(URL, VALID, format="json")
