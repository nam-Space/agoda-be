from rest_framework import serializers
from .models import Flight, FlightBookingDetail
from airports.serializers import AirportSerializer
from airports.models import Airport


class FlightSerializer(serializers.ModelSerializer):
    origin = serializers.PrimaryKeyRelatedField(queryset=Airport.objects.all())
    destination = serializers.PrimaryKeyRelatedField(queryset=Airport.objects.all())

    class Meta:
        model = Flight
        fields = ["id", "flight_number", "airline", "origin", "destination",
                  "departure_datetime", "arrival_datetime", "price", "seat_capacity"]


# 👇 Dùng khi hiển thị trong Booking detail
class FlightBookingDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlightBookingDetail
        fields = [
            "flight",
            "seat_class",
            "num_passengers",
        ]

