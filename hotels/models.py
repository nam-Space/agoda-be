from django.db import models
from cities.models import City
from django.db.models import Avg
import math

from django.utils import timezone


class Hotel(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="hotels", null=True
    )
    owner = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        related_name="hotels",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    nearbyLocation = models.TextField(blank=True, null=True)
    mostFeature = models.TextField(blank=True, null=True)
    facilities = models.TextField(blank=True, null=True)
    withUs = models.TextField(blank=True, null=True)
    usefulInformation = models.TextField(blank=True, null=True)
    amenitiesAndFacilities = models.TextField(blank=True, null=True)
    locationInfo = models.TextField(null=True, blank=True)
    regulation = models.TextField(blank=True)
    avg_star = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    min_price = models.FloatField(default=0.0)
    best_comment = models.TextField(blank=True, null=True)

    # ✅ Thêm các trường thống kê hành vi
    total_click = models.PositiveIntegerField(default=0)
    total_positive = models.PositiveIntegerField(default=0)
    total_negative = models.PositiveIntegerField(default=0)
    total_neutral = models.PositiveIntegerField(default=0)
    total_weighted_score = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # ✅ Hàm tự cập nhật giá trung bình của các phòng còn available
    def update_min_price(self):
        from rooms.models import Room

        avg_price = (
            Room.objects.filter(hotel=self, available=True)
            .aggregate(avg_price=models.Avg("price_per_night"))
            .get("avg_price")
        )
        self.min_price = avg_price or 0
        self.save(update_fields=["min_price"])

    # ✅ Tính sentiment score (từ review)
    @property
    def sentiment_score(self):
        total = self.total_positive + self.total_negative + self.total_neutral
        return (self.total_positive - self.total_negative) / (total + 1)

    # ✅ Click score (độ phổ biến)
    @property
    def click_score(self):
        return math.log(1 + self.total_click)

    # ✅ Weighted score — dùng để sắp xếp, đề xuất
    @property
    def calc_total_weighted_score(self):
        """Tính toán điểm total_weighted_score (không lưu DB)"""
        w1, w2, w3 = 0.6, 0.3, 0.1
        return w1 * self.avg_star + w2 * self.click_score + w3 * self.sentiment_score

    def update_total_weighted_score(self):
        """Cập nhật và lưu total_weighted_score xuống DB"""
        self.total_weighted_score = self.calc_total_weighted_score
        self.save(update_fields=["total_weighted_score"])

    def save(self, *args, **kwargs):
        try:
            self.total_weighted_score = self.calc_total_weighted_score
        except Exception:
            self.total_weighted_score = 0.0
        super().save(*args, **kwargs)


# Model để lưu thông tin về hình ảnh khách sạn
class HotelImage(models.Model):
    hotel = models.ForeignKey("Hotel", related_name="images", on_delete=models.CASCADE)
    image = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.hotel.name}"


class UserHotelInteraction(models.Model):
    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="user_hotel_interactions",
    )
    hotel = models.ForeignKey(
        Hotel, on_delete=models.CASCADE, related_name="user_hotel_interactions"
    )

    click_count = models.PositiveIntegerField(default=0)
    positive_count = models.PositiveIntegerField(default=0)
    negative_count = models.PositiveIntegerField(default=0)
    neutral_count = models.PositiveIntegerField(default=0)
    weighted_score = models.FloatField(default=0.0)
    last_interacted = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "hotel")

    def __str__(self):
        return f"{self.user.username} ↔ {self.hotel.name}"

    def update_weighted_score(self):
        """
        Cập nhật điểm weighted_score cá nhân của user cho hotel
        """
        total = self.positive_count + self.negative_count + self.neutral_count
        sentiment = (self.positive_count - self.negative_count) / (total + 1)
        click_factor = math.log(1 + self.click_count)
        w1, w2 = 0.7, 0.3  # trọng số có thể tinh chỉnh
        self.weighted_score = w1 * sentiment + w2 * click_factor
        self.save(update_fields=["weighted_score"])
