# handbooks/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Handbook, UserHandbookInteraction
from .serializers import (
    HandbookSerializer,
    HandbookCreateSerializer,
    UserHandbookInteractionSerializer,
    UserHandbookInteractionCreateSerializer,
)
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from rest_framework import status
from django.db.models import Q, OuterRef, Subquery, Value
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, OuterRef, Subquery, Value
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, FloatField, ExpressionWrapper, functions as Func
from rest_framework.exceptions import AuthenticationFailed, ValidationError, NotFound


# Phân trang
class HandbookPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    filters = {}

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")
        city_id = request.query_params.get("city_id")
        country_id = request.query_params.get("country_id")
        category = request.query_params.get("category")
        author_id = request.query_params.get("author_id")

        if city_id:
            self.filters["city_id"] = city_id

        if country_id:
            self.filters["city__country_id"] = country_id

        if category:
            self.filters["category"] = category

        if author_id:
            self.filters["author_id"] = author_id

        for field, value in request.query_params.items():
            if field not in [
                "current",
                "pageSize",
                "recommended",
                "sort",
                "city_id",
                "country_id",
                "category",
                "author_id",
            ]:
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

        total_count = Handbook.objects.filter(**self.filters).count()
        total_pages = math.ceil(total_count / self.page_size)

        self.filters.clear()

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched handbook successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách cẩm nang (với phân trang)
class HandbookListView(generics.ListAPIView):
    serializer_class = HandbookSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    pagination_class = HandbookPagination
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Handbook.objects.all()
        params = self.request.query_params
        user = self.request.user

        city_id = params.get("city_id")
        if city_id:
            try:
                city_id = int(city_id)
                queryset = queryset.filter(city_id=city_id)
            except ValueError:
                return Handbook.objects.none()

        country_id = params.get("country_id")
        if country_id:
            try:
                country_id = int(country_id)
                queryset = queryset.filter(city__country_id=country_id)
            except ValueError:
                return Handbook.objects.none()

        category = params.get("category")
        if category:
            try:
                queryset = queryset.filter(category=category)
            except ValueError:
                return Handbook.objects.none()

        author_id = params.get("author_id")
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        # ---- other filters ----
        q_filter = Q()
        for field, value in params.items():
            if field not in [
                "pageSize",
                "current",
                "recommended",
                "sort",
                "city_id",
                "country_id",
                "category",
                "author_id",
            ]:
                if field in [f.name for f in Handbook._meta.get_fields()]:
                    q_filter &= Q(**{f"{field}__icontains": value})

        # Áp dụng lọc cho queryset
        queryset = queryset.filter(q_filter)
        sort_params = params.get("sort")
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

        # ---- Recommended sorting ----
        recommended = params.get("recommended")

        if recommended:
            if user and user.is_authenticated:
                user_interaction = UserHandbookInteraction.objects.filter(
                    user=user, handbook=OuterRef("pk")
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


# API GET chi tiết cẩm nang
class HandbookDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Handbook.objects.all()
    serializer_class = HandbookSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết cẩm nang.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "Handbook details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


# API POST tạo cẩm nang
class HandbookCreateView(generics.CreateAPIView):
    queryset = Handbook.objects.all()
    serializer_class = HandbookCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo cẩm nang

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            handbook = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Handbook created successfully",
                    "data": HandbookCreateSerializer(handbook).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create handbook",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật cẩm nang
class HandbookUpdateView(generics.UpdateAPIView):
    queryset = Handbook.objects.all()
    serializer_class = HandbookCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa cẩm nang

    def update(self, request, *args, **kwargs):
        handbook = self.get_object()
        serializer = self.get_serializer(handbook, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Handbook updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update handbook",
                "data": serializer.errors,
            },
            status=400,
        )


class UserHandbookInteractionDetailView(generics.RetrieveAPIView):
    serializer_class = UserHandbookInteractionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def get_object(self):
        user = self.request.user
        handbook_id = self.kwargs.get("handbook_id")

        if not user or not user.is_authenticated:
            raise AuthenticationFailed("User not authenticated")

        if not handbook_id:
            raise ValidationError("Missing handbook_id")

        try:
            return UserHandbookInteraction.objects.get(
                user=user, handbook_id=handbook_id
            )
        except UserHandbookInteraction.DoesNotExist:
            raise NotFound("UserHandbookInteraction not found")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "UserHandbookInteraction details fetched successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserHandbookInteractionUpsertView(generics.UpdateAPIView):
    serializer_class = UserHandbookInteractionCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        user = request.user
        handbook_id = request.data.get("handbook_id")

        if not user or not user.is_authenticated:
            return Response(
                {"isSuccess": False, "message": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not handbook_id:
            return Response(
                {"isSuccess": False, "message": "Missing handbook_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interaction, created = UserHandbookInteraction.objects.get_or_create(
            user=user, handbook_id=handbook_id
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
        handbook = interaction.handbook
        totals = handbook.user_handbook_interactions.aggregate(
            total_click=Sum("click_count"),
            total_positive=Sum("positive_count"),
            total_negative=Sum("negative_count"),
            total_neutral=Sum("neutral_count"),
        )
        handbook.total_click = totals["total_click"] or 0
        handbook.total_positive = totals["total_positive"] or 0
        handbook.total_negative = totals["total_negative"] or 0
        handbook.total_neutral = totals["total_neutral"] or 0

        handbook.save()
        handbook.update_total_weighted_score()

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


# API DELETE xóa cẩm nang
class HandbookDeleteView(generics.DestroyAPIView):
    queryset = Handbook.objects.all()
    serializer_class = HandbookSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa cẩm nang

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Handbook deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class UserHandbookInteractionDetailView(generics.RetrieveAPIView):
    serializer_class = UserHandbookInteractionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def get_object(self):
        user = self.request.user
        handbook_id = self.kwargs.get("handbook_id")

        if not user or not user.is_authenticated:
            raise AuthenticationFailed("User not authenticated")

        if not handbook_id:
            raise ValidationError("Missing handbook_id")

        try:
            return UserHandbookInteraction.objects.get(
                user=user, handbook_id=handbook_id
            )
        except UserHandbookInteraction.DoesNotExist:
            raise NotFound("UserHandbookInteraction not found")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "UserHandbookInteraction details fetched successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserHandbookInteractionUpsertView(generics.UpdateAPIView):
    serializer_class = UserHandbookInteractionCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        user = request.user
        handbook_id = request.data.get("handbook_id")

        if not user or not user.is_authenticated:
            return Response(
                {"isSuccess": False, "message": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not handbook_id:
            return Response(
                {"isSuccess": False, "message": "Missing handbook_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interaction, created = UserHandbookInteraction.objects.get_or_create(
            user=user, handbook_id=handbook_id
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
        handbook = interaction.handbook
        totals = handbook.user_handbook_interactions.aggregate(
            total_click=Sum("click_count"),
            total_positive=Sum("positive_count"),
            total_negative=Sum("negative_count"),
            total_neutral=Sum("neutral_count"),
        )
        handbook.total_click = totals["total_click"] or 0
        handbook.total_positive = totals["total_positive"] or 0
        handbook.total_negative = totals["total_negative"] or 0
        handbook.total_neutral = totals["total_neutral"] or 0

        handbook.save()
        handbook.update_total_weighted_score()

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
