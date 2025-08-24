# cities/admin.py
from django.contrib import admin
from .models import City


class CityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "created_at",
        "description",
    )  # Hiển thị description
    search_fields = ("name", "country__name")
    list_filter = ("country", "created_at")


admin.site.register(City, CityAdmin)
