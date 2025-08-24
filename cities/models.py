# cities/models.py
from django.db import models
from countries.models import Country  # Liên kết với model Country


# Model Thành phố
class City(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="cities"
    )
    description = models.TextField(blank=True, null=True)  # Trường description mới
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.name}, {self.country.name}"
