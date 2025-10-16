from django.db import models
from cities.models import City


class TravelTip(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="travel_tips")
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    type = models.CharField(
        max_length=100, default="general"
    )  # ví dụ: reasons, best_time, tips, transport
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.city.name}"
