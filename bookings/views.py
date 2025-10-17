# bookings/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Booking
from .serializers import BookingSerializer
from django.db.models import Q
from rooms.serializers import RoomBookingDetailSerializer
from cars.serializers import CarBookingDetailSerializer
from flights.serializers import FlightBookingDetailSerializer
from activities.serializers import ActivityDateBookingDetailSerializer
from .constants.service_type import ServiceType
from rooms.models import RoomBookingDetail
from cars.models import CarBookingDetail
from flights.models import FlightBookingDetail
from activities.models import ActivityDateBookingDetail


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [AllowAny]

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

            detail = RoomBookingDetail.objects.filter(booking=booking).first()
            if detail:
                data = RoomBookingDetailSerializer(detail).data

        elif service_type == ServiceType.CAR:

            detail = CarBookingDetail.objects.filter(booking=booking).first()
            if detail:
                data = CarBookingDetailSerializer(detail).data

        elif service_type == ServiceType.FLIGHT:

            detail = FlightBookingDetail.objects.filter(booking=booking).first()
            if detail:
                data = FlightBookingDetailSerializer(detail).data

        elif service_type == ServiceType.ACTIVITY:

            detail = ActivityDateBookingDetail.objects.filter(booking=booking).first()
            if detail:
                data = ActivityDateBookingDetailSerializer(detail).data
                # ✅ Cập nhật service_ref_id = ID của activity detail
                booking.service_ref_id = detail.id
                booking.save(update_fields=["service_ref_id"])

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
