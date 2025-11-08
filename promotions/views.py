from rest_framework import generics, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Promotion, HotelPromotion, FlightPromotion
from .serializers import (
    PromotionSerializer,
    HotelPromotionSerializer,
    FlightPromotionSerializer,
)
from django.utils import timezone

# class PromotionViewSet(viewsets.ModelViewSet):
#     queryset = Promotion.objects.prefetch_related(
#         "hotel_promotions__hotel",
#         "flight_promotions__airport",
#     ).all()
#     serializer_class = PromotionSerializer
#     parser_classes = [MultiPartParser, FormParser]


# Promotion
class PromotionListCreateView(generics.ListCreateAPIView):
    serializer_class = PromotionSerializer

    def get_queryset(self):
        now = timezone.now()
        queryset = Promotion.objects.prefetch_related(
            "hotel_promotions__hotel",
            "flight_promotions__airport",
        ).filter(end_date__gte=now) 
        queryset = queryset.order_by("-created_at")
        
        promotion_type = self.request.query_params.get("promotion_type")
        if promotion_type:
            queryset = queryset.filter(promotion_type=promotion_type)
        return queryset


class PromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Promotion.objects.prefetch_related(
            "hotel_promotions__hotel",
            "flight_promotions__airport",
        ).all()

    serializer_class = PromotionSerializer
    def get_serializer_context(self):
        context = super().get_serializer_context()
        request = self.request

        context["city_id"] = request.query_params.get("city_id")
        # context["active_only"] = request.query_params.get("active_only", "true").lower() == "true"
        context["min_rating"] = request.query_params.get("min_rating")
        context["min_price"] = request.query_params.get("min_price")

        return context


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
