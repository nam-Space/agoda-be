from rest_framework import serializers
from .models import Flight, FlightBookingDetail
from airports.serializers import AirportSerializer
from airports.models import Airport
from datetime import datetime


class FlightSerializer(serializers.ModelSerializer):
    origin = serializers.PrimaryKeyRelatedField(queryset=Airport.objects.all())
    destination = serializers.PrimaryKeyRelatedField(queryset=Airport.objects.all())
    origin_name = serializers.CharField(source='origin.name', read_only=True)
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    origin_city = serializers.CharField(source='origin.city.name', read_only=True)
    destination_city = serializers.CharField(source='destination.city.name', read_only=True)
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Flight
        fields = ["id", "flight_number", "airline", "origin", "destination",
                  "origin_name", "destination_name", "origin_city", "destination_city",
                  "departure_datetime", "arrival_datetime", "price", "seat_capacity",
                  "duration_minutes"]
    
    def get_duration_minutes(self, obj):
        if obj.departure_datetime and obj.arrival_datetime:
            delta = obj.arrival_datetime - obj.departure_datetime
            return int(delta.total_seconds() / 60)
        return 0


class FlightDetailSerializer(serializers.ModelSerializer):
    origin = AirportSerializer(read_only=True)
    destination = AirportSerializer(read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Flight
        fields = ["id", "flight_number", "airline", "origin", "destination",
                  "departure_datetime", "arrival_datetime", "price", "seat_capacity",
                  "duration_minutes", "duration_formatted"]
    
    def get_duration_minutes(self, obj):
        if obj.departure_datetime and obj.arrival_datetime:
            delta = obj.arrival_datetime - obj.departure_datetime
            return int(delta.total_seconds() / 60)
        return 0
    
    def get_duration_formatted(self, obj):
        minutes = self.get_duration_minutes(obj)
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"


# 👇 Dùng khi hiển thị trong Booking detail
class FlightBookingDetailSerializer(serializers.ModelSerializer):
    flight = FlightSerializer(read_only=True)
    flight_id = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.all(), source='flight', write_only=True
    )
    
    class Meta:
        model = FlightBookingDetail
        fields = [
            "id",
            "booking",
            "flight",
            "flight_id",
            "seat_class",
            "num_passengers",
        ]
        read_only_fields = ['id', 'booking']

