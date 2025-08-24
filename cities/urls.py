# cities/urls.py
from django.urls import path
from .views import (
    CityListView,
    CityDetailView,
    CityCreateView,
    CityUpdateView,
    CityDeleteView,
)

urlpatterns = [
    path(
        "cities/", CityListView.as_view(), name="city-list"
    ),  # GET tất cả thành phố, phân trang
    path(
        "cities/create/", CityCreateView.as_view(), name="city-create"
    ),  # POST tạo thành phố
    path(
        "cities/<int:pk>/", CityDetailView.as_view(), name="city-detail"
    ),  # GET chi tiết thành phố
    path(
        "cities/<int:pk>/update/", CityUpdateView.as_view(), name="city-update"
    ),  # PUT/PATCH cập nhật thành phố
    path(
        "cities/<int:pk>/delete/", CityDeleteView.as_view(), name="city-delete"
    ),  # DELETE xóa thành phố
]
