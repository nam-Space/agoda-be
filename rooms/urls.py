# rooms/urls.py
from django.urls import path
from .views import (
    RoomListView,
    RoomCreateView,
    RoomDetailView,
    RoomUpdateView,
    RoomDeleteView,
    RoomImageDeleteView,
)

urlpatterns = [
    path("rooms/", RoomListView.as_view(), name="room-list"),
    path("rooms/create/", RoomCreateView.as_view(), name="room-create"),
    path("rooms/<int:pk>/", RoomDetailView.as_view(), name="room-detail"),
    path("rooms/<int:pk>/update/", RoomUpdateView.as_view(), name="room-update"),
    path("rooms/<int:pk>/delete/", RoomDeleteView.as_view(), name="room-delete"),
    path(
        "room-images/<int:pk>/delete/",
        RoomImageDeleteView.as_view(),
        name="room-image-delete",
    ),
]
