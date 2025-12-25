from rest_framework import serializers
from .models import Car, CarBookingDetail, UserCarInteraction
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


class CarSerializer(serializers.ModelSerializer):
    user = UserSerializer()  # tài xế
    promotion = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = "__all__"

    def get_promotion(self, obj):
        return obj.get_active_promotion()

    def get_has_promotion(self, obj):
        return obj.get_active_promotion() is not None


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
            "avg_star",
            "price_per_km",
            "avg_speed",
            "image",
        ]  # Chỉ có những trường cần thiết


class CarBookingDetailSerializer(serializers.ModelSerializer):
    car = CarSerializer()
    driver = UserSerializer(read_only=True)

    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    discount_amount = serializers.FloatField(read_only=True)
    final_price = serializers.FloatField(read_only=True)

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
            "dropoff_datetime",
            "driver_required",
            "distance_km",
            "total_time_estimate",
            "passenger_quantity_booking",
            "driver",
            "total_price",
            "discount_amount",
            "final_price",
            "status",
        ]


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
            "dropoff_datetime",
            "driver_required",
            "distance_km",
            "total_time_estimate",
            "passenger_quantity_booking",
            "status",
        ]


class CarBookingUpdateSerializer(serializers.ModelSerializer):
    car = serializers.PrimaryKeyRelatedField(
        queryset=Car.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CarBookingDetail
        fields = [
            "car",
            "pickup_location",
            "dropoff_location",
            "lat1",
            "lng1",
            "lat2",
            "lng2",
            "pickup_datetime",
            "dropoff_datetime",
            "driver_required",
            "distance_km",
            "total_time_estimate",
            "passenger_quantity_booking",
            "status",
        ]
        extra_kwargs = {
            field: {"required": False, "allow_null": True} for field in fields
        }


class UserCarInteractionSerializer(serializers.ModelSerializer):
    car = CarSerializer(read_only=True)

    class Meta:
        model = UserCarInteraction
        fields = "__all__"


class UserCarInteractionCreateSerializer(serializers.ModelSerializer):
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())

    class Meta:
        model = UserCarInteraction
        fields = "__all__"
        read_only_fields = ["weighted_score", "last_interacted"]
