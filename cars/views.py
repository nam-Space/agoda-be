# cars/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Car, CarBookingDetail, UserCarInteraction
from .serializers import (
    CarSerializer,
    CarCreateSerializer,
    CarBookingDetailSerializer,
    UserCarInteractionSerializer,
    UserCarInteractionCreateSerializer,
)
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed, ValidationError, NotFound
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.db.models import Q, OuterRef, Subquery, Value
from django.db.models import Avg, F, FloatField, ExpressionWrapper, functions as Func


# Phân trang
class CarPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    filters = {}

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")
        user_id = request.query_params.get("user_id")

        if user_id:
            self.filters["user_id"] = user_id

        for field, value in request.query_params.items():
            if field not in ["current", "pageSize", "user_id", "recommended", "sort"]:
                # có thể dùng __icontains nếu muốn LIKE, hoặc để nguyên nếu so sánh bằng
                self.filters[f"{field}__icontains"] = value

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
        total_count = Car.objects.filter(**self.filters).count()
        total_pages = math.ceil(total_count / self.page_size)

        self.filters.clear()

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
        user = self.request.user

        # Lọc dữ liệu theo query params
        filter_params = self.request.query_params

        user_id = filter_params.get("user_id")
        if user_id:
            try:
                user_id = int(user_id)
                queryset = queryset.filter(user_id=user_id)
            except ValueError:
                return Car.objects.none()

        query_filter = Q()

        for field, value in filter_params.items():
            if field not in [
                "pageSize",
                "current",
                "user_id",
                "recommended",
                "sort",
            ]:  # Bỏ qua các trường phân trang
                query_filter &= Q(**{f"{field}__icontains": value})

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
                user_interaction = UserCarInteraction.objects.filter(
                    user=user, car=OuterRef("pk")
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


class CarBookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CarBookingDetail.objects.all()
    serializer_class = CarBookingDetailSerializer
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
                "message": "Car booking details fetched successfully",
                "data": serializer.data,  # Dữ liệu xe đặt
            }
        )


class UserCarInteractionDetailView(generics.RetrieveAPIView):
    serializer_class = UserCarInteractionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def get_object(self):
        user = self.request.user
        car_id = self.kwargs.get("car_id")

        if not user or not user.is_authenticated:
            raise AuthenticationFailed("User not authenticated")

        if not car_id:
            raise ValidationError("Missing car_id")

        try:
            return UserCarInteraction.objects.get(user=user, car_id=car_id)
        except UserCarInteraction.DoesNotExist:
            raise NotFound("UserCarInteraction not found")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "UserCarInteraction details fetched successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserCarInteractionUpsertView(generics.UpdateAPIView):
    serializer_class = UserCarInteractionCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        user = request.user
        car_id = request.data.get("car_id")

        if not user or not user.is_authenticated:
            return Response(
                {"isSuccess": False, "message": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not car_id:
            return Response(
                {"isSuccess": False, "message": "Missing car_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interaction, created = UserCarInteraction.objects.get_or_create(
            user=user, car_id=car_id
        )

        # ✅ Cập nhật hành vi
        interaction.booking_count = int(request.data.get("booking_count", 0))

        # ✅ Cập nhật điểm người dùng
        interaction.update_weighted_score()
        interaction.save()

        # ✅ Cập nhật thống kê tổng của khách sạn
        car = interaction.car
        totals = car.user_car_interactions.aggregate(
            total_booking_count=Sum("booking_count"),
        )
        car.total_booking_count = totals["total_booking_count"] or 0

        car.save()
        car.update_total_weighted_score()

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
