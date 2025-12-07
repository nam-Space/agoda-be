from django.db import models
from accounts.models import CustomUser


class Airline(models.Model):
    flight_operations_staff = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="airlines",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(
        max_length=10, unique=True, help_text="Mã IATA (VD: VN, VJ)"
    )
    logo = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Aircraft(models.Model):
    airline = models.ForeignKey(
        Airline, on_delete=models.CASCADE, related_name="aircrafts"
    )
    model = models.CharField(max_length=100, help_text="VD: Boeing 777, Airbus A321")
    registration_number = models.CharField(
        max_length=50, unique=True, help_text="Số đăng ký máy bay (VD: VN-A123)"
    )

    # Thông tin kỹ thuật
    total_seats = models.IntegerField(default=0)
    economy_seats = models.IntegerField(default=0)
    business_seats = models.IntegerField(default=0)
    first_class_seats = models.IntegerField(default=0)

    # Trạng thái
    is_active = models.BooleanField(default=True)
    manufacture_year = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["airline", "model"]
        verbose_name = "Aircraft"
        verbose_name_plural = "Aircrafts"

    def __str__(self):
        return f"{self.airline.code} - {self.model} ({self.registration_number})"
