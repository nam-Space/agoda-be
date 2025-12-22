# hotels/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Hotel, HotelImage, UserHotelInteraction
from .serializers import (
    HotelSerializer,
    HotelCreateSerializer,
    HotelImageSerializer,
    UserHotelInteractionSerializer,
    UserHotelInteractionCreateSerializer,
)
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, OuterRef, Subquery, Value
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import os
from django.conf import settings
from django.db.models import F, FloatField, ExpressionWrapper, functions as Func
from rest_framework import status
from django.db.models import Sum
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed, ValidationError, NotFound
from django.db.models.functions import Coalesce
import math
from django.core.paginator import Paginator


# -------------------- Pagination --------------------
class HotelPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    filters = {}

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")
        city_id = request.query_params.get("cityId")
        owner_id = request.query_params.get("ownerId")

        if city_id:
            self.filters["city_id"] = city_id

        if owner_id:
            self.filters["owner_id"] = owner_id

        for field, value in request.query_params.items():
            if field not in [
                "current",
                "pageSize",
                "cityId",
                "ownerId",
                "recommended",
                "avg_star",
                "min_avg_price",
                "max_avg_price",
                "sort",
                "stay_type",
                "adult",
                "child",
                "room",
                "startDate",
                "endDate",
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
                        self.filters["min_price__gte"] = float(min_avg_price)
                    except ValueError:
                        pass

                if max_avg_price:
                    try:
                        self.filters["min_price__lte"] = float(max_avg_price)
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

        total_count = Hotel.objects.filter(**self.filters).count()
        total_pages = math.ceil(total_count / self.page_size)

        self.filters.clear()

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched hotel successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# -------------------- Hotel List --------------------
class HotelListView(generics.ListAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    pagination_class = HotelPagination
    authentication_classes = [JWTAuthentication]  # ✅ cần có để lấy user
    permission_classes = []
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Hotel.objects.all()
        params = self.request.query_params
        user = self.request.user

        # ---- city_id filter ----
        city_id = params.get("cityId")
        if city_id:
            try:
                city_id = int(city_id)
                queryset = queryset.filter(city_id=city_id)
            except ValueError:
                return Hotel.objects.none()

        # ---- stay_type filter ----
        stay_type = params.get("stay_type")
        if stay_type:
            queryset = queryset.filter(rooms__stay_type=stay_type).distinct()

        # ---- capacity filters ----
        adult = params.get("adult")
        if adult:
            try:
                adult = int(adult)
                queryset = queryset.filter(rooms__adults_capacity__gte=adult).distinct()
            except ValueError:
                pass

        child = params.get("child")
        if child:
            try:
                child = int(child)
                queryset = queryset.filter(rooms__children_capacity__gte=child).distinct()
            except ValueError:
                pass

        room = params.get("room")
        if room:
            try:
                room = int(room)
                # Filter hotels có tổng available_rooms >= room (cho tất cả rooms hoặc tổng)
                # Giả sử tổng available_rooms của hotel >= room
                queryset = queryset.annotate(total_available=Sum('rooms__available_rooms')).filter(total_available__gte=room)
            except ValueError:
                pass

        # ---- date filters ----
        startDate = params.get("startDate")
        endDate = params.get("endDate")
        if startDate and endDate:
            try:
                from datetime import datetime
                sd = datetime.strptime(startDate, "%Y-%m-%d").date()
                ed = datetime.strptime(endDate, "%Y-%m-%d").date()
                if sd <= ed:
                    # Filter hotels có rooms available trong khoảng ngày
                    queryset = queryset.filter(
                        rooms__start_date__lte=sd,
                        rooms__end_date__gte=ed
                    ).distinct()
            except ValueError:
                pass

        owner = params.get("ownerId")
        if owner:
            try:
                owner = int(owner)
                queryset = queryset.filter(owner=owner)
            except ValueError:
                return Hotel.objects.none()

        # ---- other filters ----
        q_filter = Q()
        for field, value in params.items():
            if field not in [
                "pageSize",
                "current",
                "cityId",
                "ownerId",
                "recommended",
                "avg_star",
                "min_avg_price",
                "max_avg_price",
                "sort",
                "stay_type",
                "adult",
                "child",
                "room",
                "startDate",
                "endDate",
            ]:
                if field in [f.name for f in Hotel._meta.get_fields()]:
                    q_filter &= Q(**{f"{field}__icontains": value})

            if field in ["avg_star"]:
                try:
                    int_value = int(value)
                    q_filter &= Q(**{f"{field}__gte": int_value}) & Q(
                        **{f"{field}__lt": int_value + 1}
                    )
                except ValueError:
                    pass  # bỏ qua nếu không phải số hợp lệ

            if field in ["min_avg_price", "max_avg_price"]:
                min_avg_price = params.get("min_avg_price")
                max_avg_price = params.get("max_avg_price")

                if min_avg_price:
                    try:
                        q_filter &= Q(min_price__gte=float(min_avg_price))
                    except ValueError:
                        pass

                if max_avg_price:
                    try:
                        q_filter &= Q(min_price__lte=float(max_avg_price))
                    except ValueError:
                        pass

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
                user_interaction = UserHotelInteraction.objects.filter(
                    user=user, hotel=OuterRef("pk")
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


class HotelUpdateViewNotImage(generics.UpdateAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelCreateSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        hotel = self.get_object()
        serializer = self.get_serializer(hotel, data=request.data, partial=True)
        if serializer.is_valid():
            updated_hotel = serializer.save()
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


class UserHotelInteractionDetailView(generics.RetrieveAPIView):
    serializer_class = UserHotelInteractionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def get_object(self):
        user = self.request.user
        hotel_id = self.kwargs.get("hotel_id")

        if not user or not user.is_authenticated:
            raise AuthenticationFailed("User not authenticated")

        if not hotel_id:
            raise ValidationError("Missing hotel_id")

        try:
            return UserHotelInteraction.objects.get(user=user, hotel_id=hotel_id)
        except UserHotelInteraction.DoesNotExist:
            raise NotFound("UserHotelInteraction not found")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "UserHotelInteraction details fetched successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserHotelInteractionUpsertView(generics.UpdateAPIView):
    serializer_class = UserHotelInteractionCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        user = request.user
        hotel_id = request.data.get("hotel_id")

        if not user or not user.is_authenticated:
            return Response(
                {"isSuccess": False, "message": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not hotel_id:
            return Response(
                {"isSuccess": False, "message": "Missing hotel_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interaction, created = UserHotelInteraction.objects.get_or_create(
            user=user, hotel_id=hotel_id
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
        hotel = interaction.hotel
        totals = hotel.user_hotel_interactions.aggregate(
            total_click=Sum("click_count"),
            total_positive=Sum("positive_count"),
            total_negative=Sum("negative_count"),
            total_neutral=Sum("neutral_count"),
        )
        hotel.total_click = totals["total_click"] or 0
        hotel.total_positive = totals["total_positive"] or 0
        hotel.total_negative = totals["total_negative"] or 0
        hotel.total_neutral = totals["total_neutral"] or 0

        hotel.save()
        hotel.update_total_weighted_score()

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


# -------------------- Hotel List by City --------------------
class HotelByCityView(generics.ListAPIView):
    serializer_class = HotelSerializer
    pagination_class = HotelPagination
    authentication_classes = []  # không yêu cầu đăng nhập
    permission_classes = []  # không giới hạn quyền truy cập

    def get_queryset(self):
        city_id = self.kwargs.get("city_id")
        params = self.request.query_params
        user = self.request.user

        if not city_id:
            return Hotel.objects.none()

        try:
            city_id = int(city_id)
        except ValueError:
            return Hotel.objects.none()

        recommended = params.get("recommended")
        if recommended:
            if user and user.is_authenticated:
                # Người dùng đã đăng nhập → sắp xếp theo điểm cá nhân hóa
                return Hotel.objects.filter(city_id=city_id).order_by("-weighted_score")
            else:
                # Người dùng chưa đăng nhập → sắp xếp theo tổng điểm chung
                return Hotel.objects.filter(city_id=city_id).order_by(
                    "-total_weighted_score"
                )

        return Hotel.objects.filter(city_id=city_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


from rest_framework.generics import ListAPIView
from .models import Hotel
from .serializers import HotelSearchSerializer


class HotelSearchPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"
    max_page_size = 50


class HotelSearchView(ListAPIView):
    serializer_class = HotelSearchSerializer
    pagination_class = HotelSearchPagination

    def get_queryset(self):
        queryset = Hotel.objects.all()
        hotel_name = self.request.query_params.get("hotel_name")

        if hotel_name:
            queryset = queryset.filter(name__icontains=hotel_name)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(
            {
                "isSuccess": True,
                "message": "Fetched hotels successfully!",
                "meta": {
                    "totalItems": self.paginator.page.paginator.count,
                    "currentPage": self.paginator.page.number,
                    "itemsPerPage": self.paginator.get_page_size(request),
                    "totalPages": self.paginator.page.paginator.num_pages,
                },
                "data": serializer.data,
            }
        )
