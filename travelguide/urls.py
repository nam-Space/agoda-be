from django.urls import path
from .views import TravelGuideByHotelView

urlpatterns = [
    path(
        "by-hotel/<int:hotel_id>/",
        TravelGuideByHotelView.as_view(),
        name="travel-guides-by-hotel",
    ),
]
