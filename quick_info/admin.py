from django.contrib import admin
from .models import QuickInfo


class QuickInfoAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "highlight", "city")
    list_filter = ("highlight", "city")
    search_fields = ("label", "city__name")


admin.site.register(QuickInfo, QuickInfoAdmin)
