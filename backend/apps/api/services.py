"""Orchestration service for weather-aware route analysis (docs/PROJECT_SPEC.md §2, §6, §7, §9)."""

from __future__ import annotations

import bisect
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings

from apps.providers_errors import ProviderError, ProviderNotConfigured
from apps.risk.classification import CheckpointRisk, classify_checkpoint
from apps.risk.ranking import RiskInterval, compute_metrics, recommend
from apps.routing.domain import LatLon, Route, RouteRequest, RouteResult
from apps.routing.geometry import (
    CheckpointPosition,
    cumulative_distances,
    eta_at_distance,
    generate_checkpoints,
)
from apps.routing.providers.base import RoutingProvider
from apps.routing.providers.google_routes import GoogleRoutesProvider
from apps.weather.providers.base import HourlyWeather, LocationForecast, WeatherProvider
from apps.weather.providers.open_meteo import OpenMeteoProvider
from apps.weather.timematch import match_forecast


def slice_polyline_by_distance(
    polyline: list[LatLon],
    cum_dists: list[float],
    start_d: float,
    end_d: float,
    start_pt: LatLon,
    end_pt: LatLon,
) -> list[LatLon]:
    """Extract polyline vertices that fall strictly inside (start_d, end_d),

    bracketed by start_pt and end_pt.
    """
    total = cum_dists[-1]
    s_clamp = max(0.0, min(start_d, total))
    e_clamp = max(0.0, min(end_d, total))

    # Find internal vertices
    # Vertices with cum_dist > s_clamp and cum_dist < e_clamp
    i_start = bisect.bisect_right(cum_dists, s_clamp + 1e-9)
    i_end = bisect.bisect_left(cum_dists, e_clamp - 1e-9)

    interior = polyline[i_start:i_end]
    coords = [start_pt]
    for pt in interior:
        if pt != coords[-1]:
            coords.append(pt)
    if end_pt != coords[-1]:
        coords.append(end_pt)
    return coords


def find_closest_forecast(
    forecasts: list[LocationForecast], target_lat: float, target_lon: float
) -> LocationForecast | None:
    """Associate returned forecast with the requested coordinate.

    Uses Euclidean distance in degrees. If forecasts list is empty, returns None.
    """
    if not forecasts:
        return None
    best_fc = None
    best_dist = float("inf")
    for fc in forecasts:
        # Distance squared
        d_sq = (fc.lat - target_lat) ** 2 + (fc.lon - target_lon) ** 2
        if d_sq < best_dist:
            best_dist = d_sq
            best_fc = fc
    # Only match if reasonably close (within ~1.0 degree)
    if best_dist <= 1.0:
        return best_fc
    return None


