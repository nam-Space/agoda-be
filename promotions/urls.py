from django.urls import path
from .views import (
    PromotionListCreateView, PromotionDetailView,
    HotelPromotionListCreateView, HotelPromotionDetailView,
    FlightPromotionListCreateView, FlightPromotionDetailView,
)

urlpatterns = [
    path("", PromotionListCreateView.as_view(), name="promotion-list-create"),
    path("<int:pk>/", PromotionDetailView.as_view(), name="promotion-detail"),

    path("hotel-promotions/", HotelPromotionListCreateView.as_view(), name="hotel-promotion-list-create"),
    path("hotel-promotions/<int:pk>/", HotelPromotionDetailView.as_view(), name="hotel-promotion-detail"),

    path("flight-promotions/", FlightPromotionListCreateView.as_view(), name="flight-promotion-list-create"),
    path("flight-promotions/<int:pk>/", FlightPromotionDetailView.as_view(), name="flight-promotion-detail"),
]
