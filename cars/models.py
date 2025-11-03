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
    total_booking_count = models.PositiveIntegerField(default=0)
    total_weighted_score = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    # ✅ Weighted score — dùng để sắp xếp, đề xuất
    @property
    def calc_total_weighted_score(self):
        """Tính toán điểm total_weighted_score (không lưu DB)"""
        w1 = 1.0
        return w1 * self.total_booking_count

    def update_total_weighted_score(self):
        """Cập nhật và lưu total_weighted_score xuống DB"""
        self.total_weighted_score = self.calc_total_weighted_score
        self.save(update_fields=["total_weighted_score"])


class UserCarInteraction(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="user_car_interactions"
    )
    car = models.ForeignKey(
        Car, on_delete=models.CASCADE, related_name="user_car_interactions"
    )

    booking_count = models.PositiveIntegerField(default=0)
    weighted_score = models.FloatField(default=0.0)
    last_interacted = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "car")

    def __str__(self):
        return f"{self.user.username} ↔ {self.car.name}"

    def update_weighted_score(self):
        """
        Cập nhật điểm weighted_score cá nhân của user cho car
        """
        w1 = 1  # trọng số có thể tinh chỉnh
        self.weighted_score = w1 * self.booking_count
        self.save(update_fields=["weighted_score"])


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
