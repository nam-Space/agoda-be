from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HotelListView,
    HotelCreateView,
    HotelDetailView,
    HotelUpdateView,
    HotelDeleteView,
    HotelImageDeleteView,
)

urlpatterns = [
    path(
        "hotels/", HotelListView.as_view(), name="hotel-list"
    ),  # GET tất cả khách sạn, phân trang
    path(
        "hotels/create/", HotelCreateView.as_view(), name="hotel-create"
    ),  # POST tạo khách sạn
    path(
        "hotels/<int:pk>/", HotelDetailView.as_view(), name="hotel-detail"
    ),  # GET chi tiết khách sạn
    path(
        "hotels/<int:pk>/update/", HotelUpdateView.as_view(), name="hotel-update"
    ),  # PUT/PATCH cập nhật khách sạn
    path(
        "hotels/<int:pk>/delete/", HotelDeleteView.as_view(), name="hotel-delete"
    ),  # DELETE xóa khách sạn
    path(
        "hotel-images/<int:pk>/delete/",
        HotelImageDeleteView.as_view(),
        name="hotel-image-delete",
    ),  # DELETE xóa ảnh khách sạn
]
