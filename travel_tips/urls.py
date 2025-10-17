from django.urls import path
from .views import TravelTipListView

urlpatterns = [
    path("by-city/", TravelTipListView.as_view(), name="travel-tip-by-city"),
]
