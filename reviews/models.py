from django.db import models
from django.conf import settings
from bookings.models import ServiceType  # import lại từ chỗ khai báo ServiceType
from accounts.models import CustomUser


class Review(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=True,
        blank=True,
    )
    service_type = models.IntegerField(
        choices=ServiceType.choices, blank=True, null=True
    )
    service_ref_id = models.IntegerField(
        blank=True, null=True
    )  # ID của dịch vụ cụ thể (Hotel, Car, Activity, ...)
    rating = models.PositiveSmallIntegerField(
        blank=True, null=True
    )  # thường là 1–5 sao
    comment = models.TextField(blank=True, null=True)
    # 🆕 Thêm 2 trường đánh giá cảm xúc
    sentiment = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review({self.user}) - {ServiceType(self.service_type).label} #{self.service_ref_id}"

    @property
    def service_type_name(self):
        """Trả về tên hiển thị (label) của service_type"""
        return ServiceType(self.service_type).label

    def get_service_instance(self):
        """Trả về instance cụ thể của dịch vụ"""
        from hotels.models import Hotel
        from activities.models import Activity

        if self.service_type == ServiceType.HOTEL:
            return Hotel.objects.filter(id=self.service_ref_id).first()
        elif self.service_type == ServiceType.ACTIVITY:
            return Activity.objects.filter(id=self.service_ref_id).first()
        return None
