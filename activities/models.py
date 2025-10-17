# activities/models.py
from django.db import models
from cities.models import City  # Liên kết với model Country
from bookings.models import Booking


# Model hoạt động
class Activity(models.Model):
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
    more_information = models.TextField(blank=True, null=True)  # Trường description mới
    cancellation_policy = models.TextField(
        blank=True, null=True
    )  # Trường cancellation_policy mới
    departure_information = models.TextField(
        blank=True, null=True
    )  # Trường departure_information mới
    avg_price = models.FloatField(default=0.0)
    avg_star = models.FloatField(default=0.0)
    total_time = models.PositiveIntegerField()  # số giờ hoạt động
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}, {self.city.name}"


# Model để lưu thông tin về hình ảnh hoạt động
class ActivityImage(models.Model):
    activity = models.ForeignKey(
        "Activity", related_name="images", on_delete=models.CASCADE
    )
    image = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.activity.name}"


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
        ActivityDate, on_delete=models.CASCADE, related_name="activities_dates"
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
