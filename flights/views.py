from rest_framework import viewsets
from .models import Flight, FlightBookingDetail
from .serializers import FlightBookingDetailSerializer, FlightSerializer

class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.all()
    serializer_class = FlightSerializer


class FlightBookingDetailViewSet(viewsets.ModelViewSet):
    queryset = FlightBookingDetail.objects.all()
    serializer_class = FlightBookingDetailSerializer
