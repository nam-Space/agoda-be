from rest_framework import serializers
from .models import Hotel, HotelImage
from cities.models import City
from cities.serializers import CityCreateSerializer


class HotelImageSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của khách sạn
    hotel = serializers.PrimaryKeyRelatedField(queryset=Hotel.objects.all())

    class Meta:
        model = HotelImage
        fields = "__all__"


class HotelSerializer(serializers.ModelSerializer):
    images = HotelImageSerializer(many=True, read_only=True)
    city = CityCreateSerializer(read_only=True)
    city_id = serializers.IntegerField(source="city.id", read_only=True)

    class Meta:
        model = Hotel
        fields = "__all__"


class HotelCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của thành phố
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    class Meta:
        model = Hotel
        fields = [
            "city",
            "name",
            "description",
            "lat",
            "lng",
            "location",
            "nearbyLocation",
            "point",
            "mostFeature",
            "facilities",
            "withUs",
            "usefulInformation",
            "amenitiesAndFacilities",
            "locationInfo",
            "regulation",
            "avg_star",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết
