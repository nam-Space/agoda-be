from django.urls import path
from .views import (
    ReviewListView,
    ReviewCreateView,
    ReviewDetailView,
    ReviewUpdateView,
    ReviewDeleteView,
)

urlpatterns = [
    path("reviews/", ReviewListView.as_view(), name="review-list"),
    path(
        "reviews/create/", ReviewCreateView.as_view(), name="view-create"
    ),  # POST tạo reviews
    path(
        "reviews/<int:pk>/", ReviewDetailView.as_view(), name="view-detail"
    ),  # GET chi tiết reviews
    path(
        "reviews/<int:pk>/update/",
        ReviewUpdateView.as_view(),
        name="view-update",
    ),  # PUT/PATCH cập nhật reviews
    path(
        "reviews/<int:pk>/delete/",
        ReviewDeleteView.as_view(),
        name="view-delete",
    ),  # DELETE xóa reviews
]
