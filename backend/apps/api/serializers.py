"""Request contract for POST /api/v1/route-analysis/ (spec §9)."""

from __future__ import annotations

from datetime import UTC

from rest_framework import serializers

from apps.routing.geometry import ALLOWED_INTERVALS_MILES


class RouteAnalysisRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=200, trim_whitespace=True)
    destination = serializers.CharField(max_length=200, trim_whitespace=True)
    departure_time = serializers.DateTimeField()
    load_weight_lbs = serializers.FloatField(min_value=0, max_value=200_000)
    checkpoint_interval_miles = serializers.ChoiceField(choices=ALLOWED_INTERVALS_MILES)
    forecast_offset_hours = serializers.IntegerField(min_value=0, max_value=48, default=0)

    def to_internal_value(self, data):
        # Reject naive timestamps before DRF silently applies the server time zone.
        raw = data.get("departure_time") if hasattr(data, "get") else None
        if isinstance(raw, str):
            s = raw.strip()
            tail = s[10:] if len(s) > 10 else ""
            if not (s.endswith("Z") or "+" in tail or "-" in tail):
                raise serializers.ValidationError(
                    {"departure_time": ["Include a UTC offset, e.g. 2026-10-11T08:00:00-05:00."]}
                )
        return super().to_internal_value(data)

    def validate_load_weight_lbs(self, value: float) -> float:
        if value <= 0:
            raise serializers.ValidationError("Load weight must be greater than 0 lb.")
        return value

    def validate_departure_time(self, value):
        return value.astimezone(UTC)

    def validate(self, attrs):
        if attrs["origin"].casefold() == attrs["destination"].casefold():
            raise serializers.ValidationError(
                {"destination": ["Destination must differ from origin."]}
            )
        return attrs
