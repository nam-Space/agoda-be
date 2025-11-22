from rest_framework import generics
from .models import Airline, Aircraft
from .serializers import AirlineSerializer, AircraftSerializer
from rest_framework.response import Response
from rest_framework import status


class AirlineListView(generics.ListCreateAPIView):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer
    authentication_classes = []
    permission_classes = []

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all airlines successfully!",
                "meta": {
                    "totalItems": queryset.count(),
                    "pagination": None
                },
                "data": serializer.data,
            }
        )

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
    queryset = Aircraft.objects.select_related('airline').all()
    serializer_class = AircraftSerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        queryset = super().get_queryset()
        airline_id = self.request.query_params.get('airline_id')
        if airline_id:
            queryset = queryset.filter(airline_id=airline_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all aircrafts successfully!",
                "meta": {
                    "totalItems": queryset.count(),
                    "pagination": None
                },
                "data": serializer.data,
            }
        )

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
