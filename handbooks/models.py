# cities/models.py
from django.db import models
from cities.models import City  # Liên kết với model City
from accounts.models import CustomUser
import math


# Model cẩm nang
class Handbook(models.Model):
    CATEGORY_CHOICES = [
        ("cuisine", "Cuisine"),
        ("activity", "Activity"),
        ("day_trip", "Day Trip"),
        ("night_life", "Night Life"),
        ("scenic_spots", "Scenic Spots"),
        ("trip", "Trip"),
        ("best_hotel", "Best Hotel"),
        ("shopping", "Shopping"),
        ("holidays_and_events", "Holidays And Events"),
        ("accommodation", "Accommodation"),
        ("airport", "Airport"),
        ("travel_information", "Travel Information"),
    ]
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="handbooks",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="cities")
    short_description = models.TextField(
        blank=True, null=True
    )  # Trường description mới
    description = models.TextField(blank=True, null=True)  # Trường description mới
    image = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(
        max_length=255, choices=CATEGORY_CHOICES, default="cuisine"
    )

    avg_star = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)

    # ✅ Thêm các trường thống kê hành vi
    total_click = models.PositiveIntegerField(default=0)
    total_positive = models.PositiveIntegerField(default=0)
    total_negative = models.PositiveIntegerField(default=0)
    total_neutral = models.PositiveIntegerField(default=0)
    total_weighted_score = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}, {self.city.name}"

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


class UserHandbookInteraction(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="user_handbook_interactions"
    )
    handbook = models.ForeignKey(
        Handbook, on_delete=models.CASCADE, related_name="user_handbook_interactions"
    )

    click_count = models.PositiveIntegerField(default=0)
    positive_count = models.PositiveIntegerField(default=0)
    negative_count = models.PositiveIntegerField(default=0)
    neutral_count = models.PositiveIntegerField(default=0)
    weighted_score = models.FloatField(default=0.0)
    last_interacted = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "handbook")

    def __str__(self):
        return f"{self.user.username} ↔ {self.handbook.title}"

    def update_weighted_score(self):
        """
        Cập nhật điểm weighted_score cá nhân của user cho handbook
        """
        total = self.positive_count + self.negative_count + self.neutral_count
        sentiment = (self.positive_count - self.negative_count) / (total + 1)
        click_factor = math.log(1 + self.click_count)
        w1, w2 = 0.7, 0.3  # trọng số có thể tinh chỉnh
        self.weighted_score = w1 * sentiment + w2 * click_factor
        self.save(update_fields=["weighted_score"])
