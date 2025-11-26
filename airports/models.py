# airports/models.py
from django.db import models
from cities.models import City


# Model sân bay
class Airport(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="airports", null=True
    )
    code = models.CharField(max_length=10, unique=True, null=True, blank=True)  # Mã sân bay (VD: HAN, SGN)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)  # Trường description mới
    location = models.TextField(blank=True, null=True)  # Trường location mới
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
