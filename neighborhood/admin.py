from django.contrib import admin
from .models import Neighborhood


class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    search_fields = ("name", "city__name")
    list_filter = ("city",)


admin.site.register(Neighborhood, NeighborhoodAdmin)
