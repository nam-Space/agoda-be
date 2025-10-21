from rest_framework import serializers
from .models import Review
from bookings.models import ServiceType


class ReviewSerializer(serializers.ModelSerializer):
    service_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "service_type",
            "service_type_name",
            "service_ref_id",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["user", "created_at", "service_type_name"]

    def get_service_type_name(self, obj):
        return ServiceType(obj.service_type).label
