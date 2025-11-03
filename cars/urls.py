# cars/urls.py
from django.urls import path
from .views import (
    CarListView,
    CarDetailView,
    CarCreateView,
    CarUpdateView,
    CarDeleteView,
    CarBookingDetailView,
    UserCarInteractionDetailView,
    UserCarInteractionUpsertView,
)

urlpatterns = [
    path("cars/", CarListView.as_view(), name="car-list"),  # GET tất cả xe, phân trang
    path("cars/create/", CarCreateView.as_view(), name="car-create"),  # POST tạo xe
    path(
        "cars/<int:pk>/", CarDetailView.as_view(), name="car-detail"
    ),  # GET chi tiết xe
    path(
        "cars/<int:pk>/update/", CarUpdateView.as_view(), name="car-update"
    ),  # PUT/PATCH cập nhật xe
    path(
        "cars/<int:pk>/delete/", CarDeleteView.as_view(), name="car-delete"
    ),  # DELETE xóa xe
    path(
        "cars-booking/<int:pk>/",
        CarBookingDetailView.as_view(),
        name="car-booking-detail",
    ),
    path(
        "user-car-interaction/<int:car_id>/",
        UserCarInteractionDetailView.as_view(),
        name="user-car-interaction-detail",
    ),  # GET chi tiết tương tác người dùng với taxi
    path(
        "user-car-interaction/upsert/",
        UserCarInteractionUpsertView.as_view(),
        name="user-car-interaction-upsert",
    ),  # PUT/PATCH cập nhật tương tác người dùng với taxi
]
