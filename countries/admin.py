# countries/admin.py
from django.contrib import admin
from .models import Country


class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "description")  # Hiển thị description
    search_fields = ("name",)
    list_filter = ("created_at",)


admin.site.register(Country, CountryAdmin)
