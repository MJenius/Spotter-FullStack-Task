"""Google Routes API adapter (docs/PROJECT_SPEC.md §3.1)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from apps.providers_errors import (
    ProviderError,
    ProviderNotConfigured,
    ProviderRateLimited,
    ProviderTimeout,
)

from ..domain import Route, RouteRequest, RouteResult, RouteStep
from ..polyline import decode_polyline

COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
METERS_PER_MILE = 1609.344
FIELD_MASK = ",".join(
    [
        "routes.distanceMeters",
        "routes.duration",
        "routes.staticDuration",
        "routes.polyline.encodedPolyline",
        "routes.routeLabels",
        "routes.description",
        "routes.legs.steps.distanceMeters",
        "routes.legs.steps.staticDuration",
    ]
)


def _seconds(value: str | None) -> float:
    # Google durations are strings like "1234s".
    if not value:
        return 0.0
    return float(value.rstrip("s"))


def _waypoint(value: str) -> dict:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) == 2:
        try:
            lat, lng = float(parts[0]), float(parts[1])
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return {"location": {"latLng": {"latitude": lat, "longitude": lng}}}
        except ValueError:
            pass
    return {"address": value}


def normalize_routes(payload: dict) -> RouteResult:
    routes: list[Route] = []
    seen: set[str] = set()
    for raw in payload.get("routes") or []:
        encoded = (raw.get("polyline") or {}).get("encodedPolyline")
        if not encoded or encoded in seen:
            continue  # never duplicate or fabricate routes
        seen.add(encoded)
        steps = [
            RouteStep(
                distance_miles=(s.get("distanceMeters") or 0) / METERS_PER_MILE,
                duration_seconds=_seconds(s.get("staticDuration")),
            )
            for leg in raw.get("legs") or []
            for s in leg.get("steps") or []
        ]
        labels = raw.get("routeLabels") or []
        try:
            decoded = decode_polyline(encoded)
        except Exception:
            continue  # Ignore routes with malformed polylines safely
        routes.append(
            Route(
                id=f"route-{len(routes)}",
                label=labels[0] if labels else "ROUTE",
                description=raw.get("description") or "",
                distance_miles=(raw.get("distanceMeters") or 0) / METERS_PER_MILE,
                duration_seconds=_seconds(raw.get("duration") or raw.get("staticDuration")),
                polyline=decoded,
                steps=steps,
            )
        )
    warnings = []
    if 0 < len(routes) < 3:
        warnings.append(
            {
                "code": "FEWER_THAN_THREE_ROUTES",
                "message": f"The routing provider returned {len(routes)} distinct route(s) "
                "for this trip; no routes were fabricated.",
            }
        )
    return RouteResult(routes=routes, warnings=warnings)


class GoogleRoutesProvider:
    def __init__(self, api_key: str, timeout: float = 15.0, client: httpx.Client | None = None):
        if not api_key:
            raise ProviderNotConfigured("GOOGLE_ROUTES_API_KEY is not configured on the server.")
        self._api_key = api_key
        self._timeout = timeout
        self._client = client

    def compute_routes(self, request: RouteRequest) -> RouteResult:
        # According to Google Routes API rules:
        # TRAFFIC_AWARE or TRAFFIC_AWARE_OPTIMAL requires departureTime to be set in the future.
        # If departure is in the past, Google Routes returns 400 if TRAFFIC_AWARE is sent.
        routing_preference = "TRAFFIC_AWARE"
        try:
            dep_dt = datetime.fromisoformat(request.departure_time_iso.replace("Z", "+00:00"))
            if dep_dt < datetime.now(UTC):
                routing_preference = "TRAFFIC_UNAWARE"
        except Exception:
            pass

        body = {
            "origin": _waypoint(request.origin),
            "destination": _waypoint(request.destination),
            "travelMode": "DRIVE",
            "routingPreference": routing_preference,
            "computeAlternativeRoutes": True,
            "departureTime": request.departure_time_iso,
            "polylineEncoding": "ENCODED_POLYLINE",
            "units": "IMPERIAL",
        }
        headers = {"X-Goog-Api-Key": self._api_key, "X-Goog-FieldMask": FIELD_MASK}
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(COMPUTE_ROUTES_URL, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("Routing provider timed out.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("Could not reach routing provider.") from exc
        finally:
            if self._client is None:
                client.close()
        if resp.status_code == 429:
            raise ProviderRateLimited("Routing provider rate limit reached.")
        if resp.status_code >= 400:
            status = (resp.json().get("error") or {}).get("status", "") if _is_json(resp) else ""
            raise ProviderError(f"Routing provider error (HTTP {resp.status_code} {status}).")
        return normalize_routes(resp.json())


def _is_json(resp: httpx.Response) -> bool:
    return "json" in resp.headers.get("content-type", "")
