# payments/serializers.py
from rest_framework import serializers
from .models import Payment
from bookings.serializers import BookingSerializer
from bookings.models import Booking


class PaymentSerializer(serializers.ModelSerializer):
    booking = BookingSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"


class PaymentCreateSerializer(serializers.ModelSerializer):
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())

    class Meta:
        model = Payment
        fields = "__all__"
