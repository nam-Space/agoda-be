from django.db import models
from accounts.models import CustomUser
from bookings.models import Booking
from cars.constants.car_booking_status import CarBookingStatus


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

    def get_active_promotion(self):
        from django.utils import timezone

        now = timezone.now()
        car_promotions = self.promotions.select_related("promotion").all()

        # Chỉ lấy những promotion đang active
        active_promos = [
            cp
            for cp in car_promotions
            if cp.promotion.is_active
            and cp.promotion.start_date <= now <= cp.promotion.end_date
        ]

        if not active_promos:
            return None

        # Lấy promotion có discount lớn nhất
        best_promo = max(
            active_promos,
            key=lambda cp: (
                cp.discount_percent
                if cp.discount_percent is not None
                else (cp.promotion.discount_percent or 0)
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
    pickup_datetime = models.DateTimeField(null=True, blank=True)
    dropoff_datetime = models.DateTimeField(null=True, blank=True)
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
    status = models.CharField(
        max_length=20,
        choices=CarBookingStatus.choices,
        default=CarBookingStatus.STARTING,
    )

    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.FloatField(default=0.0)
    final_price = models.FloatField(default=0.0)

    def save(self, *args, **kwargs):
        # ✅ Tự động gán chủ khách sạn khi tạo booking
        if self.car and not self.driver:
            self.driver = self.car.user

        # =========================
        # 🎯 CẬP NHẬT DRIVER STATUS
        # =========================
        if self.driver:
            if self.status == CarBookingStatus.ARRIVED:
                self.driver.driver_status = "idle"
            else:
                self.driver.driver_status = "busy"

            # Chỉ update field cần thiết
            self.driver.save(update_fields=["driver_status"])

        # Tính toán giảm giá nếu có promotion (giả sử có hàm get_active_promotion ở car)
        if self.car and hasattr(self.car, "get_active_promotion"):
            promo = self.car.get_active_promotion()
            if promo:
                percent = float(promo.get("discount_percent") or 0)
                amount = float(promo.get("discount_amount") or 0)
                if amount > 0:
                    self.discount_amount = min(amount, float(self.total_price))
                elif percent > 0:
                    self.discount_amount = float(self.total_price) * percent / 100
                else:
                    self.discount_amount = 0
                self.final_price = float(self.total_price) - self.discount_amount
            else:
                self.discount_amount = 0
                self.final_price = float(self.total_price)
        else:
            self.discount_amount = 0
            self.final_price = float(self.total_price)
        super().save(*args, **kwargs)
        # Tổng hợp discount/final_price lên booking nếu có nhiều car detail (giả sử dùng service_ref_ids)
        if self.booking:
            details = [self]
            if (
                hasattr(self.booking, "service_ref_ids")
                and self.booking.service_ref_ids
            ):
                from .models import CarBookingDetail

                details = CarBookingDetail.objects.filter(
                    id__in=self.booking.service_ref_ids
                )
            self.booking.discount_amount = sum(
                getattr(d, "discount_amount", 0) for d in details
            )
            self.booking.final_price = sum(
                getattr(d, "final_price", 0) for d in details
            )
            self.booking.save(update_fields=["discount_amount", "final_price"])

    def __str__(self):
        return f"CarBooking for {self.booking.booking_code}"
