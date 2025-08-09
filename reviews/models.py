from django.db import models
from django.conf import settings

class Review(models.Model):
    hotel = models.ForeignKey(
        'hotels.Hotel',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField()  # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('hotel', 'user')  # 1 user chỉ review 1 lần/khách sạn
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.hotel} ({self.rating})"