class RouteAnalysisService:
    def __init__(
        self,
        routing_provider: RoutingProvider | None = None,
        weather_provider: WeatherProvider | None = None,
    ):
        if routing_provider is not None:
            self._routing_provider = routing_provider
        else:
            api_key = settings.GOOGLE_ROUTES_API_KEY
            if not api_key:
                raise ProviderNotConfigured(
                    "GOOGLE_ROUTES_API_KEY is not configured on the server."
                )
            self._routing_provider = GoogleRoutesProvider(
                api_key=api_key,
                timeout=settings.PROVIDER_TIMEOUT_SECONDS,
            )

        if weather_provider is not None:
            self._weather_provider = weather_provider
        else:
            self._weather_provider = OpenMeteoProvider(
                base_url=settings.OPEN_METEO_BASE_URL,
                timeout=settings.PROVIDER_TIMEOUT_SECONDS,
                cache_ttl=settings.WEATHER_CACHE_TTL_SECONDS,
            )

    def analyze(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        origin: str = validated_data["origin"]
        destination: str = validated_data["destination"]
        departure_time: datetime = validated_data["departure_time"]  # UTC datetime
        load_weight_lbs: float = float(validated_data["load_weight_lbs"])
        checkpoint_interval_miles: float = float(validated_data["checkpoint_interval_miles"])
        forecast_offset_hours: int = int(validated_data.get("forecast_offset_hours", 0))

        # Effective departure time with shifted-scenario offset
        effective_departure = departure_time + timedelta(hours=forecast_offset_hours)
        departure_iso = effective_departure.strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Compute routes
        route_req = RouteRequest(
            origin=origin,
            destination=destination,
            departure_time_iso=departure_iso,
        )
        route_result: RouteResult = self._routing_provider.compute_routes(route_req)
        routes: list[Route] = route_result.routes
        warnings: list[dict[str, str]] = list(route_result.warnings)

        if not routes:
            return {
                "request": {
                    "origin": origin,
                    "destination": destination,
                    "departure_time": departure_time.isoformat(),
                    "load_weight_lbs": load_weight_lbs,
                    "checkpoint_interval_miles": int(checkpoint_interval_miles),
                    "forecast_offset_hours": forecast_offset_hours,
                },
                "effective_departure_time": effective_departure.isoformat(),
                "routes": [],
                "recommendation": {
                    "status": "NO_ROUTES",
                    "route_id": None,
                    "deciding_criterion": None,
                    "explanation": "No routes were returned by the routing provider.",
                },
                "warnings": warnings,
                "attribution": {
                    "routing": "Google Routes API",
                    "weather": "Open-Meteo.com",
                },
            }

        # 2. Collect unique coordinates across all routes for batch weather lookup
        # Checkpoint generation per route
        route_cps_map: dict[str, list[CheckpointPosition]] = {}
        route_cum_map: dict[str, list[float]] = {}
        all_coords: list[tuple[float, float]] = []
        max_duration_seconds = 0.0

        for r in routes:
            pts = r.polyline
            if len(pts) < 2:
                continue
            cum = cumulative_distances(pts)
            route_cum_map[r.id] = cum
            cps = generate_checkpoints(pts, checkpoint_interval_miles)
            route_cps_map[r.id] = cps
            for cp in cps:
                all_coords.append((cp.lat, cp.lon))
            if r.duration_seconds > max_duration_seconds:
                max_duration_seconds = r.duration_seconds

        # Deduplicate coordinates while preserving order (rounding to 3 decimals)
        seen_coord: set[tuple[float, float]] = set()
        deduped_coords: list[tuple[float, float]] = []
        for lat, lon in all_coords:
            key = (round(lat, 3), round(lon, 3))
            if key not in seen_coord:
                seen_coord.add(key)
                deduped_coords.append((lat, lon))

        # Determine overall time window for weather query
        window_start = effective_departure
        window_end = effective_departure + timedelta(seconds=max_duration_seconds + 3600)

        # 3. Retrieve weather forecasts in bounded batches
        weather_forecasts: list[LocationForecast] = []
        weather_fetch_failed = False
        batch_size = 50

        for i in range(0, len(deduped_coords), batch_size):
            chunk = deduped_coords[i : i + batch_size]
            try:
                chunk_fcs = self._weather_provider.hourly_forecasts(chunk, window_start, window_end)
                weather_forecasts.extend(chunk_fcs)
            except ProviderError:
                weather_fetch_failed = True
            except Exception:
                weather_fetch_failed = True

        if weather_fetch_failed:
            warnings.append(
                {
                    "code": "WEATHER_PROVIDER_UNAVAILABLE",
                    "message": (
                        "Weather provider experienced an error or outage; "
                        "affected intervals are marked Unknown."
                    ),
                }
            )

        # 4. Process each route: ETAs, weather matching, risk classification, segments, metrics
        analyzed_routes: list[dict[str, Any]] = []
        candidate_metrics: dict[str, Any] = {}
        has_any_incomplete_weather = False

        for r in routes:
            cps = route_cps_map.get(r.id, [])
            cum_dists = route_cum_map.get(r.id, [])
            analyzed_cps: list[dict[str, Any]] = []
            risk_intervals: list[RiskInterval] = []
            route_unsafe_reasons: list[str] = []
            route_has_incomplete = False

            for cp in cps:
                eta = eta_at_distance(
                    effective_departure,
                    cp.distance_miles,
                    r.distance_miles,
                    r.duration_seconds,
                    r.steps,
                )
                loc_fc = find_closest_forecast(weather_forecasts, cp.lat, cp.lon)
                hw: HourlyWeather | None = match_forecast(loc_fc, eta) if loc_fc else None

                wind_mph = hw.wind_mph if hw else None
                rain_in = hw.rain_in_per_hr if hw else None
                snow_in = hw.snow_in_per_hr if hw else None
                forecast_available = (
                    hw is not None
                    and wind_mph is not None
                    and rain_in is not None
                    and snow_in is not None
                )

                if not forecast_available:
                    route_has_incomplete = True
                    has_any_incomplete_weather = True

                cp_risk: CheckpointRisk = classify_checkpoint(
                    wind_mph, rain_in, snow_in, load_weight_lbs
                )
                risk_intervals.append(RiskInterval(cp.represented_miles, cp_risk.overall))

                if cp_risk.overall.value == "No Travel":
                    for reason in cp_risk.reasons:
                        if reason not in route_unsafe_reasons:
                            route_unsafe_reasons.append(reason)

                analyzed_cps.append(
                    {
                        "index": cp.index,
                        "lat": round(cp.lat, 6),
                        "lon": round(cp.lon, 6),
                        "distance_miles": round(cp.distance_miles, 2),
                        "interval_start_miles": round(cp.interval_start_miles, 2),
                        "interval_end_miles": round(cp.interval_end_miles, 2),
                        "represented_miles": round(cp.represented_miles, 2),
                        "eta": eta.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "weather": {
                            "wind_mph": round(wind_mph, 1) if wind_mph is not None else None,
                            "rain_in_per_hr": round(rain_in, 2) if rain_in is not None else None,
                            "snow_in_per_hr": round(snow_in, 2) if snow_in is not None else None,
                            "forecast_time": hw.time.strftime("%Y-%m-%dT%H:%M:%SZ") if hw else None,
                        },
                        "forecast_available": forecast_available,
                        "risk": {
                            "wind": cp_risk.wind.value,
                            "rain": cp_risk.rain.value,
                            "snow": cp_risk.snow.value,
                            "overall": cp_risk.overall.value,
                        },
                        "reasons": cp_risk.reasons,
                    }
                )

            # Build segments corresponding to checkpoint intervals
            segments: list[dict[str, Any]] = []
            for i, cp in enumerate(cps):
                cp_dict = analyzed_cps[i]
                start_pt = (
                    (r.polyline[0][0], r.polyline[0][1])
                    if i == 0
                    else (
                        (cps[i - 1].lat + cp.lat) / 2,
                        (cps[i - 1].lon + cp.lon) / 2,
                    )
                )
                end_pt = (
                    (r.polyline[-1][0], r.polyline[-1][1])
                    if i == len(cps) - 1
                    else (
                        (cp.lat + cps[i + 1].lat) / 2,
                        (cp.lon + cps[i + 1].lon) / 2,
                    )
                )
                seg_coords = slice_polyline_by_distance(
                    r.polyline,
                    cum_dists,
                    cp.interval_start_miles,
                    cp.interval_end_miles,
                    start_pt,
                    end_pt,
                )
                segments.append(
                    {
                        "start_miles": round(cp.interval_start_miles, 2),
                        "end_miles": round(cp.interval_end_miles, 2),
                        "risk": cp_dict["risk"]["overall"],
                        "coordinates": [[round(lat, 6), round(lon, 6)] for lat, lon in seg_coords],
                    }
                )

            # Compute route metrics
            metrics = compute_metrics(risk_intervals, r.duration_seconds)
            candidate_metrics[r.id] = metrics

            analyzed_routes.append(
                {
                    "id": r.id,
                    "label": r.label,
                    "description": r.description,
                    "distance_miles": round(r.distance_miles, 2),
                    "duration_seconds": round(r.duration_seconds, 1),
                    "polyline": [[round(lat, 6), round(lon, 6)] for lat, lon in r.polyline],
                    "checkpoints": analyzed_cps,
                    "segments": segments,
                    "metrics": {
                        "severe_miles": round(metrics.severe_miles, 2),
                        "high_miles": round(metrics.high_miles, 2),
                        "moderate_miles": round(metrics.moderate_miles, 2),
                        "low_miles": round(metrics.low_miles, 2),
                        "no_travel_miles": round(metrics.no_travel_miles, 2),
                        "unknown_miles": round(metrics.unknown_miles, 2),
                        "average_risk": (
                            round(metrics.average_risk, 2)
                            if metrics.average_risk is not None
                            else None
                        ),
                        "duration_seconds": round(metrics.duration_seconds, 1),
                    },
                    "eligible": metrics.eligible,
                    "weather_incomplete": route_has_incomplete,
                    "unsafe_reasons": route_unsafe_reasons,
                }
            )

        # 5. Recommendation
        rec = recommend(candidate_metrics)
        rec_data = {
            "status": rec.status,
            "route_id": rec.route_id,
            "deciding_criterion": rec.deciding_criterion,
            "explanation": rec.explanation,
        }

        if has_any_incomplete_weather:
            warnings.append(
                {
                    "code": "FORECAST_INCOMPLETE",
                    "message": (
                        "One or more checkpoints lack full forecast data; "
                        "routes are marked incomplete and cannot be verified safe."
                    ),
                }
            )

        return {
            "request": {
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time.isoformat(),
                "load_weight_lbs": load_weight_lbs,
                "checkpoint_interval_miles": int(checkpoint_interval_miles),
                "forecast_offset_hours": forecast_offset_hours,
            },
            "effective_departure_time": effective_departure.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "routes": analyzed_routes,
            "recommendation": rec_data,
            "warnings": warnings,
            "attribution": {
                "routing": "Google Routes API",
                "weather": "Open-Meteo.com",
            },
        }
