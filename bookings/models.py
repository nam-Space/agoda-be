import uuid
from django.db import models
from django.conf import settings
from payments.constants.payment_status import PaymentStatus
from .constants.service_type import ServiceType
from .constants.booking_status import BookingStatus
from accounts.models import CustomUser


class Booking(models.Model):
    service_type = models.PositiveSmallIntegerField(choices=ServiceType.choices)
    service_ref_id = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL
    )
    booking_code = models.CharField(max_length=50, unique=True, editable=False)

    status = models.PositiveSmallIntegerField(
        choices=BookingStatus.choices, default=BookingStatus.PENDING
    )
    payment_status = models.PositiveSmallIntegerField(
        choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    total_price = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.booking_code:
            from datetime import datetime

            date_str = datetime.now().strftime("%Y%m%d")
            self.booking_code = f"AGD{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.booking_code}"


class GuestInfo(models.Model):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="guest_info"
    )
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=100, null=True, blank=True)
    special_request = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.full_name
