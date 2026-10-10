"""Distance-based checkpoint generation and ETA interpolation (docs/PROJECT_SPEC.md §6–§7)."""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from .domain import LatLon, RouteStep

EARTH_RADIUS_MILES = 3958.7613
ALLOWED_INTERVALS_MILES = (10, 25, 50)


def haversine_miles(a: LatLon, b: LatLon) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(min(1.0, h)))


def cumulative_distances(points: list[LatLon]) -> list[float]:
    out = [0.0]
    for i in range(1, len(points)):
        out.append(out[-1] + haversine_miles(points[i - 1], points[i]))
    return out


def point_at_distance(points: list[LatLon], cum: list[float], d: float) -> LatLon:
    if d <= 0:
        return points[0]
    if d >= cum[-1]:
        return points[-1]
    i = bisect.bisect_right(cum, d)  # cum[i-1] <= d < cum[i]
    seg = cum[i] - cum[i - 1]
    t = 0.0 if seg == 0 else (d - cum[i - 1]) / seg
    (a_lat, a_lon), (b_lat, b_lon) = points[i - 1], points[i]
    return (a_lat + (b_lat - a_lat) * t, a_lon + (b_lon - a_lon) * t)


@dataclass(frozen=True)
class CheckpointPosition:
    index: int
    lat: float
    lon: float
    distance_miles: float
    interval_start_miles: float
    interval_end_miles: float

    @property
    def represented_miles(self) -> float:
        return self.interval_end_miles - self.interval_start_miles


def generate_checkpoints(points: list[LatLon], interval_miles: float) -> list[CheckpointPosition]:
    """Checkpoints at 0, N, 2N, … and the destination, using midpoint interval allocation.

    Distances are measured along the decoded geometry (never by vertex index).
    """
    if interval_miles <= 0:
        raise ValueError("interval_miles must be positive")
    if len(points) < 2:
        raise ValueError("Route geometry needs at least two points")
    cum = cumulative_distances(points)
    total = cum[-1]
    dists = [0.0]
    k = 1
    while k * interval_miles < total - 1e-9:
        dists.append(k * interval_miles)
        k += 1
    if total > 0:
        dists.append(total)
    out: list[CheckpointPosition] = []
    for i, d in enumerate(dists):
        start = 0.0 if i == 0 else (dists[i - 1] + d) / 2
        end = total if i == len(dists) - 1 else (d + dists[i + 1]) / 2
        lat, lon = point_at_distance(points, cum, d)
        out.append(CheckpointPosition(i, lat, lon, d, start, end))
    return out


def eta_at_distance(
    departure: datetime,
    distance_miles: float,
    total_distance_miles: float,
    total_duration_seconds: float,
    steps: list[RouteStep] | None = None,
) -> datetime:
    """ETA at a cumulative distance.

    Uses the step (distance, duration) profile scaled to the total duration when steps exist;
    otherwise falls back to a distance-proportional approximation.
    """
    if total_distance_miles <= 0:
        return departure
    d = max(0.0, min(distance_miles, total_distance_miles))
    step_dist = sum(s.distance_miles for s in steps or [])
    step_dur = sum(s.duration_seconds for s in steps or [])
    if not steps or step_dist <= 0 or step_dur <= 0:
        return departure + timedelta(seconds=total_duration_seconds * d / total_distance_miles)

    # Map d (route-geometry miles) onto step-distance miles, then scale step time to the total.
    target = d * step_dist / total_distance_miles
    dist_scale = total_duration_seconds / step_dur
    acc_d = acc_t = 0.0
    for s in steps:
        if acc_d + s.distance_miles >= target:
            frac = 0.0 if s.distance_miles == 0 else (target - acc_d) / s.distance_miles
            acc_t += s.duration_seconds * frac
            break
        acc_d += s.distance_miles
        acc_t += s.duration_seconds
    return departure + timedelta(seconds=acc_t * dist_scale)
