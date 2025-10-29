# activities/models.py
from django.db import models
from cities.models import City  # Liên kết với model Country
from bookings.models import Booking
from accounts.models import CustomUser
import math


# Model hoạt động
class Activity(models.Model):
    event_organizer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="activities",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="activities")

    CATEGORY_CHOICES = [
        ("journey", "Journey"),
        ("moving", "Moving"),
        ("experience", "Experience"),
        ("food", "Food"),
        ("tourist_attractions", "Tourist_Attractions"),
        ("travel_preparation", "Travel_Preparation"),
    ]
    category = models.CharField(
        max_length=255, choices=CATEGORY_CHOICES, default="journey"
    )
    short_description = models.TextField(blank=True, null=True)
    more_information = models.TextField(blank=True, null=True)
    cancellation_policy = models.TextField(blank=True, null=True)
    departure_information = models.TextField(blank=True, null=True)
    avg_price = models.FloatField(default=0.0)
    avg_star = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    total_time = models.PositiveIntegerField()  # số giờ hoạt động

    # ✅ Thêm các trường hành vi
    total_click = models.PositiveIntegerField(default=0)
    total_positive = models.PositiveIntegerField(default=0)
    total_negative = models.PositiveIntegerField(default=0)
    total_neutral = models.PositiveIntegerField(default=0)
    total_weighted_score = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}, {self.city.name}"

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


# Model để lưu thông tin về hình ảnh hoạt động
class ActivityImage(models.Model):
    activity = models.ForeignKey(
        "Activity", related_name="images", on_delete=models.CASCADE
    )
    image = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.activity.name}"


class UserActivityInteraction(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="user_activity_interactions"
    )
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="user_activity_interactions"
    )

    click_count = models.PositiveIntegerField(default=0)
    positive_count = models.PositiveIntegerField(default=0)
    negative_count = models.PositiveIntegerField(default=0)
    neutral_count = models.PositiveIntegerField(default=0)
    weighted_score = models.FloatField(default=0.0)
    last_interacted = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "activity")

    def __str__(self):
        return f"{self.user.username} ↔ {self.activity.name}"

    def update_weighted_score(self):
        """
        Cập nhật điểm weighted_score cá nhân của user cho activity
        """
        total = self.positive_count + self.negative_count + self.neutral_count
        sentiment = (self.positive_count - self.negative_count) / (total + 1)
        click_factor = math.log(1 + self.click_count)
        w1, w2 = 0.7, 0.3  # trọng số có thể tinh chỉnh
        self.weighted_score = w1 * sentiment + w2 * click_factor
        self.save(update_fields=["weighted_score"])


# Model các gói hoạt động
class ActivityPackage(models.Model):
    activity = models.ForeignKey(
        "Activity", on_delete=models.CASCADE, related_name="activities_packages"
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}, {self.activity.name}"


# Model các gói hoạt động
class ActivityDate(models.Model):
    activity_package = models.ForeignKey(
        "ActivityPackage", on_delete=models.CASCADE, related_name="activities_dates"
    )
    price_adult = models.FloatField(default=0.0)
    price_child = models.FloatField(default=0.0)
    adult_quantity = models.PositiveIntegerField(default=1)
    child_quantity = models.PositiveIntegerField(default=1)
    date_launch = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}, {self.activity_package.name}"


class ActivityDateBookingDetail(models.Model):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="activity_date_detail"
    )
    activity_date = models.ForeignKey(
        ActivityDate, on_delete=models.CASCADE, related_name="activities_dates_bookings"
    )
    price_adult = models.FloatField(default=0.0)
    price_child = models.FloatField(default=0.0)
    adult_quantity_booking = models.PositiveIntegerField(default=1)
    child_quantity_booking = models.PositiveIntegerField(default=1)
    date_launch = models.DateTimeField()
    activity_package_name = models.CharField(max_length=255, null=True, blank=True)
    activity_name = models.CharField(max_length=255, null=True, blank=True)
    activity_image = models.CharField(max_length=255, null=True, blank=True)
    avg_price = models.FloatField(default=0.0)
    avg_star = models.FloatField(default=0.0)
    city_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.city_name}, {self.activity_package_name}"
