from __future__ import annotations

from typing import Protocol

from ..domain import RouteRequest, RouteResult


class RoutingProvider(Protocol):
    def compute_routes(self, request: RouteRequest) -> RouteResult: ...
