from django.urls import path
from .views import (
    PromotionListCreateView,
    PromotionDetailView,
    PromotionCreateView,
)

urlpatterns = [
    path("", PromotionListCreateView.as_view(), name="promotion-list-create"),
    path("<int:pk>/", PromotionDetailView.as_view(), name="promotion-detail"),
    path("create-details/", PromotionCreateView.as_view(), name="promotion-create"),
]
