from rest_framework import generics
from .models import TravelTip
from .serializers import TravelTipSerializer


class TravelTipListView(generics.ListAPIView):
    serializer_class = TravelTipSerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        city_id = self.request.query_params.get("cityId")
        if city_id:
            return TravelTip.objects.filter(city_id=city_id).order_by("id")
        return TravelTip.objects.none()
