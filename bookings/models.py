from django.db import models
from accounts.models import CustomUser


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class Booking(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="bookings"
    )
    room = models.ForeignKey(
        "rooms.Room", on_delete=models.CASCADE, related_name="bookings"
    )

    check_in_date = models.DateField()
    check_out_date = models.DateField()
    number_of_guests = models.PositiveIntegerField()

    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=10, choices=BookingStatus.choices, default=BookingStatus.PENDING
    )

    booking_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.id} - {self.user.username} - {self.room}"
