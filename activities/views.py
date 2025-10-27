# activities/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import (
    Activity,
    ActivityImage,
    ActivityPackage,
    ActivityDate,
    ActivityDateBookingDetail,
    UserActivityInteraction,
)
from .serializers import (
    ActivitySerializer,
    ActivityDetailSerializer,
    ActivityCreateSerializer,
    ActivityImageSerializer,
    ActivityPackageSerializer,
    ActivityPackageCreateSerializer,
    ActivityDateSerializer,
    ActivityDateCreateSerializer,
    ActivityDateBookingDetailSerializer,
    ActivityDateBookingCreateSerializer,
    UserActivityInteractionSerializer,
    UserActivityInteractionCreateSerializer,
)
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models.functions import Coalesce
from django.db.models import Q, OuterRef, Subquery, Value
from django.db.models import F, FloatField, ExpressionWrapper, functions as Func
from rest_framework.exceptions import AuthenticationFailed, ValidationError, NotFound
from django.db.models import Sum


# Phân trang
class ActivityPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    filters = {}

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")
        city_id = request.query_params.get("city_id")

        if city_id:
            self.filters["city_id"] = city_id

        for field, value in request.query_params.items():
            if field not in [
                "current",
                "pageSize",
                "city_id",
                "recommended",
                "avg_star",
                "min_avg_price",
                "max_avg_price",
                "sort",
                "min_total_time",
                "max_total_time",
            ]:
                # có thể dùng __icontains nếu muốn LIKE, hoặc để nguyên nếu so sánh bằng
                self.filters[f"{field}__icontains"] = value
            if field in ["avg_star"]:
                try:
                    int_value = int(value)
                    self.filters["avg_star__gte"] = int_value
                    self.filters["avg_star__lt"] = int_value + 1
                except ValueError:
                    pass

            if field in ["min_avg_price", "max_avg_price"]:
                min_avg_price = request.query_params.get("min_avg_price")
                max_avg_price = request.query_params.get("max_avg_price")

                if min_avg_price:
                    try:
                        self.filters["avg_price__gte"] = float(min_avg_price)
                    except ValueError:
                        pass

                if max_avg_price:
                    try:
                        self.filters["avg_price__lte"] = float(max_avg_price)
                    except ValueError:
                        pass

            if field in ["min_total_time", "max_total_time"]:
                min_total_time = request.query_params.get("min_total_time")
                max_total_time = request.query_params.get("max_total_time")

                if min_total_time:
                    try:
                        self.filters["total_time__gte"] = float(min_total_time)
                    except ValueError:
                        pass

                if max_total_time:
                    try:
                        self.filters["total_time__lte"] = float(max_total_time)
                    except ValueError:
                        pass

        # Nếu không có hoặc giá trị không hợp lệ, dùng giá trị mặc định
        try:
            self.page_size = int(page_size) if page_size is not None else self.page_size
        except (ValueError, TypeError):
            self.page_size = self.page_size

        try:
            self.currentPage = (
                int(currentPage) if currentPage is not None else self.currentPage
            )
        except (ValueError, TypeError):
            self.currentPage = self.currentPage

        return self.page_size

    def get_paginated_response(self, data):

        total_count = Activity.objects.filter(**self.filters).count()
        total_pages = math.ceil(total_count / self.page_size)

        self.filters.clear()

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
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Activity.objects.all()
        user = self.request.user

        # Lọc dữ liệu theo query params
        filter_params = self.request.query_params
        query_filter = Q()

        # lọc theo city_id (city_id là FK trong model Hotel)
        city_id = filter_params.get("city_id")
        if city_id:
            query_filter &= Q(city_id=city_id)

        for field, value in filter_params.items():
            if field not in [
                "pageSize",
                "current",
                "city_id",
                "recommended",
                "avg_star",
                "min_avg_price",
                "max_avg_price",
                "sort",
                "min_total_time",
                "max_total_time",
            ]:  # Bỏ qua các trường phân trang
                query_filter &= Q(**{f"{field}__icontains": value})

            if field in ["avg_star"]:
                try:
                    int_value = int(value)
                    query_filter &= Q(**{f"{field}__gte": int_value}) & Q(
                        **{f"{field}__lt": int_value + 1}
                    )
                except ValueError:
                    pass  # bỏ qua nếu không phải số hợp lệ

            if field in ["min_avg_price", "max_avg_price"]:
                min_avg_price = filter_params.get("min_avg_price")
                max_avg_price = filter_params.get("max_avg_price")

                if min_avg_price:
                    try:
                        query_filter &= Q(avg_price__gte=float(min_avg_price))
                    except ValueError:
                        pass

                if max_avg_price:
                    try:
                        query_filter &= Q(avg_price__lte=float(max_avg_price))
                    except ValueError:
                        pass

            if field in ["min_total_time", "max_total_time"]:
                min_total_time = filter_params.get("min_total_time")
                max_total_time = filter_params.get("max_total_time")

                if min_total_time:
                    try:
                        query_filter &= Q(total_time__gte=float(min_total_time))
                    except ValueError:
                        pass

                if max_total_time:
                    try:
                        query_filter &= Q(total_time__lte=float(max_total_time))
                    except ValueError:
                        pass

        # Áp dụng lọc cho queryset
        queryset = queryset.filter(query_filter)
        sort_params = filter_params.get("sort")
        order_fields = []

        if sort_params:
            # Ví dụ: sort=avg_price-desc,avg_star-asc
            sort_list = sort_params.split(",")
            for sort_item in sort_list:
                try:
                    field, direction = sort_item.split("-")
                    if direction == "desc":
                        order_fields.append(f"-{field}")
                    else:
                        order_fields.append(field)
                except ValueError:
                    continue  # bỏ qua format không hợp lệ

        # Nếu có recommended thì sắp xếp ưu tiên theo weighted_score trước
        recommended = filter_params.get("recommended")
        if recommended:
            if user and user.is_authenticated:
                user_interaction = UserActivityInteraction.objects.filter(
                    user=user, activity=OuterRef("pk")
                ).values("weighted_score")[:1]

                queryset = queryset.annotate(
                    weighted_score_user=Coalesce(
                        Subquery(user_interaction, output_field=FloatField()),
                        Value(0.0),
                    )
                )

                # Nếu có order_fields thì thêm sau weighted_score_user
                queryset = queryset.order_by(
                    "-weighted_score_user", "-total_weighted_score", *order_fields
                )
            else:
                queryset = queryset.order_by("-total_weighted_score", *order_fields)
        elif order_fields:
            queryset = queryset.order_by(*order_fields)

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
                ActivityImage.objects.create(activity=activity, image=image)

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
    serializer_class = ActivityDetailSerializer
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


