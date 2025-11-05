# bookings/serializers.py
from rest_framework import serializers
from .models import Booking, GuestInfo
from rooms.serializers import (
    RoomBookingDetailSerializer,
    RoomBookingDetailCreateSerializer,
)
from cars.serializers import (
    CarBookingDetailSerializer,
    CarBookingDetailCreateSerializer,
)
from flights.serializers import FlightBookingDetailSerializer
from activities.serializers import ActivityDateBookingDetailSerializer
from rooms.models import RoomBookingDetail
from cars.models import CarBookingDetail
from flights.models import FlightBookingDetail
from activities.models import ActivityDateBookingDetail
from .constants.service_type import ServiceType
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


class GuestInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestInfo
        fields = ["full_name", "email", "phone", "country", "special_request"]


class BookingSerializer(serializers.ModelSerializer):
    service_ref_id = serializers.IntegerField(
        required=False, allow_null=True
    )  # 👈 Thêm dòng này
    guest_info = GuestInfoSerializer(required=False)
    user = UserSerializer(read_only=True)
    # hotel_detail_data_create = RoomBookingDetailSerializer(required=False)
    # car_detail_data_create = CarBookingDetailCreateSerializer(required=False)
    # flight_detail_data_create = FlightBookingDetailSerializer(required=False)
    # activity_date_detail_data_create = ActivityDateBookingDetailSerializer(required=False)

    hotel_detail = serializers.SerializerMethodField()
    car_detail = serializers.SerializerMethodField()
    flight_detail = serializers.SerializerMethodField()
    activity_date_detail = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "booking_code",
            "service_type",
            "service_ref_id",
            "total_price",
            "status",
            "payment_status",
            "created_at",
            "guest_info",
            "hotel_detail",
            "car_detail",
            "flight_detail",
            "activity_date_detail",
        ]
        read_only_fields = ["id", "status", "payment_status", "created_at"]

    def get_hotel_detail(self, obj):
        if obj.service_type != ServiceType.HOTEL or not obj.service_ref_id:
            return None
        room_booking_detail = RoomBookingDetail.objects.filter(
            id=obj.service_ref_id
        ).first()
        if not room_booking_detail:
            return None
        return RoomBookingDetailSerializer(
            room_booking_detail, context=self.context
        ).data

    def get_car_detail(self, obj):
        if obj.service_type != ServiceType.CAR or not obj.service_ref_id:
            return None
        car_booking_detail = CarBookingDetail.objects.filter(
            id=obj.service_ref_id
        ).first()
        if not car_booking_detail:
            return None
        return CarBookingDetailSerializer(car_booking_detail, context=self.context).data

    def get_flight_detail(self, obj):
        if obj.service_type != ServiceType.FLIGHT or not obj.service_ref_id:
            return None
        flight_booking_detail = FlightBookingDetail.objects.filter(
            id=obj.service_ref_id
        ).first()
        if not flight_booking_detail:
            return None
        return FlightBookingDetailSerializer(
            flight_booking_detail, context=self.context
        ).data

    def get_activity_date_detail(self, obj):
        """Nếu review thuộc loại ACTIVITY thì trả dữ liệu ActivitySerializer"""
        if obj.service_type != ServiceType.ACTIVITY or not obj.service_ref_id:
            return None

        activity_date_booking_detail = ActivityDateBookingDetail.objects.filter(
            id=obj.service_ref_id
        ).first()
        if not activity_date_booking_detail:
            return None
        return ActivityDateBookingDetailSerializer(
            activity_date_booking_detail, context=self.context
        ).data

    def create(self, validated_data):
        guest_data = validated_data.pop("guest_info", None)

        # hotel_data = validated_data.pop("hotel_detail", None)
        # car_data = validated_data.pop("car_detail", None)
        # flight_data = validated_data.pop("flight_detail", None)
        # activity_data = validated_data.pop("activity_date_detail", None)

        # ✅ Gán user từ context (viewset tự gửi vào)
        request = self.context.get("request", None)
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user

        booking = Booking.objects.create(**validated_data)
        if guest_data:
            GuestInfo.objects.create(booking=booking, **guest_data)

        # service_type = booking.service_type
        # if service_type == ServiceType.HOTEL and hotel_data:
        #     RoomBookingDetail.objects.create(booking=booking, **hotel_data)
        # elif service_type == ServiceType.CAR and car_data:
        #     CarBookingDetail.objects.create(booking=booking, **car_data)
        # elif service_type == ServiceType.FLIGHT and flight_data:
        #     FlightBookingDetail.objects.create(booking=booking, **flight_data)
        # elif service_type == ServiceType.ACTIVITY and activity_data:
        #     ActivityDateBookingDetail.objects.create(booking=booking, **activity_data)

        return booking

    def update(self, instance, validated_data):
        # Lấy dữ liệu guest_info nếu có
        guest_info_data = validated_data.pop("guest_info", None)

        # Update Booking fields (nếu có)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update GuestInfo nếu có
        if guest_info_data:
            guest_info, created = GuestInfo.objects.get_or_create(booking=instance)
            for attr, value in guest_info_data.items():
                setattr(guest_info, attr, value)
            guest_info.save()

        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # chỉ giữ field tương ứng service_type
        service_type = instance.service_type
        if service_type == ServiceType.HOTEL:
            ret.pop("car_detail", None)
            ret.pop("flight_detail", None)
            ret.pop("activity_date_detail", None)
        elif service_type == ServiceType.CAR:
            ret.pop("hotel_detail", None)
            ret.pop("flight_detail", None)
            ret.pop("activity_date_detail", None)
        elif service_type == ServiceType.FLIGHT:
            ret.pop("hotel_detail", None)
            ret.pop("car_detail", None)
            ret.pop("activity_date_detail", None)
        elif service_type == ServiceType.ACTIVITY:
            ret.pop("hotel_detail", None)
            ret.pop("car_detail", None)
            ret.pop("flight_detail", None)
        return ret
