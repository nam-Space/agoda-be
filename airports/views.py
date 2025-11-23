# countries/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Airport
from .serializers import AirportSerializer, AirportCreateSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from rest_framework import status


# Phân trang
class AirportPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize", "10")
        currentPage = request.query_params.get("current", "1")

        # Nếu không có hoặc giá trị không hợp lệ, dùng giá trị mặc định
        try:
            self.page_size = int(page_size)
        except (ValueError, TypeError):
            self.page_size = 10
        
        try:
            self.currentPage = int(currentPage)
        except (ValueError, TypeError):
            self.currentPage = 1
            
        return self.page_size

    def get_paginated_response(self, data):
        total_count = Airport.objects.all().count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched airport successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách sân bay (với phân trang)
class AirportListView(generics.ListAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def get_paginated_response(self, data):
        # Custom response khi có phân trang
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched airports successfully!",
                "meta": self.paginator.get_paginated_response_meta(data) if hasattr(self, 'paginator') else None,
                "data": data,
            }
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Nếu không truyền current hoặc pageSize thì trả về tất cả
        has_pagination = request.query_params.get("current") or request.query_params.get("pageSize")
        
        if not has_pagination:
            # Không phân trang, trả về tất cả
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "isSuccess": True,
                    "message": "Fetched all airports successfully!",
                    "meta": {
                        "totalItems": queryset.count(),
                        "pagination": None
                    },
                    "data": serializer.data,
                }
            )
        
        # Có phân trang
        self.pagination_class = AirportPagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        queryset = Airport.objects.all()

        # Lọc dữ liệu theo query params
        filter_params = self.request.query_params
        query_filter = Q()

        for field, value in filter_params.items():
            if field not in ["pageSize", "current"]:
                query_filter &= Q(**{f"{field}__icontains": value})

        # Áp dụng lọc cho queryset
        queryset = queryset.filter(query_filter)
        
        return queryset


# API GET chi tiết sân bay
class AirportDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết sân bay.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "Airport details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


# API POST tạo sân bay
class AirportCreateView(generics.CreateAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo sân bay

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            airport = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Airport created successfully",
                    "data": AirportCreateSerializer(airport).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create airport",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật sân bay
class AirportUpdateView(generics.UpdateAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa sân bay

    def update(self, request, *args, **kwargs):
        airport = self.get_object()
        serializer = self.get_serializer(airport, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Airport updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update airport",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa sân bay
class AirportDeleteView(generics.DestroyAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa sân bay

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Airport deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
