from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.providers_errors import ProviderNotConfigured

from .errors import error_response
from .serializers import RouteAnalysisRequestSerializer


class HealthView(APIView):
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "truck-routing-api",
                "version": "v1",
                "providers": {
                    # Only whether a key exists — never the key itself.
                    "routing_configured": bool(settings.GOOGLE_ROUTES_API_KEY),
                    "weather_base_url": settings.OPEN_METEO_BASE_URL,
                },
            }
        )


class RouteAnalysisView(APIView):
    """Stage-1: validates the contract; analysis orchestration is implemented in milestone 4."""

    def post(self, request):
        serializer = RouteAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not settings.GOOGLE_ROUTES_API_KEY:
            raise ProviderNotConfigured("GOOGLE_ROUTES_API_KEY is not configured on the server.")
        return error_response(
            "NOT_IMPLEMENTED",
            "Route analysis is not implemented yet (request validated successfully).",
            status.HTTP_501_NOT_IMPLEMENTED,
        )
