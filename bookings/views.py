# bookings/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Booking
from .serializers import BookingSerializer
from django.db.models import Q

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Booking.objects.all().order_by('-created_at') 
        # Lọc theo email của user hoặc guest_info
        email = self.request.query_params.get('email')
        if email:
            queryset = queryset.filter(Q(user__email=email) | Q(guest_info__email=email))
        # Lọc theo service_type
        service_type = self.request.query_params.get('service_type')
        if service_type:
            queryset = queryset.filter(service_type=service_type)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response({
            "message": "Booking created successfully",
            "booking_id": booking.id,
            "booking_code": booking.booking_code
        }, status=status.HTTP_201_CREATED)
