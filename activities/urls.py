from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ActivityListView,
    ActivityCreateView,
    ActivityDetailView,
    ActivityUpdateView,
    ActivityDeleteView,
    ActivityImageDeleteView,
    ActivityPackageListView,
    ActivityPackageListForActivityAndDateLaunchView,
    ActivityPackageCreateView,
    ActivityPackageDetailView,
    ActivityPackageUpdateView,
    ActivityPackageDeleteView,
    ActivityDateListView,
    ActivityDateCreateView,
    ActivityDateDetailView,
    ActivityDateUpdateView,
    ActivityDateDeleteView,
    ActivityDateBulkCreateView,
    ActivityDateBulkDeleteView,
    ActivityDateBookingDetailView,
    ActivityDateBookingCreateView,
)

urlpatterns = [
    path(
        "activities/", ActivityListView.as_view(), name="activity-list"
    ),  # GET tất cả activities, phân trang
    path(
        "activities/create/", ActivityCreateView.as_view(), name="activity-create"
    ),  # POST tạo activities
    path(
        "activities/<int:pk>/", ActivityDetailView.as_view(), name="activity-detail"
    ),  # GET chi tiết activities
    path(
        "activities/<int:pk>/update/",
        ActivityUpdateView.as_view(),
        name="activity-update",
    ),  # PUT/PATCH cập nhật activities
    path(
        "activities/<int:pk>/delete/",
        ActivityDeleteView.as_view(),
        name="activity-delete",
    ),  # DELETE xóa activities
    path(
        "activity-images/<int:pk>/delete/",
        ActivityImageDeleteView.as_view(),
        name="activity-image-delete",
    ),  # DELETE xóa ảnh activities
    path(
        "activities-packages/",
        ActivityPackageListView.as_view(),
        name="activity-package-list",
    ),  # GET tất cả activities-packages, phân trang
    path(
        "activities-packages/activity-and-date-launch/",
        ActivityPackageListForActivityAndDateLaunchView.as_view(),
        name="activity-packages-list-for-activity-and-date-launch",
    ),
    path(
        "activities-packages/create/",
        ActivityPackageCreateView.as_view(),
        name="activity-package-create",
    ),  # POST tạo activities-packages
    path(
        "activities-packages/<int:pk>/",
        ActivityPackageDetailView.as_view(),
        name="activity-package-detail",
    ),  # GET chi tiết activities-packages
    path(
        "activities-packages/<int:pk>/update/",
        ActivityPackageUpdateView.as_view(),
        name="activity-package-update",
    ),  # PUT/PATCH cập nhật activities-packages
    path(
        "activities-packages/<int:pk>/delete/",
        ActivityPackageDeleteView.as_view(),
        name="activity-package-delete",
    ),  # DELETE xóa activities-packages
    path(
        "activities-dates/",
        ActivityDateListView.as_view(),
        name="activity-date-list",
    ),  # GET tất cả activities-dates, phân trang
    path(
        "activities-dates/create/",
        ActivityDateCreateView.as_view(),
        name="activity-date-create",
    ),  # POST tạo activities-dates
    path(
        "activities-dates/create/bulk/",
        ActivityDateBulkCreateView.as_view(),
        name="activity-date-create-bulk",
    ),  # POST tạo activities-dates
    path(
        "activities-dates/<int:pk>/",
        ActivityDateDetailView.as_view(),
        name="activity-date-detail",
    ),  # GET chi tiết activities-dates
    path(
        "activities-dates/<int:pk>/update/",
        ActivityDateUpdateView.as_view(),
        name="activity-date-update",
    ),  # PUT/PATCH cập nhật activities-dates
    path(
        "activities-dates/<int:pk>/delete/",
        ActivityDateDeleteView.as_view(),
        name="activity-date-delete",
    ),  # DELETE xóa activities-dates
    path(
        "activities-dates/bulk-delete/",
        ActivityDateBulkDeleteView.as_view(),
        name="activity-date-bulk-delete",
    ),
    path(
        "activities-dates-booking/<int:pk>/",
        ActivityDateBookingDetailView.as_view(),
        name="activity-date-booking-detail",
    ),
    path(
        "activities-dates-booking/create/",
        ActivityDateBookingCreateView.as_view(),
        name="activity-dates-booking-create",
    ),
]
