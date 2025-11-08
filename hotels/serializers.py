from rest_framework import serializers
from .models import Hotel, HotelImage
from cities.models import City
from cities.serializers import CityCreateSerializer, CitySerializer
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


class HotelImageSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của khách sạn
    hotel = serializers.PrimaryKeyRelatedField(queryset=Hotel.objects.all())

    class Meta:
        model = HotelImage
        fields = "__all__"


class HotelSimpleSerializer(serializers.ModelSerializer):
    images = HotelImageSerializer(many=True, read_only=True)
    city = CityCreateSerializer(read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Hotel
        fields = "__all__"


class HotelSerializer(serializers.ModelSerializer):
    images = HotelImageSerializer(many=True, read_only=True)
    city = CityCreateSerializer(read_only=True)
    owner = UserSerializer(read_only=True)
    city_id = serializers.IntegerField(source="city.id", read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    promotion = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()
    
    class Meta:
        model = Hotel
        fields = "__all__"

    def get_promotion(self, obj):
        return obj.get_active_promotion()

    def get_has_promotion(self, obj):
        return obj.get_active_promotion() is not None


class HotelCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của thành phố
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    owner = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Hotel
        fields = [
            "city",
            "owner",
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
            "min_price",
        ]  # Chỉ có những trường cần thiết

class HotelSearchSerializer(serializers.ModelSerializer):
    images = HotelImageSerializer(many=True, read_only=True)
    city = CitySerializer(read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Hotel
        fields = [
            "id",
            "images",
            "city",
            "owner",
            "city_id",
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
            "min_price",
        ]
