from django.urls import path
from .views import AirlineListView, AirlineDetailView, AircraftListView, AircraftDetailView

urlpatterns = [
    path('', AirlineListView.as_view(), name='airline-list'),
    path('<int:pk>/', AirlineDetailView.as_view(), name='airline-detail'),
    path('aircrafts/', AircraftListView.as_view(), name='aircraft-list'),
    path('aircrafts/<int:pk>/', AircraftDetailView.as_view(), name='aircraft-detail'),
]
