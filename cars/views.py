# cars/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Car
from .serializers import CarSerializer, CarCreateSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status


# Phân trang
class CarPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")

        # Nếu không có hoặc giá trị không hợp lệ, dùng giá trị mặc định
        self.page_size = int(page_size)
        self.currentPage = int(currentPage)
        return self.page_size

    def get_paginated_response(self, data):
        total_count = Car.objects.all().count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched cars successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách xe (với phân trang)
class CarListView(generics.ListAPIView):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    pagination_class = CarPagination
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Car.objects.all()

        # Lọc dữ liệu theo query params
        filter_params = self.request.query_params
        query_filter = Q()

        for field, value in filter_params.items():
            if field not in ["pageSize", "current"]:  # Bỏ qua các trường phân trang
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


# API GET chi tiết xe
class CarDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết xe.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": "Car details fetched successfully",
                "data": serializer.data,  # Dữ liệu xe
            }
        )


# API POST tạo xe
class CarCreateView(generics.CreateAPIView):
    queryset = Car.objects.all()
    serializer_class = CarCreateSerializer
    permission_classes = [
        # IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo xe

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            car = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Car created successfully",
                    "data": CarCreateSerializer(car).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create car",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật xe
class CarUpdateView(generics.UpdateAPIView):
    queryset = Car.objects.all()
    serializer_class = CarCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa xe

    def update(self, request, *args, **kwargs):
        car = self.get_object()
        serializer = self.get_serializer(car, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Car updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update car",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa xe
class CarDeleteView(generics.DestroyAPIView):
    queryset = Car.objects.all()
    serializer_class = CarCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa xe

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Car deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
