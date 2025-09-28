# hotels/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Activity, ActivityImage, ActivityPackage, ActivityDate
from .serializers import (
    ActivitySerializer,
    ActivityCreateSerializer,
    ActivityImageSerializer,
    ActivityPackageSerializer,
    ActivityPackageCreateSerializer,
    ActivityDateSerializer,
    ActivityDateCreateSerializer,
)
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
import os
from django.conf import settings


# Phân trang
class ActivityPagination(PageNumberPagination):
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
        total_count = Activity.objects.all().count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched activity successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách activity (với phân trang)
class ActivityListView(generics.ListAPIView):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    pagination_class = ActivityPagination
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Activity.objects.all()

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


class ActivityCreateView(generics.CreateAPIView):
    queryset = Activity.objects.all()
    serializer_class = ActivityCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo activity

    def create(self, request, *args, **kwargs):
        # Lấy dữ liệu từ request
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Lưu activity mới
            activity = serializer.save()

            # Kiểm tra xem có ảnh được gửi lên không
            new_images = request.data.get("images", [])
            for image in new_images:
                # Thêm ảnh vào bảng ActivityImage
                ActivityImage.objects.create(hotel=activity, image=image)

            return Response(
                {
                    "isSuccess": True,
                    "message": "Activity created successfully",
                    "data": ActivityCreateSerializer(activity).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create activity",
                "data": serializer.errors,
            },
            status=400,
        )


class ActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết activity.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": "Activity details fetched successfully",
                "data": serializer.data,  # Dữ liệu activity
            }
        )


class ActivityUpdateView(generics.UpdateAPIView):
    queryset = Activity.objects.all()
    serializer_class = ActivityCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa activity

    def update(self, request, *args, **kwargs):
        activity = self.get_object()
        serializer = self.get_serializer(activity, data=request.data, partial=True)

        if serializer.is_valid():
            # Lưu các thay đổi của activity
            updated_activity = serializer.save()

            # Xóa ảnh cũ liên quan đến activity này
            ActivityImage.objects.filter(activity=updated_activity).delete()

            # Kiểm tra xem có ảnh mới không, nếu có thì thêm ảnh mới vào
            new_images = request.data.get("images", [])
            for image in new_images:
                ActivityImage.objects.create(activity=updated_activity, image=image)

            return Response(
                {
                    "isSuccess": True,
                    "message": "Activity updated successfully",
                    "data": ActivityCreateSerializer(updated_activity).data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update activity",
                "data": serializer.errors,
            },
            status=400,
        )


class ActivityDeleteView(generics.DestroyAPIView):
    queryset = Activity.objects.all()
    serializer_class = ActivityCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa activity

    def perform_destroy(self, instance):
        """
        Xóa hẳn activity trong cơ sở dữ liệu.
        """
        instance.delete()  # Xóa activity khỏi cơ sở dữ liệu

        return Response(
            {
                "isSuccess": True,
                "message": "Activity deleted successfully",
                "data": {},
            },
            status=200,  # Trả về mã HTTP 200 khi xóa thành công
        )


class ActivityImageDeleteView(generics.DestroyAPIView):
    queryset = ActivityImage.objects.all()
    serializer_class = ActivityImageSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa ảnh activity

    def perform_destroy(self, instance):
        """
        Xóa hẳn ảnh activity khỏi cơ sở dữ liệu và hệ thống tệp.
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

        instance.delete()  # Xóa ảnh activity khỏi cơ sở dữ liệu

        return Response(
            {
                "isSuccess": True,
                "message": "ActivityImage deleted successfully",
                "data": {},
            },
            status=200,  # Trả về mã HTTP 200 khi xóa thành công
        )


# Phân trang
class ActivityPackagePagination(PageNumberPagination):
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
        total_count = ActivityPackage.objects.all().count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched activity package successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách activity package (với phân trang)
class ActivityPackageListView(generics.ListAPIView):
    queryset = ActivityPackage.objects.all()
    serializer_class = ActivityPackageSerializer
    pagination_class = ActivityPackagePagination
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = ActivityPackage.objects.all()

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


# API GET chi tiết activity package
class ActivityPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ActivityPackage.objects.all()
    serializer_class = ActivityPackageSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết activity package.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": "ActivityPackage details fetched successfully",
                "data": serializer.data,  # Dữ liệu activity package
            }
        )


# API POST tạo activity package
class ActivityPackageCreateView(generics.CreateAPIView):
    queryset = ActivityPackage.objects.all()
    serializer_class = ActivityPackageCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo activity package

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            activity_package = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "ActivityPackage created successfully",
                    "data": ActivityPackageCreateSerializer(activity_package).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create activity package",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật activity package
class ActivityPackageUpdateView(generics.UpdateAPIView):
    queryset = ActivityPackage.objects.all()
    serializer_class = ActivityPackageCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa activity package

    def update(self, request, *args, **kwargs):
        activity_package = self.get_object()
        serializer = self.get_serializer(
            activity_package, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Activity package updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update activity package",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa activity package
class ActivityPackageDeleteView(generics.DestroyAPIView):
    queryset = ActivityPackage.objects.all()
    serializer_class = ActivityPackageCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa activity package

    def perform_destroy(self, instance):
        """
        Xóa hẳn activity package trong cơ sở dữ liệu.
        """
        instance.delete()  # Xóa activity package khỏi cơ sở dữ liệu

        return Response(
            {
                "isSuccess": True,
                "message": "ActivityPackage deleted successfully",
                "data": {},
            },
            status=200,  # Trả về mã HTTP 204 (No Content) khi xóa thành công
        )


# Phân trang
class ActivityDatePagination(PageNumberPagination):
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
        total_count = ActivityDate.objects.all().count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched activity date successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách activity date (với phân trang)
class ActivityDateListView(generics.ListAPIView):
    queryset = ActivityDate.objects.all()
    serializer_class = ActivityDateSerializer
    pagination_class = ActivityDatePagination
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = ActivityDate.objects.all()

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


# API GET chi tiết activity date
class ActivityDateDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ActivityDate.objects.all()
    serializer_class = ActivityDateSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết activity date.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": "ActivityDate details fetched successfully",
                "data": serializer.data,  # Dữ liệu activity date
            }
        )


# API POST tạo activity date
class ActivityDateCreateView(generics.CreateAPIView):
    queryset = ActivityDate.objects.all()
    serializer_class = ActivityDateCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo activity date

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            activity_date = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "ActivityDate created successfully",
                    "data": ActivityDateCreateSerializer(activity_date).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create activity date",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật activity date
class ActivityDateUpdateView(generics.UpdateAPIView):
    queryset = ActivityDate.objects.all()
    serializer_class = ActivityDateCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa activity date

    def update(self, request, *args, **kwargs):
        activity_date = self.get_object()
        serializer = self.get_serializer(activity_date, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Activity date updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update activity date",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa activity date
class ActivityDateDeleteView(generics.DestroyAPIView):
    queryset = ActivityDate.objects.all()
    serializer_class = ActivityDateCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa activity date

    def perform_destroy(self, instance):
        """
        Xóa hẳn activity date trong cơ sở dữ liệu.
        """
        instance.delete()  # Xóa activity date khỏi cơ sở dữ liệu

        return Response(
            {
                "isSuccess": True,
                "message": "ActivityDate deleted successfully",
                "data": {},
            },
            status=200,  # Trả về mã HTTP 204 (No Content) khi xóa thành công
        )