class UserActivityInteractionDetailView(generics.RetrieveAPIView):
    serializer_class = UserActivityInteractionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def get_object(self):
        user = self.request.user
        activity_id = self.kwargs.get("activity_id")

        if not user or not user.is_authenticated:
            raise AuthenticationFailed("User not authenticated")

        if not activity_id:
            raise ValidationError("Missing activity_id")

        try:
            return UserActivityInteraction.objects.get(
                user=user, activity_id=activity_id
            )
        except UserActivityInteraction.DoesNotExist:
            raise NotFound("UserActivityInteraction not found")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "UserActivityInteraction details fetched successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserActivityInteractionUpsertView(generics.UpdateAPIView):
    serializer_class = UserActivityInteractionCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        user = request.user
        activity_id = request.data.get("activity_id")

        if not user or not user.is_authenticated:
            return Response(
                {"isSuccess": False, "message": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not activity_id:
            return Response(
                {"isSuccess": False, "message": "Missing activity_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interaction, created = UserActivityInteraction.objects.get_or_create(
            user=user, activity_id=activity_id
        )

        # ✅ Cập nhật hành vi
        interaction.click_count = int(request.data.get("click_count", 0))
        interaction.positive_count = int(request.data.get("positive_count", 0))
        interaction.negative_count = int(request.data.get("negative_count", 0))
        interaction.neutral_count = int(request.data.get("neutral_count", 0))

        # ✅ Cập nhật điểm người dùng
        interaction.update_weighted_score()
        interaction.save()

        # ✅ Cập nhật thống kê tổng của khách sạn
        activity = interaction.activity
        totals = activity.user_activity_interactions.aggregate(
            total_click=Sum("click_count"),
            total_positive=Sum("positive_count"),
            total_negative=Sum("negative_count"),
            total_neutral=Sum("neutral_count"),
        )
        activity.total_click = totals["total_click"] or 0
        activity.total_positive = totals["total_positive"] or 0
        activity.total_negative = totals["total_negative"] or 0
        activity.total_neutral = totals["total_neutral"] or 0

        activity.save()
        activity.update_total_weighted_score()

        serializer = self.get_serializer(interaction)

        return Response(
            {
                "isSuccess": True,
                "message": (
                    "Interaction created successfully!"
                    if created
                    else "Interaction updated successfully!"
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ActivityDeleteView(generics.DestroyAPIView):
    queryset = Activity.objects.all()
    serializer_class = ActivityCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa activity

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Activity deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
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


# API GET danh sách activity package dựa trên activity_id và date_launch (không phân trang)
class ActivityPackageListForActivityAndDateLaunchView(generics.ListAPIView):
    serializer_class = ActivityPackageSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def get_queryset(self):
        queryset = ActivityPackage.objects.all()
        activity_id = self.request.query_params.get("activity_id")
        date_launch = self.request.query_params.get("date_launch")

        if activity_id:
            queryset = queryset.filter(activity_id=activity_id)

        if date_launch:
            queryset = queryset.filter(activities_dates__date_launch=date_launch)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "isSuccess": True,
                "message": (
                    "Get activity package successfully!" if queryset else "No data"
                ),
                "data": serializer.data,
            }
        )


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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "ActivityPackage deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
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


class ActivityDateBulkCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        activity_package_id = request.data.get("activity_package")
        price_adult = request.data.get("price_adult")
        price_child = request.data.get("price_child")
        adult_quantity = request.data.get("adult_quantity")
        child_quantity = request.data.get("child_quantity")
        dates = request.data.get("dates", [])

        if not activity_package_id or not dates:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Missing required fields: activity_package or dates",
                    "data": {},
                },
                status=400,
            )

        created_dates = []
        for date_str in dates:
            activity_date = ActivityDate.objects.create(
                activity_package_id=activity_package_id,
                price_adult=price_adult,
                price_child=price_child,
                adult_quantity=adult_quantity,
                child_quantity=child_quantity,
                date_launch=date_str,  # date_str phải đúng format datetime
            )
            created_dates.append(ActivityDateCreateSerializer(activity_date).data)

        return Response(
            {
                "isSuccess": True,
                "message": f"Created {len(created_dates)} ActivityDate(s) successfully",
                "data": created_dates,
            },
            status=200,
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
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "ActivityDate deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class ActivityDateBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated]  # Bắt buộc user đăng nhập

    def delete(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Invalid or empty 'ids' list",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lấy tất cả các bản ghi cần xóa
        dates_to_delete = ActivityDate.objects.filter(id__in=ids)
        deleted_count = dates_to_delete.count()

        if deleted_count == 0:
            return Response(
                {
                    "isSuccess": False,
                    "message": "No ActivityDate found for given ids",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Xóa các bản ghi
        dates_to_delete.delete()

        return Response(
            {
                "isSuccess": True,
                "message": f"Deleted {deleted_count} ActivityDate(s) successfully",
                "data": {"deleted_ids": ids},
            },
            status=status.HTTP_200_OK,
        )


class ActivityDateBookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ActivityDateBookingDetail.objects.all()
    serializer_class = ActivityDateBookingDetailSerializer
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


class ActivityDateBookingCreateView(generics.CreateAPIView):
    queryset = ActivityDateBookingDetail.objects.all()
    serializer_class = ActivityDateBookingCreateSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def create(self, request, *args, **kwargs):
        # Lấy dữ liệu từ request
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Lưu activity date booking mới
            activity_date_booking = serializer.save()

            return Response(
                {
                    "isSuccess": True,
                    "message": "Activity date booking created successfully",
                    "data": ActivityDateBookingCreateSerializer(
                        activity_date_booking
                    ).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create activity date booking",
                "data": serializer.errors,
            },
            status=400,
        )
