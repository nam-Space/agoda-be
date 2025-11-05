from django.db import models
from accounts.models import CustomUser
from bookings.models import Booking


class Car(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="cars",
        null=True,
        blank=True,
    )  # tài xế
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    capacity = models.PositiveIntegerField()  # số chỗ ngồi
    luggage = models.PositiveIntegerField(null=True)  # số hành lý
    point = models.FloatField(default=0.0)  # có thể là toạ độ hoặc điểm số
    avg_star = models.DecimalField(
        max_digits=2, decimal_places=1, default=0.0
    )  # VD: 4.5 sao
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    avg_speed = models.FloatField(default=0.0)
    image = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"


class CarBookingDetail(models.Model):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="car_detail"
    )
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="cars_bookings")
    pickup_location = models.CharField(max_length=255, null=True, blank=True)
    dropoff_location = models.CharField(max_length=255, null=True, blank=True)
    lat1 = models.FloatField(null=True, blank=True)
    lng1 = models.FloatField(null=True, blank=True)
    lat2 = models.FloatField(null=True, blank=True)
    lng2 = models.FloatField(null=True, blank=True)
    pickup_datetime = models.DateTimeField()
    driver_required = models.BooleanField(default=True)
    distance_km = models.FloatField(default=0.0)
    total_time_estimate = models.FloatField(default=0.0)
    passenger_quantity_booking = models.PositiveIntegerField(default=1)
    driver = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="cars_bookings",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        # ✅ Tự động gán chủ khách sạn khi tạo booking
        if self.car and not self.driver:
            self.driver = self.car.user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"CarBooking for {self.booking.booking_code}"
