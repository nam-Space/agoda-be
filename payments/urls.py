# payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentViewSet,
    PaymentListView,
    PaymentDetailView,
    PaymentCreateView,
    PaymentUpdateView,
    PaymentDeleteView,
    PaymentListOverviewView,
)

router = DefaultRouter()
router.register(r"", PaymentViewSet, basename="payment")

urlpatterns = [
    path(
        "payments/", PaymentListView.as_view(), name="payment-list"
    ),  # GET tất cả thành phố, phân trang
    path(
        "payments/overview/",
        PaymentListOverviewView.as_view(),
        name="payment-overview-list",
    ),
    path(
        "payments/create/", PaymentCreateView.as_view(), name="payment-create"
    ),  # POST tạo payments
    path(
        "payments/<int:pk>/", PaymentDetailView.as_view(), name="payment-detail"
    ),  # GET chi tiết payments
    path(
        "payments/<int:pk>/update/",
        PaymentUpdateView.as_view(),
        name="payment-update",
    ),  # PUT/PATCH cập nhật payments
    path(
        "payments/<int:pk>/delete/",
        PaymentDeleteView.as_view(),
        name="payment-delete",
    ),  # DELETE xóa payments
    path("", include(router.urls)),
]
