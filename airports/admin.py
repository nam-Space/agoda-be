# countries/admin.py
from django.contrib import admin
from .models import Airport


class AirportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "lat",
        "lng",
        "created_at",
        "description",
        "location",
    )  # Hiển thị
    search_fields = ("name",)
    list_filter = ("created_at",)


admin.site.register(Airport, AirportAdmin)
