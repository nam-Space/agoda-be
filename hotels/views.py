from rest_framework import viewsets
from .models import Hotel, HotelImage
from .serializers import (
    HotelSerializer,
    HotelImageSerializer,
)


# ViewSet cho Hotel
class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer


class HotelImageViewSet(viewsets.ModelViewSet):
    queryset = HotelImage.objects.all()
    serializer_class = HotelImageSerializer
