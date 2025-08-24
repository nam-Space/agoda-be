# countries/models.py
from django.db import models


# Model Quốc gia
class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)  # Trường description mới
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
