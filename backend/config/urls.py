from django.urls import include, path

from apps.api.views import HealthView

urlpatterns = [
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/v1/", include("apps.api.urls")),
]
