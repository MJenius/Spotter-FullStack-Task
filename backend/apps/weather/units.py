"""Explicit unit normalisation (docs/PROJECT_SPEC.md §3.2). Risk engine needs mph and in/hr."""

from __future__ import annotations

_SPEED_TO_MPH = {
    "mph": 1.0,
    "km/h": 1 / 1.609344,
    "m/s": 2.2369362920544,
    "kn": 1.150779448,
}
_DEPTH_TO_IN = {"inch": 1.0, "in": 1.0, "mm": 1 / 25.4, "cm": 1 / 2.54}


class UnknownUnitError(ValueError):
    pass


def speed_to_mph(value: float, unit: str) -> float:
    try:
        return value * _SPEED_TO_MPH[unit]
    except KeyError as exc:
        raise UnknownUnitError(f"Unsupported speed unit: {unit!r}") from exc


def depth_to_inches(value: float, unit: str) -> float:
    """Convert an hourly accumulation to inches; a 1-hour sum in inches equals in/hr."""
    try:
        return value * _DEPTH_TO_IN[unit]
    except KeyError as exc:
        raise UnknownUnitError(f"Unsupported depth unit: {unit!r}") from exc
