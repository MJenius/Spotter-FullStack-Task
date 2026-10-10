"""Distance-weighted route metrics and lexicographic recommendation (docs/PROJECT_SPEC.md §6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .classification import Risk


@dataclass(frozen=True)
class RiskInterval:
    miles: float
    risk: Risk


@dataclass(frozen=True)
class RouteMetrics:
    severe_miles: float
    high_miles: float
    moderate_miles: float
    low_miles: float
    no_travel_miles: float
    unknown_miles: float
    average_risk: float | None
    duration_seconds: float

    @property
    def eligible(self) -> bool:
        return self.no_travel_miles <= 0

    @property
    def weather_incomplete(self) -> bool:
        return self.unknown_miles > 0


def compute_metrics(intervals: list[RiskInterval], duration_seconds: float) -> RouteMetrics:
    totals = {r: 0.0 for r in Risk}
    for iv in intervals:
        totals[iv.risk] += iv.miles
    # Average over known, non-No-Travel intervals using Low=0..Severe=3 (§6).
    weighted = sum(
        iv.miles * iv.risk.ordinal
        for iv in intervals
        if iv.risk not in (Risk.UNKNOWN, Risk.NO_TRAVEL)
    )
    known = sum(iv.miles for iv in intervals if iv.risk not in (Risk.UNKNOWN, Risk.NO_TRAVEL))
    return RouteMetrics(
        severe_miles=totals[Risk.SEVERE],
        high_miles=totals[Risk.HIGH],
        moderate_miles=totals[Risk.MODERATE],
        low_miles=totals[Risk.LOW],
        no_travel_miles=totals[Risk.NO_TRAVEL],
        unknown_miles=totals[Risk.UNKNOWN],
        average_risk=(weighted / known) if known > 0 else None,
        duration_seconds=duration_seconds,
    )


CRITERIA = ("severe_miles", "high_miles", "average_risk", "duration_seconds")
_EPS = 1e-6


def _key(m: RouteMetrics) -> tuple[float, ...]:
    avg = m.average_risk if m.average_risk is not None else float("inf")
    return (
        round(m.severe_miles, 6),
        round(m.high_miles, 6),
        round(avg, 6),
        m.duration_seconds,
    )


@dataclass(frozen=True)
class Recommendation:
    status: str  # RECOMMENDED | NO_SAFE_ROUTE | NO_ROUTES
    route_id: str | None
    deciding_criterion: str | None
    explanation: str
    ranking: list[str] = field(default_factory=list)


def recommend(candidates: dict[str, RouteMetrics]) -> Recommendation:
    if not candidates:
        return Recommendation("NO_ROUTES", None, None, "No routes were returned.")
    eligible = {rid: m for rid, m in candidates.items() if m.eligible}
    if not eligible:
        return Recommendation(
            "NO_SAFE_ROUTE",
            None,
            None,
            "Every route contains at least one No Travel checkpoint; no safe route found.",
        )
    ranking = sorted(eligible, key=lambda rid: _key(eligible[rid]))
    best = ranking[0]
    if len(ranking) == 1:
        return Recommendation("RECOMMENDED", best, None, "Only one eligible route.", ranking)
    a, b = _key(eligible[best]), _key(eligible[ranking[1]])
    criterion = next((CRITERIA[i] for i in range(len(CRITERIA)) if abs(a[i] - b[i]) > _EPS), None)
    explanation = (
        f"Wins on {criterion} versus runner-up {ranking[1]}."
        if criterion
        else f"Tied with {ranking[1]} on all criteria; first returned route kept."
    )
    return Recommendation("RECOMMENDED", best, criterion, explanation, ranking)
