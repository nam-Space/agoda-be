from django.db import models
from cities.models import City


# Thông tin nhanh về thành phố (giá, khu phổ biến, khách sạn, v.v.)
class QuickInfo(models.Model):
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    highlight = models.BooleanField(default=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="quick_infos")

    def __str__(self):
        return f"{self.label} - {self.city.name}"
