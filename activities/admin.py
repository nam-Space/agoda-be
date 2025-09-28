from django.contrib import admin
from .models import Activity, ActivityImage, ActivityPackage, ActivityDate


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "city",
        "avg_price",
        "avg_star",
        "total_time",
        "created_at",
    )
    search_fields = ("name", "city__name")
    list_filter = ("city", "created_at")
    ordering = ("-created_at",)


@admin.register(ActivityImage)
class ActivityImageAdmin(admin.ModelAdmin):
    list_display = ("id", "activity", "image", "created_at")
    search_fields = ("activity__name",)
    list_filter = ("created_at",)


@admin.register(ActivityPackage)
class ActivityPackageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "activity")
    search_fields = ("name", "activity__name")
    list_filter = ("activity",)


@admin.register(ActivityDate)
class ActivityDateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "activity_package", "price", "date_launch")
    search_fields = ("name", "activity_package__name")
    list_filter = ("activity_package", "date_launch")
