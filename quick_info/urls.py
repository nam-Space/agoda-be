from django.urls import path
from .views import (
    QuickInfoListView,
    QuickInfoDetailView,
    QuickInfoCreateView,
    QuickInfoUpdateView,
    QuickInfoDeleteView,
    QuickInfoByCityView,  # ✅ import thêm
)

urlpatterns = [
    path("", QuickInfoListView.as_view(), name="quick-info-list"),
    path("<int:pk>/", QuickInfoDetailView.as_view(), name="quick-info-detail"),
    path("create/", QuickInfoCreateView.as_view(), name="quick-info-create"),
    path("<int:pk>/update/", QuickInfoUpdateView.as_view(), name="quick-info-update"),
    path("<int:pk>/delete/", QuickInfoDeleteView.as_view(), name="quick-info-delete"),
    path("by-city/", QuickInfoByCityView.as_view(), name="quick-info-by-city"),
]
