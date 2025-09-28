# activities/models.py
from django.db import models
from cities.models import City  # Liên kết với model Country


# Model hoạt động
class Activity(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="activities")
    short_description = models.CharField(max_length=255, null=True, blank=True)
    more_information = models.TextField(blank=True, null=True)  # Trường description mới
    cancellation_policy = models.TextField(
        blank=True, null=True
    )  # Trường description mới
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
    name = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date_launch = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}, {self.activity_package.name}"
