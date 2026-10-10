"""Structured error responses: {"error": {"code", "message", "details"?}} (spec §9)."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from apps.providers_errors import ProviderError


def error_response(code: str, message: str, http_status: int, details=None) -> Response:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return Response(body, status=http_status)


def exception_handler(exc, context):
    if isinstance(exc, ProviderError):
        return error_response(exc.code, str(exc), exc.status_code)
    if isinstance(exc, ValidationError):
        return error_response(
            "VALIDATION_ERROR", "Invalid request.", status.HTTP_400_BAD_REQUEST, exc.detail
        )
    response = drf_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        return error_response(
            getattr(exc, "default_code", "ERROR").upper(),
            str(detail or "Request failed."),
            response.status_code,
        )
    return None
