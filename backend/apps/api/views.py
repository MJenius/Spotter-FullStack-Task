from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.providers_errors import ProviderNotConfigured

from .serializers import RouteAnalysisRequestSerializer
from .services import RouteAnalysisService


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
    """End-to-end route analysis workflow."""

    def post(self, request):
        serializer = RouteAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not settings.GOOGLE_ROUTES_API_KEY:
            raise ProviderNotConfigured("GOOGLE_ROUTES_API_KEY is not configured on the server.")
        service = RouteAnalysisService()
        result = service.analyze(serializer.validated_data)
        return Response(result, status=status.HTTP_200_OK)
