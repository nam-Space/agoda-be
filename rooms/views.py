from rest_framework import viewsets
from .models import Room, RoomImage
from .serializers import (
    RoomSerializer,
    RoomImageSerializer,
)


# ViewSet cho Room
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class RoomImageViewSet(viewsets.ModelViewSet):
    queryset = RoomImage.objects.all()
    serializer_class = RoomImageSerializer
