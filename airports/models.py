# airports/models.py
from django.db import models


# Model sân bay
class Airport(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)  # Trường description mới
    location = models.TextField(blank=True, null=True)  # Trường location mới
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
