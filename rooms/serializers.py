from rest_framework import serializers
from .models import Room, RoomImage, RoomBookingDetail, RoomAmenity
from hotels.serializers import HotelCreateSerializer, HotelSimpleSerializer
from accounts.serializers import UserSerializer
from hotels.models import Hotel


class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    hotel = HotelSimpleSerializer(read_only=True)
    images = RoomImageSerializer(many=True, read_only=True)
    promotion = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = "__all__"

    def get_promotion(self, obj):
        return obj.get_active_promotion()

    def get_has_promotion(self, obj):
        return obj.get_active_promotion() is not None


class RoomCreateSerializer(serializers.ModelSerializer):
    hotel = serializers.PrimaryKeyRelatedField(queryset=Hotel.objects.all())
    # images = RoomImageSerializer(many=True, read_only=True)
    promotion = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()

    amenities_data = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Room
        fields = "__all__"

    def get_promotion(self, obj):
        return obj.get_active_promotion()

    def get_has_promotion(self, obj):
        return obj.get_active_promotion() is not None

    def create(self, validated_data):
        amenities_data = validated_data.pop("amenities_data", [])
        room = Room.objects.create(**validated_data)

        # Tạo RoomAmenity
        for amenity in amenities_data:
            RoomAmenity.objects.create(room=room, name=amenity.get("name"))

        return room


class RoomAmenitySerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)

    class Meta:
        model = RoomAmenity
        fields = "__all__"


class RoomAmenityCreateSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = RoomAmenity
        fields = "__all__"


class RoomBookingDetailSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)
    owner_hotel = UserSerializer(read_only=True)

    class Meta:
        model = RoomBookingDetail
        fields = [
            "id",
            "room",
            "check_in",
            "check_out",
            "num_guests",
            "room_type",
            "room_count",
            "owner_hotel",
            "total_price",
            "discount_amount",
            "final_price",
        ]


class RoomBookingDetailCreateSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = RoomBookingDetail
        fields = [
            "id",
            "room",
            "check_in",
            "check_out",
            "num_guests",
            "room_type",
            "room_count",
        ]
