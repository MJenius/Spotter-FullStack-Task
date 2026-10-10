from django.urls import path

from .views import RouteAnalysisView

urlpatterns = [
    path("route-analysis/", RouteAnalysisView.as_view(), name="route-analysis"),
]
