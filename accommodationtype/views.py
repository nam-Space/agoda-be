from rest_framework import generics
from rest_framework.response import Response
from .models import AccommodationType
from .serializers import AccommodationTypeSerializer


class AccommodationTypeByCityView(generics.ListAPIView):
    serializer_class = AccommodationTypeSerializer

    def get_queryset(self):
        city_id = self.kwargs.get("city_id")
        return AccommodationType.objects.filter(city_id=city_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched accommodation types successfully!",
                "data": serializer.data,
            }
        )
