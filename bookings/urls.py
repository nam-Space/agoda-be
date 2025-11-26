# bookings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, RefundPolicyViewSet

router = DefaultRouter()
router.register(r'refund-policies', RefundPolicyViewSet, basename='refund-policy')
router.register(r'', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
]
