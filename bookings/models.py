import uuid
from django.db import models
from django.conf import settings
from payments.constants.payment_status import PaymentStatus
from .constants.service_type import ServiceType
from .constants.booking_status import BookingStatus
from accounts.models import CustomUser

class Booking(models.Model):
    service_type = models.PositiveSmallIntegerField(choices=ServiceType.choices)
    service_ref_ids = models.JSONField(null=True, blank=True, default=list, help_text="Danh sách id chi tiết dịch vụ")
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
    discount_amount = models.FloatField(default=0.0)  
    final_price = models.FloatField(default=0.0) 
    refund_amount = models.FloatField(default=0.0, null=True, blank=True, help_text="Số tiền đã hoàn lại")

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.booking_code:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d")
            self.booking_code = f"AGD{uuid.uuid4().hex[:6].upper()}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.booking_code} - {self.service_type}"


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


class RefundPolicy(models.Model):
    """Chính sách hoàn tiền cho từng loại dịch vụ"""
    class PolicyType(models.IntegerChoices):
        FULL_REFUND = 1, "Hoàn tiền 100%"
        PARTIAL_REFUND = 2, "Hoàn tiền một phần"
        NO_REFUND = 3, "Không hoàn tiền"
    
    service_type = models.PositiveSmallIntegerField(choices=ServiceType.choices)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    policy_type = models.IntegerField(choices=PolicyType.choices, default=PolicyType.FULL_REFUND)
    refund_percentage = models.FloatField(null=True, blank=True, help_text="Phần trăm hoàn tiền (0-100)")
    refund_amount = models.FloatField(null=True, blank=True, help_text="Số tiền hoàn cố định")
    hours_before_start = models.IntegerField(null=True, blank=True, help_text="Số giờ trước khi bắt đầu để áp dụng policy này")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_service_type_display()}"
