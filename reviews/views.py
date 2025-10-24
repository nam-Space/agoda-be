from rest_framework import viewsets, permissions
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
from hotels.models import Hotel
from activities.models import Activity
from django.db.models import Avg, Count

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
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
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

        service_type = getattr(review, "service_type", None)

        if service_type == ServiceType.HOTEL:
            hotel = Hotel.objects.filter(id=review.service_ref_id).first()
            if hotel:
                stats = Review.objects.filter(
                    service_type=ServiceType.HOTEL, service_ref_id=hotel.id
                ).aggregate(avg=Avg("rating"), count=Count("id"))
                hotel.avg_star = stats["avg"] or 0
                hotel.review_count = stats["count"]
                hotel.save(update_fields=["avg_star", "review_count"])

        elif review.service_type == ServiceType.ACTIVITY:
            activity = Activity.objects.filter(id=review.service_ref_id).first()
            if activity:
                stats = Review.objects.filter(
                    service_type=ServiceType.ACTIVITY, service_ref_id=activity.id
                ).aggregate(avg=Avg("rating"), count=Count("id"))
                activity.avg_star = stats["avg"] or 0
                activity.review_count = stats["count"]
                activity.save(update_fields=["avg_star", "review_count"])

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

    def update(self, request, *args, **kwargs):
        review = self.get_object()
        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_review = serializer.save()

        # ✅ Nếu có comment mới thì phân tích lại cảm xúc
        if updated_review.comment and updated_review.comment.strip():
            result = _sentiment_analyzer(updated_review.comment)[0]
            label = result["label"]
            score = float(result["score"])

            sentiment = (
                "positive"
                if label == "POS"
                else "negative" if label == "NEG" else "neutral"
            )

            updated_review.sentiment = sentiment
            updated_review.confidence = score
            updated_review.save(update_fields=["sentiment", "confidence"])

        # ✅ Cập nhật lại điểm trung bình & số lượng review
        service_type = getattr(updated_review, "service_type", None)

        if service_type == ServiceType.HOTEL:
            hotel = Hotel.objects.filter(id=updated_review.service_ref_id).first()
            if hotel:
                stats = Review.objects.filter(
                    service_type=ServiceType.HOTEL, service_ref_id=hotel.id
                ).aggregate(avg=Avg("rating"), count=Count("id"))
                hotel.avg_star = stats["avg"] or 0
                hotel.review_count = stats["count"]
                hotel.save(update_fields=["avg_star", "review_count"])

        elif service_type == ServiceType.ACTIVITY:
            activity = Activity.objects.filter(id=updated_review.service_ref_id).first()
            if activity:
                stats = Review.objects.filter(
                    service_type=ServiceType.ACTIVITY, service_ref_id=activity.id
                ).aggregate(avg=Avg("rating"), count=Count("id"))
                activity.avg_star = stats["avg"] or 0
                activity.review_count = stats["count"]
                activity.save(update_fields=["avg_star", "review_count"])

        # ✅ Trả response chuẩn
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
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa review

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Review deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
