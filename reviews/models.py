from django.db import models
from django.conf import settings
from bookings.models import ServiceType  # import lại từ chỗ khai báo ServiceType
from accounts.models import CustomUser


class Review(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="reviews"
    )
    service_type = models.IntegerField(choices=ServiceType.choices)
    service_ref_id = (
        models.IntegerField()
    )  # ID của dịch vụ cụ thể (Hotel, Car, Activity, ...)
    rating = models.PositiveSmallIntegerField()  # thường là 1–5 sao
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review"
        unique_together = (
            "user",
            "service_type",
            "service_ref_id",
        )  # 1 user chỉ được review 1 lần trên 1 dịch vụ

    def __str__(self):
        return f"Review({self.user}) - {ServiceType(self.service_type).label} #{self.service_ref_id}"

    @property
    def service_type_name(self):
        """Trả về tên hiển thị (label) của service_type"""
        return ServiceType(self.service_type).label
