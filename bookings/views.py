# bookings/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Booking
from .serializers import BookingSerializer
from django.db.models import Q
from rooms.serializers import (
    RoomBookingDetailSerializer,
    RoomBookingDetailCreateSerializer,
)
from cars.serializers import (
    CarBookingDetailSerializer,
    CarBookingDetailCreateSerializer,
)
from flights.serializers import FlightBookingDetailSerializer
from activities.serializers import (
    ActivityDateBookingDetailSerializer,
    ActivityDateBookingCreateSerializer,
)
from .constants.service_type import ServiceType
from rooms.models import RoomBookingDetail
from cars.models import CarBookingDetail
from flights.models import FlightBookingDetail
from activities.models import ActivityDateBookingDetail
from rest_framework_simplejwt.authentication import JWTAuthentication


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def get_queryset(self):
        queryset = Booking.objects.all().order_by("-created_at")
        # Lọc theo email của user hoặc guest_info
        email = self.request.query_params.get("email")
        if email:
            queryset = queryset.filter(
                Q(user__email=email) | Q(guest_info__email=email)
            )
        # Lọc theo service_type
        service_type = self.request.query_params.get("service_type")
        if service_type:
            queryset = queryset.filter(service_type=service_type)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Sau khi tạo booking, kiểm tra service_type và lấy detail tương ứng
        service_type = booking.service_type
        data = None

        # Tìm lại detail trực tiếp trong DB
        if service_type == ServiceType.HOTEL:
            room_data = request.data.get("hotel_detail")
            if room_data:
                room_serializer = RoomBookingDetailCreateSerializer(data=room_data)
                room_serializer.is_valid(raise_exception=True)
                detail = room_serializer.save(booking=booking)
                booking.service_ref_id = detail.id
                booking.save(update_fields=["service_ref_id"])
                data = RoomBookingDetailSerializer(detail).data

        elif service_type == ServiceType.CAR:
            car_data = request.data.get("car_detail")
            if car_data:
                car_serializer = CarBookingDetailCreateSerializer(data=car_data)
                car_serializer.is_valid(raise_exception=True)
                detail = car_serializer.save(booking=booking)
                booking.service_ref_id = detail.id
                booking.save(update_fields=["service_ref_id"])
                data = CarBookingDetailSerializer(detail).data

        elif service_type == ServiceType.FLIGHT:
            flight_data = request.data.get("flight_detail")
            if flight_data:
                flight_serializer = FlightBookingDetailSerializer(data=flight_data)
                flight_serializer.is_valid(raise_exception=True)
                detail = flight_serializer.save(booking=booking)
                booking.service_ref_id = detail.id
                booking.save(update_fields=["service_ref_id"])
                data = FlightBookingDetailSerializer(detail).data

        elif service_type == ServiceType.ACTIVITY:
            activity_date_data = request.data.get("activity_date_detail")
            if activity_date_data:
                activity_date_serializer = ActivityDateBookingCreateSerializer(
                    data=activity_date_data
                )
                activity_date_serializer.is_valid(raise_exception=True)
                detail = activity_date_serializer.save(booking=booking)
                booking.service_ref_id = detail.id
                booking.save(update_fields=["service_ref_id"])
                data = ActivityDateBookingDetailSerializer(detail).data

        return Response(
            {
                "isSuccess": True,
                "message": "Booking created successfully",
                "booking_id": booking.id,
                "booking_code": booking.booking_code,
                "data": data,
            },
            status=status.HTTP_201_CREATED,
        )
