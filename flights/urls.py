from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FlightListView,
    FlightViewSet,
    FlightBookingDetailViewSet,
    FlightLegViewSet,
    SeatClassPricingViewSet,
)

router = DefaultRouter()
router.register(r"legs", FlightLegViewSet, basename="flight-leg")
router.register(r"seat-classes", SeatClassPricingViewSet, basename="seat-class")
router.register(r"bookings", FlightBookingDetailViewSet, basename="flight-booking")
router.register(
    r"", FlightViewSet, basename="flight"
)  # trong cái trường hợp flight mà có flightLeg bị rỗng, nó sẽ không hiện ra trong danh sách

urlpatterns = [
    path(
        "flights-for-admin/", FlightListView.as_view(), name="flight-list"
    ),  # GET tất cả flights, phân trang cho admin, kể cả trường hợp flight mà có flightLeg bị rỗng
    path("", include(router.urls)),
]
