from django.db import models
from cities.models import City


class FAQ(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="faqs")
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question[:50]
