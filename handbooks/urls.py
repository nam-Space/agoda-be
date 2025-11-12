# countries/urls.py
from django.urls import path
from .views import (
    HandbookListView,
    HandbookDetailView,
    HandbookCreateView,
    HandbookUpdateView,
    HandbookDeleteView,
    UserHandbookInteractionDetailView,
    UserHandbookInteractionUpsertView,
)

urlpatterns = [
    path("handbooks/", HandbookListView.as_view(), name="handbook-list"),
    path("handbooks/create/", HandbookCreateView.as_view(), name="handbook-create"),
    path("handbooks/<int:pk>/", HandbookDetailView.as_view(), name="handbook-detail"),
    path(
        "handbooks/<int:pk>/update/",
        HandbookUpdateView.as_view(),
        name="handbook-update",
    ),
    path(
        "handbooks/<int:pk>/delete/",
        HandbookDeleteView.as_view(),
        name="handbook-delete",
    ),  # Xóa cẩm nang
    path(
        "user-handbook-interaction/<int:handbook_id>/",
        UserHandbookInteractionDetailView.as_view(),
        name="user-handbook-interaction-detail",
    ),  # GET chi tiết tương tác người dùng cẩm nang
    path(
        "user-handbook-interaction/upsert/",
        UserHandbookInteractionUpsertView.as_view(),
        name="user-handbook-interaction-upsert",
    ),  # PUT/PATCH cập nhật tương tác người dùng cẩm nang
]
