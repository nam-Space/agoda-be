from django.urls import path
from .views import (
    NeighborhoodListView,
    NeighborhoodDetailView,
    NeighborhoodCreateView,
    NeighborhoodUpdateView,
    NeighborhoodDeleteView,
)

urlpatterns = [
    path("", NeighborhoodListView.as_view(), name="neighborhood-list"),
    path(
        "/<int:pk>/",
        NeighborhoodDetailView.as_view(),
        name="neighborhood-detail",
    ),
    path(
        "/create/",
        NeighborhoodCreateView.as_view(),
        name="neighborhood-create",
    ),
    path(
        "/<int:pk>/update/",
        NeighborhoodUpdateView.as_view(),
        name="neighborhood-update",
    ),
    path(
        "/<int:pk>/delete/",
        NeighborhoodDeleteView.as_view(),
        name="neighborhood-delete",
    ),
]
