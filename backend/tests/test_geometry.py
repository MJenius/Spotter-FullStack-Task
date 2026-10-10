from datetime import UTC, datetime, timedelta

import pytest

from apps.routing.domain import RouteStep
from apps.routing.geometry import (
    cumulative_distances,
    eta_at_distance,
    generate_checkpoints,
    haversine_miles,
)
from apps.routing.polyline import decode_polyline

# Uneven vertex spacing along the equator (1° lon ≈ 69.09 mi).
LINE = [(0.0, 0.0), (0.0, 0.05), (0.0, 0.1), (0.0, 1.5), (0.0, 1.55)]


def test_polyline_decode_reference():
    # Google's documented example.
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert pts == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def test_checkpoints_by_distance_not_vertex():
    total = cumulative_distances(LINE)[-1]
    cps = generate_checkpoints(LINE, 25)
    dists = [c.distance_miles for c in cps]
    assert dists[:5] == [0, 25, 50, 75, 100]
    assert dists[-1] == pytest.approx(total)
    # checkpoint at 25 mi lies on the long segment, interpolated
    assert haversine_miles(LINE[0], (cps[1].lat, cps[1].lon)) == pytest.approx(25, abs=0.01)


@pytest.mark.parametrize("interval", [10, 25, 50])
def test_intervals_reconcile_to_route_distance(interval):
    total = cumulative_distances(LINE)[-1]
    cps = generate_checkpoints(LINE, interval)
    assert sum(c.represented_miles for c in cps) == pytest.approx(total, abs=0.01)
    assert cps[0].interval_start_miles == 0 and cps[-1].interval_end_miles == total


def test_eta_proportional_fallback():
    dep = datetime(2026, 1, 1, tzinfo=UTC)
    assert eta_at_distance(dep, 50, 100, 7200) == dep + timedelta(hours=1)


def test_eta_uses_step_profile_scaled_to_total():
    dep = datetime(2026, 1, 1, tzinfo=UTC)
    steps = [RouteStep(50, 600), RouteStep(50, 3000)]  # slow second half
    # total 3600 s matches steps exactly; 50 mi ⇒ 600 s
    assert eta_at_distance(dep, 50, 100, 3600, steps) == dep + timedelta(seconds=600)
    # traffic duration 7200 doubles all step times
    assert eta_at_distance(dep, 75, 100, 7200, steps) == dep + timedelta(seconds=2 * 2100)


def test_eta_monotonic():
    dep = datetime(2026, 1, 1, tzinfo=UTC)
    steps = [RouteStep(10, 100), RouteStep(30, 900), RouteStep(60, 600)]
    etas = [eta_at_distance(dep, d, 100, 1600, steps) for d in range(0, 101, 5)]
    assert etas == sorted(etas)
