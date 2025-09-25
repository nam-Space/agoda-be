# cars/urls.py
from django.urls import path
from .views import (
    CarListView,
    CarDetailView,
    CarCreateView,
    CarUpdateView,
    CarDeleteView,
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
]
