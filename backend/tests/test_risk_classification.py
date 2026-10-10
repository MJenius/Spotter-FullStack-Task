import pytest

from apps.risk.classification import (
    Risk,
    classify_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
    classify_wind_base,
    worst,
)

L, M, H, S, N = Risk.LOW, Risk.MODERATE, Risk.HIGH, Risk.SEVERE, Risk.NO_TRAVEL


@pytest.mark.parametrize(
    "mph,expected",
    [
        (0, L),
        (24.99, L),
        (25, M),
        (34.99, M),
        (35, H),
        (44.99, H),
        (45, S),
        (54.99, S),
        (55, N),
        (80, N),
    ],
)
def test_wind_base(mph, expected):
    assert classify_wind_base(mph) is expected


@pytest.mark.parametrize(
    "inch,expected",
    [
        (0, L),
        (0.0999, L),
        (0.10, M),
        (0.2499, M),
        (0.25, H),
        (0.4999, H),
        (0.50, S),
        (1.00, S),
        (1.0001, N),
    ],
)
def test_rain(inch, expected):
    assert classify_rain(inch) is expected


@pytest.mark.parametrize(
    "inch,expected",
    [
        (0, L),
        (0.499, L),
        (0.5, M),
        (0.999, M),
        (1.0, H),
        (1.999, H),
        (2.0, S),
        (3.0, S),
        (3.0001, N),
    ],
)
def test_snow(inch, expected):
    assert classify_snow(inch) is expected


@pytest.mark.parametrize(
    "mph,load,expected",
    [
        (55, 0, N),
        (60, 1, N),
        (45, 30_000, S),
        (45, 30_000.01, N),
        (54.99, 30_001, N),
        (50, 20_000, S),
        (35, 40_000, H),
        (35, 40_000.01, S),
        (44.99, 50_000, S),
        (40, 35_000, H),
        (34.99, 80_000, M),
        (24, 80_000, L),
    ],
)
def test_wind_load_overrides(mph, load, expected):
    assert classify_wind(mph, load)[0] is expected


def test_override_has_reason():
    _, reason = classify_wind(47, 35_000)
    assert reason and "No Travel" in reason


def test_worst_of_conditions():
    assert worst(L, M, S) is S
    assert worst(L, N) is N
    assert worst(L, Risk.UNKNOWN) is Risk.UNKNOWN


def test_checkpoint_overall_and_reasons():
    r = classify_checkpoint(30, 0.3, 0.1, 10_000)
    assert (r.wind, r.rain, r.snow, r.overall) == (M, H, L, H)
    assert any("Rain" in x for x in r.reasons)


def test_missing_measurement_is_unknown_not_low():
    r = classify_checkpoint(None, 0.0, 0.0, 10_000)
    assert r.overall is Risk.UNKNOWN
    assert r.reasons
