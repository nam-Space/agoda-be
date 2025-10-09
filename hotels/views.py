# hotels/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Hotel, HotelImage
from .serializers import HotelSerializer, HotelCreateSerializer, HotelImageSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import os
from django.conf import settings


# -------------------- Pagination --------------------
class HotelPagination(PageNumberPagination):
    page_size = 10  # default
    page_size_query_param = "pageSize"
    page_query_param = "current"

    def get_paginated_response(self, data):
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched hotels successfully!",
                "meta": {
                    "totalItems": self.page.paginator.count,
                    "currentPage": self.page.number,
                    "itemsPerPage": self.get_page_size(self.request),
                    "totalPages": self.page.paginator.num_pages,
                },
                "data": data,
            }
        )


# -------------------- Hotel List --------------------
class HotelListView(generics.ListAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    pagination_class = HotelPagination
    authentication_classes = []  # bỏ auth
    permission_classes = []  # bỏ permission
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Hotel.objects.all()
        params = self.request.query_params

        # ---- city_id filter ----
        city_id = params.get("cityId")
        if city_id:
            try:
                city_id = int(city_id)
                queryset = queryset.filter(city_id=city_id)
            except ValueError:
                return Hotel.objects.none()

        # ---- other filters ----
        q_filter = Q()
        for field, value in params.items():
            if field not in ["pageSize", "current", "cityId"]:
                # Chỉ filter những field tồn tại trong model
                if field in [f.name for f in Hotel._meta.get_fields()]:
                    q_filter &= Q(**{f"{field}__icontains": value})
        queryset = queryset.filter(q_filter)

        return queryset


# -------------------- Hotel Create --------------------
class HotelCreateView(generics.CreateAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            hotel = serializer.save()
            new_images = request.data.get("images", [])
            for image in new_images:
                HotelImage.objects.create(hotel=hotel, image=image)
            return Response(
                {
                    "isSuccess": True,
                    "message": "Hotel created successfully",
                    "data": HotelCreateSerializer(hotel).data,
                },
                status=200,
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create hotel",
                "data": serializer.errors,
            },
            status=400,
        )


# -------------------- Hotel Detail --------------------
class HotelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    authentication_classes = []
    permission_classes = []

    def retrieve(self, request, *args, **kwargs):
        hotel = self.get_object()
        serializer = self.get_serializer(hotel)
        return Response(
            {
                "isSuccess": True,
                "message": "Hotel details fetched successfully",
                "data": serializer.data,
            }
        )


# -------------------- Hotel Update --------------------
class HotelUpdateView(generics.UpdateAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelCreateSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        hotel = self.get_object()
        serializer = self.get_serializer(hotel, data=request.data, partial=True)
        if serializer.is_valid():
            updated_hotel = serializer.save()
            # xóa ảnh cũ
            HotelImage.objects.filter(hotel=updated_hotel).delete()
            new_images = request.data.get("images", [])
            for image in new_images:
                HotelImage.objects.create(hotel=updated_hotel, image=image)
            return Response(
                {
                    "isSuccess": True,
                    "message": "Hotel updated successfully",
                    "data": HotelCreateSerializer(updated_hotel).data,
                }
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update hotel",
                "data": serializer.errors,
            },
            status=400,
        )


# -------------------- Hotel Delete --------------------
class HotelDeleteView(generics.DestroyAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Hotel deleted successfully",
                "data": {},
            },
            status=200,
        )


# -------------------- Hotel Image Delete --------------------
class HotelImageDeleteView(generics.DestroyAPIView):
    queryset = HotelImage.objects.all()
    serializer_class = HotelImageSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        image_path = instance.image
        if image_path.startswith("/media"):
            image_path = image_path.lstrip("/media")
        full_path = os.path.join(settings.MEDIA_ROOT, image_path.lstrip("/"))
        if os.path.exists(full_path):
            os.remove(full_path)
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "HotelImage deleted successfully",
                "data": {},
            },
            status=200,
        )
