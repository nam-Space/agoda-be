# bookings/serializers.py
from rest_framework import serializers
from .models import Booking, GuestInfo
from rooms.serializers import RoomBookingDetailSerializer
from cars.serializers import CarBookingDetailSerializer
from flights.serializers import FlightBookingDetailSerializer
from rooms.models import RoomBookingDetail
from cars.models import CarBookingDetail
from flights.models import FlightBookingDetail
from .constants.service_type import ServiceType

class GuestInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestInfo
        fields = ['full_name', 'email', 'phone', 'country', 'special_request']

class BookingSerializer(serializers.ModelSerializer):
    guest_info = GuestInfoSerializer(required=False)
    hotel_detail = RoomBookingDetailSerializer(required=False)  
    car_detail = CarBookingDetailSerializer(required=False)
    flight_detail = FlightBookingDetailSerializer(required=False)

    class Meta:
        model = Booking
        fields = ['id', 'booking_code', 'service_type', 'service_ref_id', 'total_price',
                  'status', 'payment_status', 'created_at', 'guest_info', 
                  'hotel_detail', 'car_detail', 'flight_detail']
        read_only_fields = ['id', 'status', 'payment_status', 'created_at']

    def create(self, validated_data):
        guest_data = validated_data.pop('guest_info', None)
        hotel_data = validated_data.pop('hotel_detail', None)
        car_data = validated_data.pop('car_detail', None)
        flight_data = validated_data.pop('flight_detail', None)

        booking = Booking.objects.create(**validated_data)
        if guest_data:
            GuestInfo.objects.create(booking=booking, **guest_data)

        service_type = booking.service_type
        if service_type == ServiceType.HOTEL and hotel_data:
            RoomBookingDetail.objects.create(booking=booking, **hotel_data)
        elif service_type == ServiceType.CAR and car_data:
            CarBookingDetail.objects.create(booking=booking, **car_data)
        elif service_type == ServiceType.FLIGHT and flight_data:
            FlightBookingDetail.objects.create(booking=booking, **flight_data)


        return booking
    
    def update(self, instance, validated_data):
        # Lấy dữ liệu guest_info nếu có
        guest_info_data = validated_data.pop('guest_info', None)

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
            ret.pop('car_detail', None)
            ret.pop('flight_detail', None)
        elif service_type == ServiceType.CAR:
            ret.pop('hotel_detail', None)
            ret.pop('flight_detail', None)
        elif service_type == ServiceType.FLIGHT:
            ret.pop('hotel_detail', None)
            ret.pop('car_detail', None)
        return ret