from django.contrib import admin
from .models import Hotel, HotelImage


# Hotel Admin
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "lat",
        "lng",
        "location",
        "avg_star",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "location")
    list_filter = ("avg_star",)
    ordering = ("-created_at",)


class HotelImageAdmin(admin.ModelAdmin):
    list_display = ("hotel", "image", "created_at")
    search_fields = ("hotel__name",)


admin.site.register(Hotel, HotelAdmin)
admin.site.register(HotelImage, HotelImageAdmin)
