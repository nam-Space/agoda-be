# airports/urls.py
from django.urls import path
from .views import (
    AirportListView,
    AirportDetailView,
    AirportCreateView,
    AirportUpdateView,
    AirportDeleteView,
)

urlpatterns = [
    path("airports/", AirportListView.as_view(), name="airport-list"),
    path("airports/create/", AirportCreateView.as_view(), name="airport-create"),
    path("airports/<int:pk>/", AirportDetailView.as_view(), name="airport-detail"),
    path(
        "airports/<int:pk>/update/", AirportUpdateView.as_view(), name="airport-update"
    ),
    path(
        "airports/<int:pk>/delete/", AirportDeleteView.as_view(), name="airport-delete"
    ),  # Xóa sân bay
]
