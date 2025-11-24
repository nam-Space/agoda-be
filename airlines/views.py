from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
from .models import Airline, Aircraft
from .serializers import AirlineSerializer, AircraftSerializer
from rest_framework.response import Response
from rest_framework import status

# Phân trang chung cho Airline và Aircraft
class CommonPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "isSuccess": True,
            "message": self.context.get('message', "Fetched data successfully!"),
            "meta": {
                "totalItems": self.page.paginator.count,
                "currentPage": self.page.number,
                "itemsPerPage": self.get_page_size(self.request),
                "totalPages": self.page.paginator.num_pages,
            },
            "data": data,
        })

class AirlineListView(generics.ListCreateAPIView):
    serializer_class = AirlineSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = CommonPagination

    def get_queryset(self):
        return Airline.objects.all().order_by('-id')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Truyền message vào context để phân trang trả về đúng message
            self.paginator.context = {'message': "Fetched all airlines successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "isSuccess": True,
            "message": "Fetched all airlines successfully!",
            "meta": {
                "totalItems": queryset.count(),
                "pagination": None
            },
            "data": serializer.data,
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            airline = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Airline created successfully",
                    "data": AirlineSerializer(airline).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create airline",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class AirlineDetailView(generics.RetrieveAPIView):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer
    authentication_classes = []
    permission_classes = []

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Airline details fetched successfully",
                "data": serializer.data,
            }
        )



class AircraftListView(generics.ListCreateAPIView):
    serializer_class = AircraftSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = CommonPagination

    def get_queryset(self):
        queryset = Aircraft.objects.select_related('airline').all().order_by('-created_at')
        airline_id = self.request.query_params.get('airline_id')
        if airline_id:
            queryset = queryset.filter(airline_id=airline_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            self.paginator.context = {'message': "Fetched all aircrafts successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "isSuccess": True,
            "message": "Fetched all aircrafts successfully!",
            "meta": {
                "totalItems": queryset.count(),
                "pagination": None
            },
            "data": serializer.data,
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            aircraft = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Aircraft created successfully",
                    "data": AircraftSerializer(aircraft).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create aircraft",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class AircraftDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Aircraft.objects.select_related('airline').all()
    serializer_class = AircraftSerializer
    authentication_classes = []
    permission_classes = []

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Aircraft details fetched successfully",
                "data": serializer.data,
            }
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Aircraft updated successfully",
                    "data": serializer.data,
                }
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update aircraft",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Aircraft deleted successfully",
            },
            status=status.HTTP_204_NO_CONTENT,
        )
