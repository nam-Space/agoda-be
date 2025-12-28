from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    # Trường mới: giới tính
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]
    gender = models.CharField(
        max_length=6, choices=GENDER_CHOICES, null=True, blank=True
    )

    # Trường mới: vai trò (role)
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("admin", "Admin"),
        ("hotel_staff", "Hotel Staff"),
        ("driver", "Driver"),
        ("owner", "Owner"),
        ("event_organizer", "Event Organizer"),
        ("marketing_manager", "Marketing Manager"),
        ("flight_operations_staff", "Flight Operations Staff"),
        ("airline_ticketing_staff", "Airline Ticketing Staff"),
    ]
    role = models.CharField(max_length=255, choices=ROLE_CHOICES, default="customer")
    birthday = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    avatar = models.CharField(max_length=255, null=True, blank=True)
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="hotel_staffs",
        null=True,
        blank=True,
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        on_delete=models.SET_NULL,
        related_name="hotel_staffs",
        null=True,
        blank=True,
    )
    flight_operation_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="flight_staffs",
        null=True,
        blank=True,
    )
    airline = models.ForeignKey(
        "airlines.Airline",
        on_delete=models.SET_NULL,
        related_name="flight_staffs",
        null=True,
        blank=True,
    )

    DRIVER_STATUS_CHOICES = [
        ("idle", "Idle"),
        ("busy", "Busy"),
    ]

    driver_status = models.CharField(
        max_length=6,
        choices=DRIVER_STATUS_CHOICES,
        default="idle",
    )
    driver_area = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        related_name="drivers",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username
