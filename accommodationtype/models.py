from django.db import models
from cities.models import City  # import model City bạn đã có sẵn


class AccommodationType(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="accommodation_types"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.city.name})"
