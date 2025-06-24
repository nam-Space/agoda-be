from django.contrib import admin
from .models import CustomUser


class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "birthday",
        "phone_number",
        "gender",
        "role",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_active", "date_joined", "gender", "role")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)


admin.site.register(CustomUser, CustomUserAdmin)
