from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HotelViewSet, HotelImageViewSet

router = DefaultRouter()
router.register(r"hotels", HotelViewSet)
router.register(r"hotel-images", HotelImageViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
