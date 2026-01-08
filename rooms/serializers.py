from rest_framework import serializers
from .models import Room, RoomImage, RoomBookingDetail, RoomAmenity
from hotels.serializers import HotelCreateSerializer, HotelSimpleSerializer
from accounts.serializers import UserSerializer
from hotels.models import Hotel
from django.utils import timezone
from datetime import timedelta


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
        if 'start_date' not in validated_data or validated_data['start_date'] is None:
            validated_data['start_date'] = timezone.now().date()
        if 'end_date' not in validated_data or validated_data['end_date'] is None:
            validated_data['end_date'] = timezone.now().date() + timedelta(days=365)
        
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
    
    def validate(self, data):
        room = data.get('room')
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        num_guests = data.get('num_guests')
        room_count = data.get('room_count', 1)

        # Validate dates
        if check_in >= check_out:
            raise serializers.ValidationError("Check-out must be after check-in")
        if check_in < timezone.now():
            raise serializers.ValidationError("Check-in cannot be in the past")

        # Validate capacity
        if num_guests > room.capacity:
            raise serializers.ValidationError(f"Number of guests ({num_guests}) exceeds room capacity ({room.capacity})")

        # Validate room_count
        if room_count > room.available_rooms:
            raise serializers.ValidationError(f"Only {room.available_rooms} rooms available")

        # Validate availability (check overlap với existing bookings)
        overlapping_bookings = RoomBookingDetail.objects.filter(
            room=room,
            check_in__lt=check_out,
            check_out__gt=check_in
        ).exclude(booking__status__in=['CANCELLED'])  # Loại cancelled
        total_booked_rooms = sum(b.room_count for b in overlapping_bookings)
        if total_booked_rooms + room_count > room.total_rooms:
            raise serializers.ValidationError("Room not available for selected dates")

        return data
