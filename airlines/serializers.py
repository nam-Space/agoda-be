from rest_framework import serializers
from .models import Airline, Aircraft
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


class AirlineSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airline
        fields = [
            "id",
            "name",
            "code",
            "logo",
            "description",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class AirlineSerializer(serializers.ModelSerializer):
    flight_operations_staff = UserSerializer(read_only=True)

    class Meta:
        model = Airline
        fields = [
            "id",
            "name",
            "code",
            "logo",
            "description",
            "created_at",
            "flight_operations_staff",
        ]
        read_only_fields = ["created_at"]


class AirlineCreateSerializer(serializers.ModelSerializer):
    flight_operations_staff = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all()
    )

    class Meta:
        model = Airline
        fields = [
            "id",
            "name",
            "code",
            "logo",
            "description",
            "created_at",
            "flight_operations_staff",
        ]
        read_only_fields = ["created_at"]


class AircraftSerializer(serializers.ModelSerializer):
    airline = AirlineSerializer(read_only=True)
    airline_id = serializers.PrimaryKeyRelatedField(
        queryset=Airline.objects.all(), source="airline", write_only=True
    )

    class Meta:
        model = Aircraft
        fields = [
            "id",
            "airline",
            "airline_id",
            "model",
            "registration_number",
            "total_seats",
            "economy_seats",
            "business_seats",
            "first_class_seats",
            "is_active",
            "manufacture_year",
            "created_at",
        ]
        read_only_fields = ["created_at"]
