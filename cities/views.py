# cities/views.py
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import City
from .serializers import CitySerializer, CityCreateSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from bookings.models import Booking
from bookings.constants.booking_status import BookingStatus
from rest_framework import status


# Phân trang
class CityPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1

    def get_page_size(self, request):
        self.page_size = int(request.query_params.get("pageSize", 10))
        self.currentPage = int(request.query_params.get("current", 1))
        return self.page_size

    def get_paginated_response(self, data):
        total_count = City.objects.all().count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched cities successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách thành phố (với phân trang)
class CityListView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    pagination_class = CityPagination
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = City.objects.all()

        country_id = self.request.query_params.get("country_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)

        # Lọc dữ liệu theo query params
        filter_params = self.request.query_params
        query_filter = Q()

        for field, value in filter_params.items():
            if field not in ["pageSize", "current", "country_id"]:  # Bỏ qua các trường phân trang
                query_filter &= Q(**{f"{field}__icontains": value})

        # Áp dụng lọc cho queryset
        queryset = queryset.filter(query_filter)

        # Lấy tham số 'current' từ query string để tính toán trang
        current = self.request.query_params.get(
            "current", 1
        )  # Trang hiện tại, mặc định là trang 1
        page_size = self.request.query_params.get(
            "pageSize", 10
        )  # Số phần tử mỗi trang, mặc định là 10

        # Áp dụng phân trang
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(current)

        return page


# API GET chi tiết thành phố
class CityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết thành phố.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": "City details fetched successfully",
                "data": serializer.data,  # Dữ liệu thành phố
            }
        )


# API POST tạo thành phố
class CityCreateView(generics.CreateAPIView):
    queryset = City.objects.all()
    serializer_class = CityCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo thành phố

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            city = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "City created successfully",
                    "data": CityCreateSerializer(city).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create city",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật thành phố
class CityUpdateView(generics.UpdateAPIView):
    queryset = City.objects.all()
    serializer_class = CityCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa thành phố

    def update(self, request, *args, **kwargs):
        city = self.get_object()
        serializer = self.get_serializer(city, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "City updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update city",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa thành phố
class CityDeleteView(generics.DestroyAPIView):
    queryset = City.objects.all()
    serializer_class = CityCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa thành phố

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "City deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


# API: Các điểm đến thu hút nhất Việt Nam
class TopVietnamCitiesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        limit_param = request.query_params.get("limit", 10)
        try:
            limit = int(limit_param)
        except (TypeError, ValueError):
            limit = 10

        # Chấp nhận cả tên "Vietnam" và "Việt Nam"
        vietnam_filter = Q(country__name__iexact="Vietnam") | Q(
            country__name__iexact="Việt Nam"
        )

        # Tính điểm thu hút dựa trên số booking (đã xác nhận hoặc hoàn tất)
        cities = (
            City.objects.filter(vietnam_filter)
            .annotate(
                booking_count=Count(
                    "hotels__rooms__room_bookings__booking",
                    filter=Q(
                        hotels__rooms__room_bookings__booking__status__in=[
                            BookingStatus.CONFIRMED,
                            BookingStatus.COMPLETED,
                        ]
                    ),
                    distinct=True,
                ),
                hotel_count=Count("hotels", distinct=True),
            )
            .order_by("-booking_count", "-created_at")[:limit]
        )

        # Trả về kèm theo chỉ số booking_count
        data = [
            {
                **CitySerializer(city).data,
                "bookingCount": getattr(city, "booking_count", 0),
                "hotelCount": getattr(city, "hotel_count", 0),
            }
            for city in cities
        ]

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched top destinations in Vietnam",
                "meta": {"limit": limit},
                "data": data,
            }
        )


# API: Các điểm đến nổi tiếng ngoài Việt Nam
class TopAbroadCitiesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        limit_param = request.query_params.get("limit", 10)
        try:
            limit = int(limit_param)
        except (TypeError, ValueError):
            limit = 10

        vietnam_filter = Q(country__name__iexact="Vietnam") | Q(
            country__name__iexact="Việt Nam"
        )

        cities = (
            City.objects.exclude(vietnam_filter)
            .annotate(
                booking_count=Count(
                    "hotels__rooms__room_bookings__booking",
                    filter=Q(
                        hotels__rooms__room_bookings__booking__status__in=[
                            BookingStatus.CONFIRMED,
                            BookingStatus.COMPLETED,
                        ]
                    ),
                    distinct=True,
                ),
                hotel_count=Count("hotels", distinct=True),
            )
            .order_by("-booking_count", "-created_at")[:limit]
        )

        data = [
            {
                **CitySerializer(city).data,
                "bookingCount": getattr(city, "booking_count", 0),
                "hotelCount": getattr(city, "hotel_count", 0),
            }
            for city in cities
        ]

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched famous destinations outside Vietnam",
                "meta": {"limit": limit},
                "data": data,
            }
        )
