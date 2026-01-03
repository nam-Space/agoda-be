from django.db import models


class BookingStatus(models.IntegerChoices):
    PENDING = 1, "Pending"
    CONFIRMED = 2, "Confirmed"
    CANCELLED = 3, "Cancelled"
    COMPLETED = 4, "Completed"
    REBOOKED = 5, "Rebooked"
