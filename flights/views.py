from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.core.paginator import Paginator
import math
from datetime import datetime, timedelta

from .models import Flight, FlightBookingDetail
from .serializers import FlightBookingDetailSerializer, FlightSerializer, FlightDetailSerializer
from airports.serializers import AirportSerializer


# Phân trang
class FlightPagination(PageNumberPagination):
    page_size = 10
    currentPage = 1

    def get_page_size(self, request):
        page_size = request.query_params.get("pageSize", 10)
        currentPage = request.query_params.get("current", 1)
        self.page_size = int(page_size)
        self.currentPage = int(currentPage)
        return self.page_size

    def get_paginated_response(self, data):
        total_count = self.page.paginator.count
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched flights successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.all().select_related('origin__city', 'destination__city')
    serializer_class = FlightSerializer
    pagination_class = FlightPagination
    authentication_classes = []
    permission_classes = []

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FlightDetailSerializer
        return FlightSerializer

    def get_queryset(self):
        queryset = Flight.objects.all().select_related('origin__city', 'destination__city')
        
        # Search params
        origin_id = self.request.query_params.get('origin_id')
        destination_id = self.request.query_params.get('destination_id')
        departure_date = self.request.query_params.get('departure_date')
        return_date = self.request.query_params.get('return_date')
        passengers = self.request.query_params.get('passengers')
        seat_class = self.request.query_params.get('seat_class')
        
        # Filter by origin
        if origin_id:
            queryset = queryset.filter(origin_id=origin_id)
        
        # Filter by destination
        if destination_id:
            queryset = queryset.filter(destination_id=destination_id)
        
        # Filter by departure date
        if departure_date:
            try:
                date_obj = datetime.strptime(departure_date, '%Y-%m-%d').date()
                queryset = queryset.filter(departure_datetime__date=date_obj)
            except ValueError:
                pass
        
        # Filter by passengers (seat capacity)
        if passengers:
            queryset = queryset.filter(seat_capacity__gte=int(passengers))
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', 'price')
        sort_order = self.request.query_params.get('sort_order', 'asc')
        
        if sort_by == 'price':
            queryset = queryset.order_by('price' if sort_order == 'asc' else '-price')
        elif sort_by == 'departure_time':
            queryset = queryset.order_by('departure_datetime' if sort_order == 'asc' else '-departure_datetime')
        elif sort_by == 'duration':
            # Calculate duration and sort (simplified)
            queryset = queryset.order_by('arrival_datetime' if sort_order == 'asc' else '-arrival_datetime')
        
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search flights with filters
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "isSuccess": True,
            "message": "Flights found",
            "data": serializer.data
        })


class FlightBookingDetailViewSet(viewsets.ModelViewSet):
    queryset = FlightBookingDetail.objects.all()
    serializer_class = FlightBookingDetailSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            booking_detail = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Flight booking created successfully",
                    "data": FlightBookingDetailSerializer(booking_detail).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create flight booking",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
