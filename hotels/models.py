from django.db import models
from cities.models import City


class Hotel(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="hotels", null=True
    )
    owner = models.OneToOneField(  # 🔹 Liên kết 1-0 với CustomUser
        "accounts.CustomUser",
        on_delete=models.SET_NULL,  # Nếu user bị xóa, giữ hotel lại
        related_name="hotel",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    nearbyLocation = models.TextField(blank=True, null=True)
    point = models.FloatField(default=0.0)
    mostFeature = models.TextField(blank=True, null=True)
    facilities = models.TextField(blank=True, null=True)
    withUs = models.TextField(blank=True, null=True)
    usefulInformation = models.TextField(blank=True, null=True)
    amenitiesAndFacilities = models.TextField(blank=True, null=True)
    locationInfo = models.TextField(null=True, blank=True)
    regulation = models.TextField(blank=True)
    avg_star = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# Model để lưu thông tin về hình ảnh khách sạn
class HotelImage(models.Model):
    hotel = models.ForeignKey("Hotel", related_name="images", on_delete=models.CASCADE)
    image = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.hotel.name}"
