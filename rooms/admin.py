from django.contrib import admin
from .models import Room, RoomImage, RoomAmenity


# Room Admin
class RoomAdmin(admin.ModelAdmin):
    list_display = ("hotel", "room_type", "price_per_night", "capacity", "available")
    search_fields = ("hotel__name", "room_type")
    list_filter = ("available", "hotel")


class RoomImageAdmin(admin.ModelAdmin):
    list_display = ("room", "image", "created_at")
    search_fields = ("room__room_type", "room__hotel__name")

# RoomAmenity Admin
class RoomAmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "room")
    search_fields = ("name", "room__room_type", "room__hotel__name")

admin.site.register(Room, RoomAdmin)
admin.site.register(RoomImage, RoomImageAdmin)
admin.site.register(RoomAmenity, RoomAmenityAdmin)
