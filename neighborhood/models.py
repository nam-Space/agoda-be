from django.db import models
from cities.models import City


# Khu vực trong thành phố (ví dụ: Phước Mỹ - Đà Nẵng, Quận 1 - TP.HCM)
class Neighborhood(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="neighborhood"
    )

    def __str__(self):
        return f"{self.name} ({self.city.name})"
