from .models import Review
from .serializers import ReviewSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.core.paginator import Paginator
from rest_framework import status
from transformers import pipeline
from bookings.models import ServiceType
from hotels.models import Hotel, UserHotelInteraction
from activities.models import Activity, UserActivityInteraction
from django.db.models import Avg, Count
from django.db import transaction
from handbooks.models import Handbook, UserHandbookInteraction

# Khởi tạo mô hình sentiment-analysis chỉ một lần
_model_path = "5CD-AI/Vietnamese-Sentiment-visobert"
_sentiment_analyzer = pipeline(
    "sentiment-analysis", model=_model_path, tokenizer=_model_path
)


# Phân trang
class ReviewPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    filters = {}

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")
        service_type = request.query_params.get("service_type")
        service_ref_id = request.query_params.get("service_ref_id")

        if service_type:
            self.filters["service_type"] = service_type

        if service_ref_id:
            self.filters["service_ref_id"] = service_ref_id

        for field, value in request.query_params.items():
            if field not in ["current", "pageSize", "service_type", "service_ref_id"]:
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

        total_count = Review.objects.filter(**self.filters).count()
        total_pages = math.ceil(total_count / self.page_size)

        self.filters.clear()

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched reviews successfully!",
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
class ReviewListView(generics.ListAPIView):
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    pagination_class = ReviewPagination
    authentication_classes = []  # ✅ cần có để lấy user
    permission_classes = []  # Không cần kiểm tra quyền
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Review.objects.all().order_by("-created_at")

        # Lọc dữ liệu theo query params
        filter_params = self.request.query_params
        query_filter = Q()

        # lọc theo service_type (service_type là FK trong model Hotel)
        service_type = filter_params.get("service_type")
        if service_type:
            query_filter &= Q(service_type=service_type)

        service_ref_id = filter_params.get("service_ref_id")
        if service_ref_id:
            query_filter &= Q(service_ref_id=service_ref_id)

        for field, value in filter_params.items():
            if field not in [
                "pageSize",
                "current",
                "service_type",
                "service_ref_id",
            ]:  # Bỏ qua các trường phân trang
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


