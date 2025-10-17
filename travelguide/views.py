from rest_framework import generics
from rest_framework.response import Response
from .models import TravelGuide
from .serializers import TravelGuideSerializer


class TravelGuideByHotelView(generics.ListAPIView):
    serializer_class = TravelGuideSerializer

    def get_queryset(self):
        hotel_id = self.kwargs.get("hotel_id")
        return TravelGuide.objects.filter(hotel_id=hotel_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched travel guides successfully!",
                "data": serializer.data,
            }
        )
