from django.contrib import admin
from .models import Hotel, HotelImage, UserSearchHistory


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


class UserSearchHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "destination",
        "check_in",
        "check_out",
        "adults",
        "rooms",
        "created_at"
    )
    list_filter = ("created_at", "adults", "rooms")
    search_fields = ("destination", "user__username", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


admin.site.register(Hotel, HotelAdmin)
admin.site.register(HotelImage, HotelImageAdmin)
admin.site.register(UserSearchHistory, UserSearchHistoryAdmin)
