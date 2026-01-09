from rest_framework import serializers
from django.utils import timezone
from .models import Flight, FlightLeg, FlightBookingDetail, SeatClassPricing
from airports.models import Airport
from airports.serializers import AirportSerializer
from airlines.models import Airline, Aircraft
from airlines.serializers import AirlineSerializer, AircraftSerializer


class FlightLegSerializer(serializers.ModelSerializer):
    # READ
    departure_airport = AirportSerializer(read_only=True)
    arrival_airport = AirportSerializer(read_only=True)

    # WRITE
    departure_airport_id = serializers.PrimaryKeyRelatedField(
        queryset=Airport.objects.all(), source="departure_airport", write_only=True
    )
    arrival_airport_id = serializers.PrimaryKeyRelatedField(
        queryset=Airport.objects.all(), source="arrival_airport", write_only=True
    )

    # flight_id dùng khi tạo riêng leg (không cần khi nested create)
    flight_id = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.all(), source="flight", write_only=True, required=False
    )

    duration_minutes = serializers.IntegerField(required=False)

    class Meta:
        model = FlightLeg
        fields = [
            "id",
            # link flight
            "flight_id",
            # thời gian
            "departure_time",
            "arrival_time",
            # sân bay
            "departure_airport",
            "departure_airport_id",
            "arrival_airport",
            "arrival_airport_id",
            # thông tin chuyến bay
            "flight_code",
            # auto-calculated
            "duration_minutes",
        ]


class SeatClassPricingSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField(read_only=True)
    flight_id = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.all(), source="flight", write_only=True, required=False
    )

    class Meta:
        model = SeatClassPricing
        fields = [
            "id",
            "flight_id",
            "seat_class",
            "multiplier",
            "capacity",
            "available_seats",
            "has_meal",
            "has_free_drink",
            "has_lounge_access",
            "has_power_outlet",
            "has_priority_boarding",
            "price",
        ]

    def get_price(self, obj):
        return obj.price()


class FlightSimpleSerializer(serializers.ModelSerializer):
    airline = AirlineSerializer(read_only=True)

    # Computed fields
    departure_time = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    departure_airport = serializers.SerializerMethodField()
    arrival_airport = serializers.SerializerMethodField()

    class Meta:
        model = Flight
        fields = [
            "id",
            "airline",
            "total_duration",
            "baggage_included",
            "stops",
            "base_price",
            "departure_time",
            "arrival_time",
            "departure_airport",
            "arrival_airport",
        ]

    def get_departure_time(self, obj):
        first_leg = obj.legs.order_by("departure_time").first()
        return first_leg.departure_time if first_leg else None

    def get_arrival_time(self, obj):
        last_leg = obj.legs.order_by("arrival_time").last()
        return last_leg.arrival_time if last_leg else None

    def get_departure_airport(self, obj):
        leg = obj.legs.order_by("departure_time").first()
        return AirportSerializer(leg.departure_airport).data if leg else None

    def get_arrival_airport(self, obj):
        leg = obj.legs.order_by("arrival_time").last()
        return AirportSerializer(leg.arrival_airport).data if leg else None


class FlightGetListSerializer(serializers.ModelSerializer):
    airline = AirlineSerializer(read_only=True)
    aircraft = AircraftSerializer(read_only=True)

    seat_classes = SeatClassPricingSerializer(many=True, read_only=True)
    legs = FlightLegSerializer(many=True, read_only=True)

    # Promotion
    promotion = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()

    class Meta:
        model = Flight
        fields = "__all__"

    def get_promotion(self, obj):
        return obj.get_active_promotion()

    def get_has_promotion(self, obj):
        return obj.get_active_promotion() is not None


class FlightLegGetListSerializer(serializers.ModelSerializer):
    flight = FlightGetListSerializer(read_only=True)
    departure_airport = AirportSerializer(read_only=True)
    arrival_airport = AirportSerializer(read_only=True)

    class Meta:
        model = FlightLeg
        fields = "__all__"


class SeatClassPricingGetListSerializer(serializers.ModelSerializer):
    flight = FlightGetListSerializer(read_only=True)

    class Meta:
        model = SeatClassPricing
        fields = "__all__"


