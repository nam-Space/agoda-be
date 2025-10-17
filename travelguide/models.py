from django.db import models
from hotels.models import Hotel


class TravelGuide(models.Model):
    hotel = models.ForeignKey(
        Hotel, on_delete=models.CASCADE, related_name="travel_guides",
        null=False,       # ✅ cho phép trống trong DB
        blank=False 
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.hotel.name}"
