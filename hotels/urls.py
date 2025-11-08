from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HotelListView,
    HotelCreateView,
    HotelDetailView,
    HotelUpdateView,
    HotelUpdateViewNotImage,
    HotelDeleteView,
    HotelImageDeleteView,
    HotelByCityView,
    HotelSearchView,
    UserHotelInteractionDetailView,
    UserHotelInteractionUpsertView,
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
        "hotels/<int:pk>/update/not-image/",
        HotelUpdateViewNotImage.as_view(),
        name="hotel-update-not-image",
    ),  # PUT/PATCH cập nhật khách sạn (không cập nhật ảnh)
    path(
        "hotels/<int:pk>/", HotelDetailView.as_view(), name="hotel-detail"
    ),  # GET chi tiết tương tác người dùng khách sạn
    path(
        "user-hotel-interaction/<int:hotel_id>/",
        UserHotelInteractionDetailView.as_view(),
        name="user-hotel-interaction-detail",
    ),  # GET chi tiết tương tác người dùng khách sạn
    path(
        "user-hotel-interaction/upsert/",
        UserHotelInteractionUpsertView.as_view(),
        name="user-hotel-interaction-upsert",
    ),  # PUT/PATCH cập nhật tương tác người dùng khách sạn
    path(
        "hotels/<int:pk>/delete/", HotelDeleteView.as_view(), name="hotel-delete"
    ),  # DELETE xóa khách sạn
    path(
        "hotel-images/<int:pk>/delete/",
        HotelImageDeleteView.as_view(),
        name="hotel-image-delete",
    ),  # DELETE xóa ảnh khách sạn
    path("by-city/<int:city_id>/", HotelByCityView.as_view(), name="hotel-by-city"),
    path(
        "search/", HotelSearchView.as_view(), name="hotel-search"
    ),  # Tìm kiếm khách sạn
]
