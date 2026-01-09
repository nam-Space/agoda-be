from rest_framework import serializers
from .models import Room, RoomImage, RoomBookingDetail, RoomAmenity, PhysicalRoom
from hotels.serializers import HotelCreateSerializer, HotelSimpleSerializer
from accounts.serializers import UserSerializer
from hotels.models import Hotel
from django.utils import timezone
from datetime import timedelta
from bookings.constants.booking_status import BookingStatus


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
        if "start_date" not in validated_data or validated_data["start_date"] is None:
            validated_data["start_date"] = timezone.now().date()
        if "end_date" not in validated_data or validated_data["end_date"] is None:
            validated_data["end_date"] = timezone.now().date() + timedelta(days=365)

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


class PhysicalRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhysicalRoom
        fields = ["id", "room", "code", "floor", "is_available"]


class RoomBookingDetailSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)
    owner_hotel = UserSerializer(read_only=True)
    physical_rooms = PhysicalRoomSerializer(many=True, read_only=True)

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
            "physical_rooms",
        ]


class RoomBookingDetailCreateSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    # FE có thể truyền danh sách mã phòng cụ thể (VD: ["101", "102"])
    physical_room_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

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
            "physical_room_codes",
        ]

    def validate(self, data):
        """
        Validate theo loại phòng (Room): số lượng, sức chứa, overlap theo tổng số phòng.
        Việc gán phòng cụ thể sẽ được xử lý ở create().
        """
        room = data.get("room")
        check_in = data.get("check_in")
        check_out = data.get("check_out")
        num_guests = data.get("num_guests")
        room_count = data.get("room_count", 1)
        physical_room_codes = data.get("physical_room_codes") or []

        # Validate dates
        if check_in >= check_out:
            raise serializers.ValidationError("Check-out must be after check-in")
        if check_in < timezone.now():
            raise serializers.ValidationError("Check-in cannot be in the past")

        # Validate capacity
        if num_guests > room.capacity:
            raise serializers.ValidationError(
                f"Number of guests ({num_guests}) exceeds room capacity ({room.capacity})"
            )

        # Validate room_count theo available_rooms
        if room_count > room.available_rooms:
            raise serializers.ValidationError(
                f"Only {room.available_rooms} rooms available"
            )

        # Nếu FE truyền danh sách phòng cụ thể thì số lượng phải match
        if physical_room_codes and len(physical_room_codes) != room_count:
            raise serializers.ValidationError(
                {
                    "physical_room_codes": [
                        "Số lượng phòng cụ thể phải khớp với room_count"
                    ]
                }
            )

        # Validate availability tổng quan dựa trên RoomBookingDetail + total_rooms
        overlapping_bookings = (
            RoomBookingDetail.objects.filter(
                room=room, check_in__lt=check_out, check_out__gt=check_in
            )
            .exclude(booking__status__in=[BookingStatus.CANCELLED])
        )  # Loại cancelled
        total_booked_rooms = sum(b.room_count for b in overlapping_bookings)
        if total_booked_rooms + room_count > room.total_rooms:
            raise serializers.ValidationError("Room not available for selected dates")

        return data

    def create(self, validated_data):
        """
        Tạo RoomBookingDetail và tự động gán danh sách phòng cụ thể (PhysicalRoom)
        còn trống cho khoảng thời gian check_in/check_out.
        """
        room = validated_data["room"]
        check_in = validated_data["check_in"]
        check_out = validated_data["check_out"]
        room_count = validated_data.get("room_count", 1)
        physical_room_codes = validated_data.pop("physical_room_codes", [])

        selected_rooms = []

        if physical_room_codes:
            # FE đã chọn phòng cụ thể: validate & lấy danh sách đó
            for code in physical_room_codes:
                pr = PhysicalRoom.objects.filter(
                    room=room, code=code, is_available=True
                ).first()
                if not pr:
                    raise serializers.ValidationError(
                        {
                            "physical_room_codes": [
                                f"Phòng {code} không tồn tại hoặc không khả dụng"
                            ]
                        }
                    )
                # Kiểm tra trùng lịch với các booking khác
                overlapping = RoomBookingDetail.objects.filter(
                    physical_rooms=pr, check_in__lt=check_out, check_out__gt=check_in
                ).exclude(booking__status__in=[BookingStatus.CANCELLED])
                if overlapping.exists():
                    raise serializers.ValidationError(
                        {
                            "physical_room_codes": [
                                f"Phòng {code} đã được đặt trong khoảng thời gian này"
                            ]
                        }
                    )
                selected_rooms.append(pr)
        else:
            # Không truyền phòng cụ thể -> tự động chọn
            candidates = PhysicalRoom.objects.filter(
                room=room, is_available=True
            ).order_by("id")

            free_physical_rooms = []
            for pr in candidates:
                # Kiểm tra xem phòng cụ thể này có bị trùng lịch hay không
                overlapping = RoomBookingDetail.objects.filter(
                    physical_rooms=pr, check_in__lt=check_out, check_out__gt=check_in
                ).exclude(booking__status__in=[BookingStatus.CANCELLED])

                if not overlapping.exists():
                    free_physical_rooms.append(pr)

                if len(free_physical_rooms) >= room_count:
                    break

            if len(free_physical_rooms) < room_count:
                raise serializers.ValidationError(
                    "Not enough specific rooms (physical rooms) available for selected dates"
                )

            selected_rooms = free_physical_rooms

        # Tạo RoomBookingDetail
        instance = RoomBookingDetail.objects.create(**validated_data)
        # Gán danh sách phòng cụ thể
        instance.physical_rooms.set(selected_rooms)

        # Đánh dấu các phòng cụ thể này tạm thời không còn khả dụng
        PhysicalRoom.objects.filter(id__in=[pr.id for pr in selected_rooms]).update(
            is_available=False
        )

        return instance
