from django.urls import path
from .views import LocationSuggestionsView

urlpatterns = [
    path('suggestions/', LocationSuggestionsView.as_view(), name='location_suggestions'),
]