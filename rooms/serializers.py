from rest_framework import serializers
from .models import Room, RoomImage, RoomBookingDetail


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"

class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = "__all__"

class RoomBookingDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomBookingDetail
        fields = [
            "room",
            "check_in",
            "check_out",
            "num_guests"
        ]