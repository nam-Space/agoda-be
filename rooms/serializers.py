from rest_framework import serializers
from .models import Room, RoomImage, RoomBookingDetail, RoomAmenity
from hotels.serializers import HotelCreateSerializer
from accounts.serializers import UserSerializer


class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    hotel = HotelCreateSerializer(read_only=True)
    images = RoomImageSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = "__all__"


class RoomAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomAmenity
        fields = ["id", "name"]


class RoomBookingDetailSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)
    owner_hotel = UserSerializer(read_only=True)

    class Meta:
        model = RoomBookingDetail
        fields = ["id", "room", "check_in", "check_out", "num_guests", "owner_hotel"]


class RoomBookingDetailCreateSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = RoomBookingDetail
        fields = ["id", "room", "check_in", "check_out", "num_guests"]
