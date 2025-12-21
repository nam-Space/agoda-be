# rooms/urls.py
from django.urls import path
from .views import (
    RoomListView,
    RoomAdminListView,
    RoomCreateView,
    RoomDetailView,
    RoomUpdateView,
    RoomDeleteView,
    RoomImageDeleteView,
    RoomAmenityListView,
    RoomSearchView,
    RoomBookingDetailView,
    RoomAmenityCreateView,
    RoomAmenityDetailView,
    RoomAmenityUpdateView,
    RoomAmenityDeleteView,
)

urlpatterns = [
    path("rooms/", RoomListView.as_view(), name="room-list"),
    path("rooms-admin/", RoomAdminListView.as_view(), name="room-admin-list"),
    path("rooms/create/", RoomCreateView.as_view(), name="room-create"),
    path("rooms/<int:pk>/", RoomDetailView.as_view(), name="room-detail"),
    path("rooms/<int:pk>/update/", RoomUpdateView.as_view(), name="room-update"),
    path("rooms/<int:pk>/delete/", RoomDeleteView.as_view(), name="room-delete"),
    path(
        "room-images/<int:pk>/delete/",
        RoomImageDeleteView.as_view(),
        name="room-image-delete",
    ),
    path("rooms/search/", RoomSearchView.as_view(), name="room-search"),
    path(
        "rooms-booking/<int:pk>/",
        RoomBookingDetailView.as_view(),
        name="room-booking-detail",
    ),
    # amenities
    path("amenities/", RoomAmenityListView.as_view(), name="amenities-list"),
    path("amenities/create/", RoomAmenityCreateView.as_view(), name="amenities-create"),
    path(
        "amenities/<int:pk>/", RoomAmenityDetailView.as_view(), name="amenities-detail"
    ),
    path(
        "amenities/<int:pk>/update/",
        RoomAmenityUpdateView.as_view(),
        name="amenities-update",
    ),
    path(
        "amenities/<int:pk>/delete/",
        RoomAmenityDeleteView.as_view(),
        name="amenities-delete",
    ),
]
