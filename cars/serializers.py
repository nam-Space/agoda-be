from rest_framework import serializers
from .models import Car, CarBookingDetail
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


class CarSerializer(serializers.ModelSerializer):
    user = UserSerializer()  # tài xế

    class Meta:
        model = Car
        fields = "__all__"


class CarCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của tài xế
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = Car
        fields = [
            "id",
            "user",
            "name",
            "description",
            "capacity",
            "luggage",
            "point",
            "avg_star",
            "price_per_km",
            "avg_speed",
            "image",
        ]  # Chỉ có những trường cần thiết


class CarBookingDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = CarBookingDetail
        fields = [
            "car",
            "pickup_location",
            "dropoff_location",
            "pickup_datetime",
            "driver_required",
            "distance_km",
        ]
