from rest_framework import generics, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Promotion, HotelPromotion, FlightPromotion
from .serializers import PromotionSerializer, HotelPromotionSerializer, FlightPromotionSerializer

class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    parser_classes = [MultiPartParser, FormParser] 

# Promotion
class PromotionListCreateView(generics.ListCreateAPIView):
    serializer_class = PromotionSerializer
    def get_queryset(self):
        queryset = Promotion.objects.all().order_by("-created_at")
        promotion_type = self.request.query_params.get("promotion_type")
        if promotion_type:
            queryset = queryset.filter(promotion_type=promotion_type)
        return queryset

class PromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer


# HotelPromotion
class HotelPromotionListCreateView(generics.ListCreateAPIView):
    queryset = HotelPromotion.objects.all()
    serializer_class = HotelPromotionSerializer

class HotelPromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = HotelPromotion.objects.all()
    serializer_class = HotelPromotionSerializer


# FlightPromotion
class FlightPromotionListCreateView(generics.ListCreateAPIView):
    queryset = FlightPromotion.objects.all()
    serializer_class = FlightPromotionSerializer

class FlightPromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FlightPromotion.objects.all()
    serializer_class = FlightPromotionSerializer
