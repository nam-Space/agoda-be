from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlightViewSet, FlightBookingDetailViewSet, FlightLegViewSet, SeatClassPricingViewSet

router = DefaultRouter()
router.register(r'legs', FlightLegViewSet, basename='flight-leg')
router.register(r'seat-classes', SeatClassPricingViewSet, basename='seat-class')
router.register(r'bookings', FlightBookingDetailViewSet, basename='flight-booking')
router.register(r'', FlightViewSet, basename='flight')

urlpatterns = [
    path('', include(router.urls)),
]