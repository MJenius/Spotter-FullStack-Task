"""Internal, provider-agnostic route model (docs/PROJECT_SPEC.md §7, §9)."""

from __future__ import annotations

from dataclasses import dataclass, field

LatLon = tuple[float, float]


@dataclass(frozen=True)
class RouteStep:
    distance_miles: float
    duration_seconds: float


@dataclass(frozen=True)
class Route:
    id: str
    label: str
    description: str
    distance_miles: float
    duration_seconds: float
    polyline: list[LatLon]
    steps: list[RouteStep] = field(default_factory=list)


@dataclass(frozen=True)
class RouteRequest:
    origin: str
    destination: str
    departure_time_iso: str  # RFC 3339 UTC


@dataclass(frozen=True)
class RouteResult:
    routes: list[Route]
    warnings: list[dict] = field(default_factory=list)
