# cities/admin.py
from django.contrib import admin
from .models import Car


class CarAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "capacity",
        "luggage",
        "avg_star",
        "avg_speed",
        "created_at",
    )  # Hiển thị description
    search_fields = ("name", "description")


admin.site.register(Car, CarAdmin)
