from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Neighborhood
from .serializers import NeighborhoodSerializer, NeighborhoodCreateSerializer


class NeighborhoodListView(generics.ListAPIView):
    serializer_class = NeighborhoodSerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        queryset = Neighborhood.objects.all()
        city_id = self.request.query_params.get("city_id")  # lấy ?city_id=...
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        return queryset


class NeighborhoodDetailView(generics.RetrieveAPIView):
    queryset = Neighborhood.objects.all()
    serializer_class = NeighborhoodSerializer
    authentication_classes = []
    permission_classes = []


class NeighborhoodCreateView(generics.CreateAPIView):
    queryset = Neighborhood.objects.all()
    serializer_class = NeighborhoodCreateSerializer
    permission_classes = [IsAuthenticated]


class NeighborhoodUpdateView(generics.UpdateAPIView):
    queryset = Neighborhood.objects.all()
    serializer_class = NeighborhoodCreateSerializer
    permission_classes = [IsAuthenticated]


class NeighborhoodDeleteView(generics.DestroyAPIView):
    queryset = Neighborhood.objects.all()
    serializer_class = NeighborhoodSerializer
    permission_classes = [IsAuthenticated]
