from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlightViewSet, FlightBookingDetailViewSet

router = DefaultRouter()
router.register(r'', FlightViewSet)

urlpatterns = [
    path('', include(router.urls)),
]