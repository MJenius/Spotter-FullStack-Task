from apps.risk.classification import Risk
from apps.risk.ranking import RiskInterval, compute_metrics, recommend


def m(severe=0.0, high=0.0, low=100.0, dur=3600.0, no_travel=0.0, unknown=0.0):
    ivs = [RiskInterval(low, Risk.LOW)]
    if severe:
        ivs.append(RiskInterval(severe, Risk.SEVERE))
    if high:
        ivs.append(RiskInterval(high, Risk.HIGH))
    if no_travel:
        ivs.append(RiskInterval(no_travel, Risk.NO_TRAVEL))
    if unknown:
        ivs.append(RiskInterval(unknown, Risk.UNKNOWN))
    return compute_metrics(ivs, dur)


def test_distance_weighted_average():
    metrics = compute_metrics(
        [RiskInterval(30, Risk.LOW), RiskInterval(10, Risk.SEVERE), RiskInterval(5, Risk.UNKNOWN)],
        100,
    )
    assert metrics.average_risk == 30 * 0 / 40 + 10 * 3 / 40
    assert metrics.unknown_miles == 5 and metrics.weather_incomplete


def test_severe_miles_first():
    r = recommend({"a": m(severe=5, dur=100), "b": m(severe=1, high=50, dur=9999)})
    assert (r.route_id, r.deciding_criterion) == ("b", "severe_miles")


def test_high_miles_second():
    r = recommend({"a": m(high=10, dur=100), "b": m(high=2, dur=9999)})
    assert (r.route_id, r.deciding_criterion) == ("b", "high_miles")


def test_average_risk_third():
    a = compute_metrics([RiskInterval(100, Risk.MODERATE)], 100)
    b = compute_metrics([RiskInterval(100, Risk.LOW)], 9999)
    r = recommend({"a": a, "b": b})
    assert (r.route_id, r.deciding_criterion) == ("b", "average_risk")


def test_duration_fourth():
    r = recommend({"a": m(dur=5000), "b": m(dur=4000)})
    assert (r.route_id, r.deciding_criterion) == ("b", "duration_seconds")


def test_no_travel_route_ineligible():
    r = recommend({"fast": m(dur=10, no_travel=1), "slow": m(severe=20, dur=99999)})
    assert r.route_id == "slow"
    assert "fast" not in r.ranking


def test_all_routes_unsafe():
    r = recommend({"a": m(no_travel=1), "b": m(no_travel=3)})
    assert r.status == "NO_SAFE_ROUTE" and r.route_id is None


def test_no_routes():
    assert recommend({}).status == "NO_ROUTES"
