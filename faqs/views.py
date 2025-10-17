from rest_framework import generics
from .models import FAQ
from .serializers import FAQSerializer


class FAQListView(generics.ListAPIView):
    serializer_class = FAQSerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        city_id = self.request.query_params.get("cityId")
        if city_id:
            return FAQ.objects.filter(city_id=city_id).order_by("id")
        return FAQ.objects.none()
