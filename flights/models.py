from django.db import models
from django.utils import timezone

from bookings.models import Booking
from airports.models import Airport
from airlines.models import Airline, Aircraft


class Flight(models.Model):
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE)
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flights",
    )
    total_duration = models.IntegerField(default=0, help_text="Tổng thời gian (phút)")
    baggage_included = models.BooleanField(default=False)

    # số điểm dừng = số legs - 1
    stops = models.IntegerField(default=0)
    base_price = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Flight #{self.id} - {self.airline.name}"

    # Gợi ý: tự tính stops & total_duration
    def calculate_values(self):
        legs = self.legs.all().order_by("departure_time")
        if legs.exists():
            self.stops = legs.count() - 1
            first = legs.first().departure_time
            last = legs.last().arrival_time
            self.total_duration = int((last - first).total_seconds() // 60)
        self.save()

    def get_active_promotion(self):
        now = timezone.now()
        flight_promotions = self.promotions.select_related("promotion").all()

        # Chỉ lấy những promotion đang active
        active_promos = [
            fp
            for fp in flight_promotions
            if fp.promotion.is_active
            and fp.promotion.start_date <= now <= fp.promotion.end_date
        ]

        if not active_promos:
            return None

        # Lấy promotion có discount lớn nhất
        best_promo = max(
            active_promos,
            key=lambda fp: (
                fp.discount_percent
                if fp.discount_percent is not None
                else (fp.promotion.discount_percent or 0)
            ),
        )

        promo = best_promo.promotion
        return {
            "id": promo.id,
            "title": promo.title,
            "discount_percent": best_promo.discount_percent or promo.discount_percent,
            "discount_amount": best_promo.discount_amount or promo.discount_amount,
            "start_date": promo.start_date,
            "end_date": promo.end_date,
        }


class FlightLeg(models.Model):
    flight = models.ForeignKey(Flight, related_name="legs", on_delete=models.CASCADE)

    # thời gian
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    # sân bay
    departure_airport = models.ForeignKey(
        Airport, related_name="departures", on_delete=models.CASCADE
    )
    arrival_airport = models.ForeignKey(
        Airport, related_name="arrivals", on_delete=models.CASCADE
    )

    # mã chuyến bay
    flight_code = models.CharField(max_length=20)  # PG 101

    duration_minutes = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.flight_code} ({self.departure_airport.code} → {self.arrival_airport.code})"

    # Gợi ý: tự tính duration
    def save(self, *args, **kwargs):
        if not self.duration_minutes:
            dep = self.departure_time
            arr = self.arrival_time

            # đảm bảo tính theo UTC tránh DST
            delta = (arr - dep).total_seconds()
            self.duration_minutes = int(delta // 60)
        super().save(*args, **kwargs)
        self.flight.calculate_values()

    def delete(self, *args, **kwargs):
        flight = self.flight  # backup
        super().delete(*args, **kwargs)
        flight.calculate_values()


class SeatClassPricing(models.Model):
    FLIGHT_CLASSES = [
        ("economy", "Economy"),
        ("business", "Business"),
        ("first", "First Class"),
    ]

    flight = models.ForeignKey(
        Flight, on_delete=models.CASCADE, related_name="seat_classes"
    )
    seat_class = models.CharField(max_length=20, choices=FLIGHT_CLASSES)
    multiplier = models.FloatField(default=1.0)
    capacity = models.PositiveIntegerField(default=0)
    available_seats = models.PositiveIntegerField(default=0)

    has_meal = models.BooleanField(default=False)
    has_free_drink = models.BooleanField(default=False)
    has_lounge_access = models.BooleanField(default=False)
    has_power_outlet = models.BooleanField(default=False)
    has_priority_boarding = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.flight} - {self.seat_class} (x{self.multiplier})"

    def price(self):
        return float(self.flight.base_price) * self.multiplier

    @property
    def seats_sold(self):
        return self.capacity - self.available_seats


class FlightSeat(models.Model):
    """
    Ghế cụ thể trên một chuyến bay + hạng ghế.
    Ví dụ: 12A (economy), 2C (business).
    """

    flight = models.ForeignKey(
        Flight, on_delete=models.CASCADE, related_name="seats"
    )
    seat_class = models.CharField(
        max_length=20, choices=SeatClassPricing.FLIGHT_CLASSES, default="economy"
    )
    seat_number = models.CharField(max_length=10)  # VD: 12A, 1C

    is_available = models.BooleanField(
        default=True,
        help_text="Ghế còn trống để book hay đã được giữ chỗ / sử dụng",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("flight", "seat_number")

    def __str__(self):
        return f"{self.flight} - {self.seat_number} ({self.seat_class})"


class FlightBookingDetail(models.Model):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="flight_details"
    )
    flight = models.ForeignKey(
        "flights.Flight",
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )
    seat_class = models.CharField(
        max_length=20, choices=SeatClassPricing.FLIGHT_CLASSES, default="economy"
    )
    num_passengers = models.IntegerField()
    total_price = models.FloatField(default=0.0)
    discount_amount = models.FloatField(default=0.0)
    final_price = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    # Danh sách ghế cụ thể đã gán cho booking này
    seats = models.ManyToManyField(
        FlightSeat,
        related_name="flight_bookings",
        blank=True,
        help_text="Các ghế cụ thể (12A, 12B, ...) đã được gán cho booking",
    )

    def save(self, *args, **kwargs):
        # Tính toán giảm giá nếu có promotion
        # Lấy giá từ SeatClassPricing theo seat_class
        seat_class_pricing = None
        if self.flight:
            seat_class_pricing = self.flight.seat_classes.filter(
                seat_class=self.seat_class
            ).first()
        if seat_class_pricing:
            self.total_price = seat_class_pricing.price() * self.num_passengers
        else:
            self.total_price = 0
        if self.flight and hasattr(self.flight, "get_active_promotion"):
            promo = self.flight.get_active_promotion()
            if promo:
                percent = float(promo.get("discount_percent") or 0)
                amount = float(promo.get("discount_amount") or 0)
                if percent > 0:
                    percent_discount = float(self.total_price) * percent / 100
                    if amount > 0:
                        self.discount_amount = min(percent_discount, amount)
                    else:
                        self.discount_amount = percent_discount
                elif amount > 0:
                    self.discount_amount = min(amount, float(self.total_price))
                else:
                    self.discount_amount = 0
                self.final_price = float(self.total_price) - self.discount_amount
            else:
                self.discount_amount = 0
                self.final_price = float(self.total_price)
        else:
            self.discount_amount = 0
            self.final_price = float(self.total_price)

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Khi booking mới được tạo, giảm available_seats của SeatClassPricing
        if is_new and seat_class_pricing and self.num_passengers > 0:
            seat_class_pricing.available_seats = max(
                0, seat_class_pricing.available_seats - self.num_passengers
            )
            seat_class_pricing.save(update_fields=["available_seats"])

        # Cập nhật tổng discount_amount và final_price cho booking (tránh lặp vô hạn)
        if self.booking_id:
            from django.db.models import Sum

            BookingModel = type(self.booking)
            BookingModel.objects.filter(pk=self.booking_id).update(
                discount_amount=self.booking.flight_details.aggregate(
                    total=Sum("discount_amount")
                )["total"]
                or 0,
                final_price=self.booking.flight_details.aggregate(
                    total=Sum("final_price")
                )["total"]
                or 0,
                total_price=self.booking.flight_details.aggregate(
                    total=Sum("total_price")
                )["total"]
                or 0,
            )

    def __str__(self):
        return f"FlightBooking {self.booking.booking_code} - Flight {self.flight_id}"
