# countries/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Country
from .serializers import CountrySerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from rest_framework import status


# Phân trang
class CountryPagination(PageNumberPagination):
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
        total_count = Country.objects.all().count()
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


# API GET danh sách quốc gia (với phân trang)
class CountryListView(generics.ListAPIView):
    serializer_class = CountrySerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = CountryPagination

    def get_queryset(self):
        queryset = Country.objects.all()
        filter_params = self.request.query_params
        query_filter = Q()

        for field, value in filter_params.items():
            if field not in ["pageSize", "current"]:
                query_filter &= Q(**{f"{field}__icontains": value})

        return queryset.filter(query_filter).order_by("id")

    def list(self, request, *args, **kwargs):
        """
        Override để cho phép trả về ALL nếu không có pageSize/current
        """
        page_size = request.query_params.get("pageSize")
        current = request.query_params.get("current")

        queryset = self.get_queryset()

        # ⚡ Nếu có tham số phân trang thì dùng DRF pagination
        if page_size or current:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

        # ⚡ Nếu không có pageSize/current thì trả full list
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "isSuccess": True,
            "message": "Fetched all countries successfully!",
            "meta": {
                "totalItems": queryset.count(),
                "pagination": None
            },
            "data": serializer.data,
        })

# API GET chi tiết quốc gia
class CountryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết quốc gia.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "Country details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


# API POST tạo quốc gia
class CountryCreateView(generics.CreateAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo quốc gia

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            country = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Country created successfully",
                    "data": CountrySerializer(country).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create country",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật quốc gia
class CountryUpdateView(generics.UpdateAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa quốc gia

    def update(self, request, *args, **kwargs):
        country = self.get_object()
        serializer = self.get_serializer(country, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Country updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update country",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa quốc gia
class CountryDeleteView(generics.DestroyAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa quốc gia

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Country deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
