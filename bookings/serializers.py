# bookings/serializers.py
from rest_framework import serializers
from .models import Booking, GuestInfo, RefundPolicy
from rooms.serializers import (
    RoomBookingDetailSerializer,
    RoomBookingDetailCreateSerializer,
)
from cars.serializers import (
    CarBookingDetailSerializer,
    CarBookingDetailCreateSerializer,
)
from flights.serializers import (
    FlightBookingDetailSerializer,
    FlightBookingDetailCreateSerializer,
)
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
    service_ref_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_null=True)
    guest_info = GuestInfoSerializer(required=False)
    user = UserSerializer(read_only=True)

    room_details = serializers.SerializerMethodField()
    car_detail = serializers.SerializerMethodField()
    activity_date_detail = serializers.SerializerMethodField()
    flight_detail = serializers.SerializerMethodField()


    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "booking_code",
            "service_type",
            "service_ref_ids",
            "total_price",
            "discount_amount",
            "final_price",
            "refund_amount",
            "status",
            "payment_status",
            "created_at",
            "guest_info",
            "room_details",
            "car_detail",
            "flight_detail",
            "activity_date_detail",
        ]
        read_only_fields = ["id", "status", "payment_status", "created_at"]


    def get_room_details(self, obj):
        if obj.service_type != ServiceType.HOTEL or not obj.service_ref_ids:
            return None
        room_booking_details = RoomBookingDetail.objects.filter(id__in=obj.service_ref_ids)
        return RoomBookingDetailSerializer(room_booking_details, many=True, context=self.context).data

    def get_car_detail(self, obj):
        if obj.service_type != ServiceType.CAR or not obj.service_ref_ids:
            return None
        car_booking_details = CarBookingDetail.objects.filter(id__in=obj.service_ref_ids)
        return CarBookingDetailSerializer(car_booking_details, many=True, context=self.context).data

    def get_flight_detail(self, obj):
        if obj.service_type != ServiceType.FLIGHT or not obj.service_ref_ids:
            return None
        flight_booking_details = obj.flight_details.all()
        return FlightBookingDetailSerializer(flight_booking_details, many=True, context=self.context).data

    def get_activity_date_detail(self, obj):
        if obj.service_type != ServiceType.ACTIVITY or not obj.service_ref_ids:
            return None
        activity_date_booking_details = ActivityDateBookingDetail.objects.filter(id__in=obj.service_ref_ids)
        return ActivityDateBookingDetailSerializer(activity_date_booking_details, many=True, context=self.context).data

    def create(self, validated_data):
        guest_data = validated_data.pop("guest_info", None)
        request = self.context.get("request", None)
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user

        booking = Booking.objects.create(**validated_data)
        if guest_data:
            GuestInfo.objects.create(booking=booking, **guest_data)
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
        service_type = instance.service_type
        if service_type == ServiceType.HOTEL:
            ret.pop("car_detail", None)
            ret.pop("flight_detail", None)
            ret.pop("activity_date_detail", None)
        elif service_type == ServiceType.CAR:
            ret.pop("room_details", None)
            ret.pop("flight_detail", None)
            ret.pop("activity_date_detail", None)
        elif service_type == ServiceType.FLIGHT:
            ret.pop("room_details", None)
            ret.pop("car_detail", None)
            ret.pop("activity_date_detail", None)
        elif service_type == ServiceType.ACTIVITY:
            ret.pop("room_details", None)
            ret.pop("car_detail", None)
            ret.pop("flight_detail", None)
        return ret


class RefundPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundPolicy
        fields = [
            "id",
            "service_type",
            "name",
            "description",
            "policy_type",
            "refund_percentage",
            "refund_amount",
            "hours_before_start",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
