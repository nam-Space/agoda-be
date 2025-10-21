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
    car = CarSerializer()

    class Meta:
        model = CarBookingDetail

        fields = "__all__"


class CarBookingDetailCreateSerializer(serializers.ModelSerializer):
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())

    class Meta:
        model = CarBookingDetail

        fields = [
            "id",
            "car",
            "pickup_location",
            "dropoff_location",
            "lat1",
            "lng1",
            "lat2",
            "lng2",
            "pickup_datetime",
            "driver_required",
            "distance_km",
            "total_time_estimate",
            "passenger_quantity_booking",
        ]
