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
        ("staff", "Staff"),
        ("driver", "Driver"),
        ("owner", "Owner"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="customer")

    birthday = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    avatar = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.username
