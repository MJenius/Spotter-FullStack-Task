import pytest
from django.test import override_settings
from rest_framework.test import APIClient

URL = "/api/v1/route-analysis/"
VALID = {
    "origin": "Chicago, IL",
    "destination": "Denver, CO",
    "departure_time": "2026-10-11T08:00:00-05:00",
    "load_weight_lbs": 35000,
    "checkpoint_interval_miles": 25,
    "forecast_offset_hours": 0,
}


@pytest.fixture
def client():
    return APIClient()


def test_health(client):
    r = client.get("/api/health/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["providers"]["routing_configured"] is True
    assert "test-key-not-real" not in r.content.decode()


def test_valid_request_returns_honest_not_implemented(client):
    r = client.post(URL, VALID, format="json")
    assert r.status_code == 501
    assert r.json()["error"]["code"] == "NOT_IMPLEMENTED"


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


def test_zulu_departure_accepted(client):
    r = client.post(URL, {**VALID, "departure_time": "2026-10-11T13:00:00Z"}, format="json")
    assert r.status_code == 501