class FlightSerializer(serializers.ModelSerializer):
    airline = AirlineSerializer(read_only=True)
    airline_id = serializers.PrimaryKeyRelatedField(
        queryset=Airline.objects.all(), source="airline", write_only=True
    )

    aircraft = AircraftSerializer(read_only=True)
    aircraft_id = serializers.PrimaryKeyRelatedField(
        queryset=Aircraft.objects.all(),
        source="aircraft",
        write_only=True,
        required=False,
        allow_null=True,
    )

    # READ
    seat_classes = SeatClassPricingSerializer(many=True, read_only=True)
    legs = FlightLegSerializer(many=True, read_only=True)

    # WRITE: tạo legs và seat_classes lúc tạo flight
    legs_data = FlightLegSerializer(many=True, write_only=True, required=False)
    seat_classes_data = SeatClassPricingSerializer(
        many=True, write_only=True, required=False
    )

    # Promotion
    promotion = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()

    # Computed fields
    departure_time = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    departure_airport = serializers.SerializerMethodField()
    arrival_airport = serializers.SerializerMethodField()

    class Meta:
        model = Flight
        fields = [
            "id",
            "airline",
            "airline_id",
            "aircraft",
            "aircraft_id",
            "total_duration",
            "baggage_included",
            "stops",
            "base_price",
            # legs
            "legs",
            "legs_data",
            # seat classes
            "seat_classes",
            "seat_classes_data",
            # promotion
            "promotion",
            "has_promotion",
            # computed
            "departure_time",
            "arrival_time",
            "departure_airport",
            "arrival_airport",
        ]

    # ───────────────────────────────────────────
    # CREATE FLIGHT + LEGS + SEAT CLASSES
    # ───────────────────────────────────────────
    def create(self, validated_data):
        legs_data = validated_data.pop("legs_data", [])
        seat_classes_data = validated_data.pop("seat_classes_data", [])

        # 1. Tạo flight
        flight = Flight.objects.create(**validated_data)

        # 2. Tạo từng FlightLeg
        for leg in legs_data:
            FlightLeg.objects.create(flight=flight, **leg)

        # 3. Tạo từng SeatClassPricing
        for seat_class in seat_classes_data:
            SeatClassPricing.objects.create(flight=flight, **seat_class)

        # 4. Tính toán lại total_duration, stops
        flight.calculate_values()

        return flight

    # ───────────────────────────────────────────
    # HELPER FIELDS
    # ───────────────────────────────────────────
    def get_departure_time(self, obj):
        first_leg = obj.legs.order_by("departure_time").first()
        return first_leg.departure_time if first_leg else None

    def get_arrival_time(self, obj):
        last_leg = obj.legs.order_by("arrival_time").last()
        return last_leg.arrival_time if last_leg else None

    def get_departure_airport(self, obj):
        leg = obj.legs.order_by("departure_time").first()
        return AirportSerializer(leg.departure_airport).data if leg else None

    def get_arrival_airport(self, obj):
        leg = obj.legs.order_by("arrival_time").last()
        return AirportSerializer(leg.arrival_airport).data if leg else None

    def get_promotion(self, obj):
        return obj.get_active_promotion()

    def get_has_promotion(self, obj):
        return obj.get_active_promotion() is not None


# Serializer dùng cho tạo mới (write) FlightBookingDetail
class FlightBookingDetailCreateSerializer(serializers.ModelSerializer):
    flight = serializers.PrimaryKeyRelatedField(queryset=Flight.objects.all())

    class Meta:
        model = FlightBookingDetail
        fields = [
            "flight",
            "seat_class",
            "num_passengers",
            "total_price",
        ]

    def validate(self, data):
        flight = data.get("flight")
        seat_class = data.get("seat_class")
        num_passengers = data.get("num_passengers")

        # Validate seat_class exists
        seat_class_pricing = flight.seat_classes.filter(seat_class=seat_class).first()
        if not seat_class_pricing:
            raise serializers.ValidationError(
                f"Seat class '{seat_class}' not available for this flight"
            )

        # Validate availability
        if num_passengers > seat_class_pricing.available_seats:
            raise serializers.ValidationError(
                f"Only {seat_class_pricing.available_seats} seats available in {seat_class}"
            )

        # Validate departure_time > now (từ flight.legs)
        first_leg = flight.legs.order_by("departure_time").first()
        if first_leg and first_leg.departure_time < timezone.now():
            raise serializers.ValidationError("Flight departure time is in the past")

        return data


# 👇 Dùng khi hiển thị trong Booking detail
class FlightBookingDetailSerializer(serializers.ModelSerializer):
    flight = FlightSerializer(read_only=True)

    class Meta:
        model = FlightBookingDetail
        fields = [
            "id",
            "flight",
            "seat_class",
            "num_passengers",
            "total_price",
            "discount_amount",
            "final_price",
        ]
