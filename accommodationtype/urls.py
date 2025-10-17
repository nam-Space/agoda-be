from django.urls import path
from .views import AccommodationTypeByCityView

urlpatterns = [
    path(
        "by-city/<int:city_id>/",
        AccommodationTypeByCityView.as_view(),
        name="accommodation-types-by-city",
    ),
]