class ReviewCreateView(generics.CreateAPIView):
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(user=request.user)

        # Nếu có comment thì phân tích cảm xúc
        if review.comment and review.comment.strip():
            result = _sentiment_analyzer(review.comment)[0]
            label = result["label"]
            score = float(result["score"])

            # Map nhãn model sang dạng bạn muốn lưu
            if label == "POS":
                sentiment = "positive"
            elif label == "NEG":
                sentiment = "negative"
            else:
                sentiment = "neutral"

            # Gán vào bản ghi review
            review.sentiment = sentiment
            review.confidence = score
            review.save(update_fields=["sentiment", "confidence"])

        # =========================
        # 🔹 CẬP NHẬT THỐNG KÊ
        # =========================
        service_type = getattr(review, "service_type", None)
        service_ref_id = getattr(review, "service_ref_id", None)

        if not service_type or not service_ref_id:
            return Response(
                {"isSuccess": False, "message": "Invalid service type or ref id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Hàm phụ để cập nhật thống kê
        def update_service_stats(model, type_value):
            instance = model.objects.filter(id=service_ref_id).first()
            if not instance:
                return

            reviews = Review.objects.filter(
                service_type=type_value, service_ref_id=instance.id
            )

            # Tổng hợp dữ liệu
            stats = reviews.aggregate(
                avg_star=Avg("rating"),
                review_count=Count("id"),
                total_positive=Count("id", filter=Q(sentiment="positive")),
                total_negative=Count("id", filter=Q(sentiment="negative")),
                total_neutral=Count("id", filter=Q(sentiment="neutral")),
            )

            # Cập nhật giá trị vào model
            instance.avg_star = stats["avg_star"] or 0
            instance.review_count = stats["review_count"] or 0
            instance.total_positive = stats["total_positive"] or 0
            instance.total_negative = stats["total_negative"] or 0
            instance.total_neutral = stats["total_neutral"] or 0

            instance.save(
                update_fields=[
                    "avg_star",
                    "review_count",
                    "total_positive",
                    "total_negative",
                    "total_neutral",
                ]
            )

            # ✅ Tự động cập nhật weighted_score
            instance.update_total_weighted_score()
            return instance

        # =========================
        # 🔹 GỌI CẬP NHẬT TƯƠNG ỨNG
        # =========================
        if service_type == ServiceType.HOTEL:
            hotel = update_service_stats(Hotel, ServiceType.HOTEL)

            # ✅ Cập nhật hoặc tạo UserHotelInteraction tương ứng
            if hotel:
                interaction, _ = UserHotelInteraction.objects.get_or_create(
                    user=request.user, hotel=hotel
                )

                if review.sentiment == "positive":
                    interaction.positive_count += 1
                elif review.sentiment == "negative":
                    interaction.negative_count += 1
                else:
                    interaction.neutral_count += 1

                # Cập nhật điểm trọng số cá nhân
                interaction.update_weighted_score()
                interaction.save()
        elif service_type == ServiceType.ACTIVITY:
            activity = update_service_stats(Activity, ServiceType.ACTIVITY)

            # ✅ Cập nhật hoặc tạo UserActivityInteraction tương ứng
            if activity:
                interaction, _ = UserActivityInteraction.objects.get_or_create(
                    user=request.user, activity=activity
                )

                if review.sentiment == "positive":
                    interaction.positive_count += 1
                elif review.sentiment == "negative":
                    interaction.negative_count += 1
                else:
                    interaction.neutral_count += 1

                # Cập nhật điểm trọng số cá nhân
                interaction.update_weighted_score()
                interaction.save()

        elif service_type == ServiceType.HANDBOOK:
            handbook = update_service_stats(Handbook, ServiceType.HANDBOOK)

            # ✅ Cập nhật hoặc tạo UserHandbookInteraction tương ứng
            if handbook:
                interaction, _ = UserHandbookInteraction.objects.get_or_create(
                    user=request.user, handbook=handbook
                )

                if review.sentiment == "positive":
                    interaction.positive_count += 1
                elif review.sentiment == "negative":
                    interaction.negative_count += 1
                else:
                    interaction.neutral_count += 1

                # Cập nhật điểm trọng số cá nhân
                interaction.update_weighted_score()
                interaction.save()

        # =========================
        # 🔹 TRẢ VỀ KẾT QUẢ
        # =========================
        return Response(
            {
                "isSuccess": True,
                "message": "Review created successfully",
                "data": ReviewSerializer(
                    review, context=self.get_serializer_context()
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết review.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": "Review details fetched successfully",
                "data": serializer.data,  # Dữ liệu review
            }
        )


class ReviewUpdateView(generics.UpdateAPIView):
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    # =========================
    # 🔹 Hàm phụ cập nhật thống kê
    # =========================
    def update_service_stats(self, model, type_value, ref_id):
        instance = model.objects.filter(id=ref_id).first()
        if not instance:
            return None

        reviews = Review.objects.filter(service_type=type_value, service_ref_id=ref_id)

        stats = reviews.aggregate(
            avg_star=Avg("rating"),
            review_count=Count("id"),
            total_positive=Count("id", filter=Q(sentiment="positive")),
            total_negative=Count("id", filter=Q(sentiment="negative")),
            total_neutral=Count("id", filter=Q(sentiment="neutral")),
        )

        instance.avg_star = stats["avg_star"] or 0
        instance.review_count = stats["review_count"] or 0
        instance.total_positive = stats["total_positive"] or 0
        instance.total_negative = stats["total_negative"] or 0
        instance.total_neutral = stats["total_neutral"] or 0
        instance.save(
            update_fields=[
                "avg_star",
                "review_count",
                "total_positive",
                "total_negative",
                "total_neutral",
            ]
        )

        # ✅ Cập nhật điểm trọng số tổng thể
        instance.update_total_weighted_score()
        return instance

    # =========================
    # 🔹 Hàm phụ cập nhật interaction
    # =========================
    def update_interaction(self, interaction, sentiment):
        interaction.positive_count = Review.objects.filter(
            user=interaction.user,
            sentiment="positive",
            service_ref_id=getattr(
                interaction,
                "hotel_id",
                getattr(
                    interaction,
                    "activity_id",
                    getattr(interaction, "handbook_id", None),
                ),
            ),
        ).count()

        interaction.negative_count = Review.objects.filter(
            user=interaction.user,
            sentiment="negative",
            service_ref_id=getattr(
                interaction,
                "hotel_id",
                getattr(
                    interaction,
                    "activity_id",
                    getattr(interaction, "handbook_id", None),
                ),
            ),
        ).count()

        interaction.neutral_count = Review.objects.filter(
            user=interaction.user,
            sentiment="neutral",
            service_ref_id=getattr(
                interaction,
                "hotel_id",
                getattr(
                    interaction,
                    "activity_id",
                    getattr(interaction, "handbook_id", None),
                ),
            ),
        ).count()

        interaction.update_weighted_score()
        interaction.save()

    # =========================
    # 🔹 Update chính
    # =========================
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        review = self.get_object()
        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_review = serializer.save()

        # =========================
        # 🔹 PHÂN TÍCH CẢM XÚC MỚI
        # =========================
        if updated_review.comment and updated_review.comment.strip():
            result = _sentiment_analyzer(updated_review.comment)[0]
            label = result["label"]
            score = round(float(result["score"]), 4)

            if label == "POS":
                sentiment = "positive"
            elif label == "NEG":
                sentiment = "negative"
            else:
                sentiment = "neutral"

            updated_review.sentiment = sentiment
            updated_review.confidence = score
            updated_review.save(update_fields=["sentiment", "confidence"])

        # =========================
        # 🔹 CẬP NHẬT THỐNG KÊ VÀ INTERACTION
        # =========================
        service_type = getattr(updated_review, "service_type", None)
        ref_id = getattr(updated_review, "service_ref_id", None)

        if service_type == ServiceType.HOTEL:
            hotel = self.update_service_stats(Hotel, ServiceType.HOTEL, ref_id)
            if hotel:
                interaction, _ = UserHotelInteraction.objects.get_or_create(
                    user=request.user, hotel=hotel
                )
                self.update_interaction(interaction, updated_review.sentiment)

        elif service_type == ServiceType.ACTIVITY:
            activity = self.update_service_stats(Activity, ServiceType.ACTIVITY, ref_id)
            if activity:
                interaction, _ = UserActivityInteraction.objects.get_or_create(
                    user=request.user, activity=activity
                )
                self.update_interaction(interaction, updated_review.sentiment)

        elif service_type == ServiceType.HANDBOOK:  # ✅ thêm case này
            handbook = self.update_service_stats(Handbook, ServiceType.HANDBOOK, ref_id)
            if handbook:
                interaction, _ = UserHandbookInteraction.objects.get_or_create(
                    user=request.user, handbook=handbook
                )
                self.update_interaction(interaction, updated_review.sentiment)

        # =========================
        # 🔹 TRẢ KẾT QUẢ
        # =========================
        return Response(
            {
                "isSuccess": True,
                "message": "Review updated successfully",
                "data": ReviewSerializer(
                    updated_review, context=self.get_serializer_context()
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class ReviewDeleteView(generics.DestroyAPIView):
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        service_type = instance.service_type
        ref_id = instance.service_ref_id
        user = request.user

        # Lưu lại sentiment trước khi xóa để cập nhật Interaction
        old_sentiment = instance.sentiment

        # Xóa review
        self.perform_destroy(instance)

        # =========================
        # 🔹 HÀM CẬP NHẬT THỐNG KÊ
        # =========================
        def update_service_stats(model, type_value, ref_id):
            service = model.objects.filter(id=ref_id).first()
            if not service:
                return None

            reviews = Review.objects.filter(
                service_type=type_value, service_ref_id=ref_id
            )

            stats = reviews.aggregate(
                avg_star=Avg("rating"),
                review_count=Count("id"),
                total_positive=Count("id", filter=Q(sentiment="positive")),
                total_negative=Count("id", filter=Q(sentiment="negative")),
                total_neutral=Count("id", filter=Q(sentiment="neutral")),
            )

            service.avg_star = stats["avg_star"] or 0
            service.review_count = stats["review_count"] or 0
            service.total_positive = stats["total_positive"] or 0
            service.total_negative = stats["total_negative"] or 0
            service.total_neutral = stats["total_neutral"] or 0

            service.save(
                update_fields=[
                    "avg_star",
                    "review_count",
                    "total_positive",
                    "total_negative",
                    "total_neutral",
                ]
            )

            # ✅ Cập nhật lại total_weighted_score
            service.update_total_weighted_score()
            return service

        # =========================
        # 🔹 GỌI CẬP NHẬT & CẬP NHẬT INTERACTION
        # =========================
        if service_type == ServiceType.HOTEL:
            hotel = update_service_stats(Hotel, ServiceType.HOTEL, ref_id)

            if hotel:
                interaction = UserHotelInteraction.objects.filter(
                    user=user, hotel=hotel
                ).first()
                if interaction:
                    # Giảm số lượng sentiment tương ứng
                    if old_sentiment == "positive" and interaction.positive_count > 0:
                        interaction.positive_count -= 1
                    elif old_sentiment == "negative" and interaction.negative_count > 0:
                        interaction.negative_count -= 1
                    elif old_sentiment == "neutral" and interaction.neutral_count > 0:
                        interaction.neutral_count -= 1

                    # Cập nhật lại điểm cá nhân hóa
                    interaction.update_weighted_score()
                    interaction.save()

        elif service_type == ServiceType.ACTIVITY:
            activity = update_service_stats(Activity, ServiceType.ACTIVITY, ref_id)

            if activity:
                interaction = UserActivityInteraction.objects.filter(
                    user=user, activity=activity
                ).first()
                if interaction:
                    # Giảm số lượng sentiment tương ứng
                    if old_sentiment == "positive" and interaction.positive_count > 0:
                        interaction.positive_count -= 1
                    elif old_sentiment == "negative" and interaction.negative_count > 0:
                        interaction.negative_count -= 1
                    elif old_sentiment == "neutral" and interaction.neutral_count > 0:
                        interaction.neutral_count -= 1

                    # Cập nhật lại điểm cá nhân hóa
                    interaction.update_weighted_score()
                    interaction.save()

        elif service_type == ServiceType.HANDBOOK:
            handbook = update_service_stats(Handbook, ServiceType.HANDBOOK, ref_id)

            if handbook:
                interaction = UserHandbookInteraction.objects.filter(
                    user=user, handbook=handbook
                ).first()
                if interaction:
                    # Giảm số lượng sentiment tương ứng
                    if old_sentiment == "positive" and interaction.positive_count > 0:
                        interaction.positive_count -= 1
                    elif old_sentiment == "negative" and interaction.negative_count > 0:
                        interaction.negative_count -= 1
                    elif old_sentiment == "neutral" and interaction.neutral_count > 0:
                        interaction.neutral_count -= 1

                    # Cập nhật lại điểm cá nhân hóa
                    interaction.update_weighted_score()
                    interaction.save()

        # =========================
        # 🔹 TRẢ KẾT QUẢ
        # =========================
        return Response(
            {
                "isSuccess": True,
                "message": "Review deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
