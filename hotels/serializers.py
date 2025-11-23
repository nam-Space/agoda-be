from rest_framework import serializers
from .models import Hotel, HotelImage, UserHotelInteraction
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
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            "id", 
            "name", 
            "thumbnail", 
            "min_price", 
            "location",
            "avg_star",
            "review_count",
            "city"
            ]

    def get_thumbnail(self, obj):
        if obj.images.exists():
            return obj.images.first().image
        return None

class HotelSerializer(serializers.ModelSerializer):
    images = HotelImageSerializer(many=True, read_only=True)
    city = CityCreateSerializer(read_only=True)
    owner = UserSerializer(read_only=True)
    city_id = serializers.IntegerField(source="city.id", read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = Hotel
        fields = "__all__"


class HotelCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của thành phố
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    owner = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False,  # ✅ Không bắt buộc
        allow_null=True,  # ✅ Cho phép giá trị null
    )
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

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
            "review_count",
            "total_click",
            "total_positive",
            "total_negative",
            "total_neutral",
            "total_weighted_score",
        ]  # Chỉ có những trường cần thiết


class HotelSearchSerializer(serializers.ModelSerializer):
    images = HotelImageSerializer(many=True, read_only=True)
    city = CitySerializer(read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

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
            "total_click",
            "total_positive",
            "total_negative",
            "total_neutral",
            "weighted_score",
        ]


class UserHotelInteractionSerializer(serializers.ModelSerializer):
    hotel = HotelCreateSerializer(read_only=True)

    class Meta:
        model = UserHotelInteraction
        fields = "__all__"


class UserHotelInteractionCreateSerializer(serializers.ModelSerializer):
    hotel = serializers.PrimaryKeyRelatedField(queryset=Hotel.objects.all())

    class Meta:
        model = UserHotelInteraction
        fields = "__all__"
        read_only_fields = ["weighted_score", "last_interacted"]
