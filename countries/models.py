# countries/models.py
from django.db import models


# Model Quốc gia
class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)  # Trường description mới
    calling_code = models.CharField(
        max_length=10, blank=True, null=True, help_text="Mã vùng điện thoại, ví dụ +84"
    )
    image_handbook = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
