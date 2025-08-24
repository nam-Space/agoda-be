# countries/urls.py
from django.urls import path
from .views import (
    CountryListView,
    CountryDetailView,
    CountryCreateView,
    CountryUpdateView,
    CountryDeleteView,
)

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="country-list"),
    path("countries/create/", CountryCreateView.as_view(), name="country-create"),
    path("countries/<int:pk>/", CountryDetailView.as_view(), name="country-detail"),
    path(
        "countries/<int:pk>/update/", CountryUpdateView.as_view(), name="country-update"
    ),
    path(
        "countries/<int:pk>/delete/", CountryDeleteView.as_view(), name="country-delete"
    ),  # Xóa quốc gia
]
