"""Pure risk classification per docs/PROJECT_SPEC.md §4–§5. No Django or I/O imports here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Risk(StrEnum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    SEVERE = "Severe"
    NO_TRAVEL = "No Travel"
    UNKNOWN = "Unknown"

    @property
    def ordinal(self) -> int | None:
        return _ORDINAL.get(self)


_ORDINAL = {Risk.LOW: 0, Risk.MODERATE: 1, Risk.HIGH: 2, Risk.SEVERE: 3, Risk.NO_TRAVEL: 4}

LOAD_NO_TRAVEL_THRESHOLD_LBS = 30_000
LOAD_SEVERE_THRESHOLD_LBS = 40_000


def classify_wind_base(mph: float) -> Risk:
    if mph < 25:
        return Risk.LOW
    if mph < 35:
        return Risk.MODERATE
    if mph < 45:
        return Risk.HIGH
    if mph < 55:
        return Risk.SEVERE
    return Risk.NO_TRAVEL


def classify_wind(mph: float, load_lbs: float) -> tuple[Risk, str | None]:
    """Wind category with load overrides (§5.4). Returns (risk, override_reason)."""
    base = classify_wind_base(mph)
    if 45 <= mph < 55 and load_lbs > LOAD_NO_TRAVEL_THRESHOLD_LBS:
        return Risk.NO_TRAVEL, (
            f"Wind {mph:.1f} mph with {load_lbs:,.0f} lb load "
            f"> {LOAD_NO_TRAVEL_THRESHOLD_LBS:,} lb → No Travel"
        )
    if 35 <= mph < 45 and load_lbs > LOAD_SEVERE_THRESHOLD_LBS:
        return Risk.SEVERE, (
            f"Wind {mph:.1f} mph with {load_lbs:,.0f} lb load "
            f"> {LOAD_SEVERE_THRESHOLD_LBS:,} lb → Severe"
        )
    return base, None


def classify_rain(in_per_hr: float) -> Risk:
    if in_per_hr < 0.10:
        return Risk.LOW
    if in_per_hr < 0.25:
        return Risk.MODERATE
    if in_per_hr < 0.50:
        return Risk.HIGH
    if in_per_hr <= 1.00:
        return Risk.SEVERE
    return Risk.NO_TRAVEL


def classify_snow(in_per_hr: float) -> Risk:
    if in_per_hr < 0.5:
        return Risk.LOW
    if in_per_hr < 1.0:
        return Risk.MODERATE
    if in_per_hr < 2.0:
        return Risk.HIGH
    if in_per_hr <= 3.0:
        return Risk.SEVERE
    return Risk.NO_TRAVEL


def worst(*risks: Risk) -> Risk:
    if any(r is Risk.UNKNOWN for r in risks):
        return Risk.UNKNOWN
    return max(risks, key=lambda r: _ORDINAL[r])


_ELEVATED = {Risk.HIGH, Risk.SEVERE, Risk.NO_TRAVEL}


@dataclass(frozen=True)
class CheckpointRisk:
    wind: Risk
    rain: Risk
    snow: Risk
    overall: Risk
    reasons: list[str] = field(default_factory=list)


def classify_checkpoint(
    wind_mph: float | None,
    rain_in_per_hr: float | None,
    snow_in_per_hr: float | None,
    load_lbs: float,
) -> CheckpointRisk:
    """Classify a checkpoint. Any missing measurement ⇒ Unknown overall (never Low)."""
    if wind_mph is None or rain_in_per_hr is None or snow_in_per_hr is None:
        return CheckpointRisk(
            wind=Risk.UNKNOWN if wind_mph is None else classify_wind(wind_mph, load_lbs)[0],
            rain=Risk.UNKNOWN if rain_in_per_hr is None else classify_rain(rain_in_per_hr),
            snow=Risk.UNKNOWN if snow_in_per_hr is None else classify_snow(snow_in_per_hr),
            overall=Risk.UNKNOWN,
            reasons=["Forecast unavailable for this checkpoint/time"],
        )

    wind, override = classify_wind(wind_mph, load_lbs)
    rain = classify_rain(rain_in_per_hr)
    snow = classify_snow(snow_in_per_hr)
    reasons: list[str] = []
    if override:
        reasons.append(override)
    elif wind in _ELEVATED:
        reasons.append(f"Wind {wind_mph:.1f} mph → {wind.value}")
    if rain in _ELEVATED:
        reasons.append(f"Rain {rain_in_per_hr:.2f} in/hr → {rain.value}")
    if snow in _ELEVATED:
        reasons.append(f"Snowfall {snow_in_per_hr:.2f} in/hr → {snow.value}")
    return CheckpointRisk(wind, rain, snow, worst(wind, rain, snow), reasons)
