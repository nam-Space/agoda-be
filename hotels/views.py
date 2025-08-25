# hotels/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Hotel, HotelImage
from .serializers import HotelSerializer, HotelCreateSerializer, HotelImageSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
import os
from django.conf import settings


# Phân trang
class HotelPagination(PageNumberPagination):
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
        total_count = Hotel.objects.all().count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched hotels successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách khách sạn (với phân trang)
class HotelListView(generics.ListAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    pagination_class = HotelPagination
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Hotel.objects.all()

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


class HotelCreateView(generics.CreateAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo khách sạn

    def create(self, request, *args, **kwargs):
        # Lấy dữ liệu từ request
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Lưu khách sạn mới
            hotel = serializer.save()

            # Kiểm tra xem có ảnh được gửi lên không
            new_images = request.data.get("images", [])
            for image in new_images:
                # Thêm ảnh vào bảng HotelImage
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


class HotelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết khách sạn.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": "Hotel details fetched successfully",
                "data": serializer.data,  # Dữ liệu khách sạn
            }
        )


class HotelUpdateView(generics.UpdateAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa khách sạn

    def update(self, request, *args, **kwargs):
        hotel = self.get_object()
        serializer = self.get_serializer(hotel, data=request.data, partial=True)

        if serializer.is_valid():
            # Lưu các thay đổi của khách sạn
            updated_hotel = serializer.save()

            # Xóa ảnh cũ liên quan đến khách sạn này
            HotelImage.objects.filter(hotel=updated_hotel).delete()

            # Kiểm tra xem có ảnh mới không, nếu có thì thêm ảnh mới vào
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


class HotelDeleteView(generics.DestroyAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa khách sạn

    def perform_destroy(self, instance):
        """
        Xóa hẳn khách sạn trong cơ sở dữ liệu.
        """
        instance.delete()  # Xóa khách sạn khỏi cơ sở dữ liệu

        return Response(
            {
                "isSuccess": True,
                "message": "Hotel deleted successfully",
                "data": {},
            },
            status=200,  # Trả về mã HTTP 200 khi xóa thành công
        )


class HotelImageDeleteView(generics.DestroyAPIView):
    queryset = HotelImage.objects.all()
    serializer_class = HotelImageSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa ảnh khách sạn

    def perform_destroy(self, instance):
        """
        Xóa hẳn ảnh khách sạn khỏi cơ sở dữ liệu và hệ thống tệp.
        """
        # Lấy đường dẫn tệp ảnh
        image_path = instance.image

        # Nếu đường dẫn ảnh bắt đầu với "/media", ta loại bỏ nó để tránh trùng lặp
        if image_path.startswith("/media"):
            image_path = image_path.lstrip("/media")

        full_image_path = os.path.join(settings.MEDIA_ROOT, image_path.lstrip("/"))

        # Xóa ảnh khỏi hệ thống tệp (nếu tệp tồn tại)
        if os.path.exists(full_image_path):
            os.remove(full_image_path)

        instance.delete()  # Xóa ảnh khách sạn khỏi cơ sở dữ liệu

        return Response(
            {
                "isSuccess": True,
                "message": "HotelImage deleted successfully",
                "data": {},
            },
            status=200,  # Trả về mã HTTP 200 khi xóa thành công
        )
