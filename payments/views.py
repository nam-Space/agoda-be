from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.conf import settings
from notifications.models import Notification

# from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
# from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest
import stripe

from .models import Payment
from .serializers import PaymentSerializer
from bookings.models import Booking
from payments.constants.payment_status import PaymentStatus
from payments.constants.payment_method import PaymentMethod
from bookings.constants.service_type import ServiceType
from bookings.constants.booking_status import BookingStatus
from django.db.models.functions import TruncDay, TruncMonth, TruncQuarter, TruncYear
from django.db.models import Sum
from datetime import timedelta

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [AllowAny]

    def get_booking_email(self, booking):
        if booking.user and booking.user.email:
            return booking.user.email
        elif hasattr(booking, "guest_info") and booking.guest_info.email:
            return booking.guest_info.email
        return None

    def get_queryset(self):
        queryset = Payment.objects.all()
        booking_id = self.request.query_params.get("booking_id")
        if booking_id:
            queryset = queryset.filter(booking_id=booking_id)
        return queryset

    # 🧩 Tạo Payment mới (POST /api/payments/)
    def create(self, request, *args, **kwargs):
        booking_id = request.data.get("booking_id")

        if not booking_id:
            return Response(
                {"detail": "booking_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Nếu đã có payment trước đó → không tạo mới
        if hasattr(booking, "payment"):
            return Response(
                {"detail": "Payment already exists for this booking"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.create(
            booking=booking,
            amount=request.data.get("amount", booking.total_price),
            status=PaymentStatus.PENDING,
            method=request.data.get("method", PaymentMethod.ONLINE),
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    # 🪙 Bắt đầu thanh toán PayPal
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        payment = self.get_object()

        if payment.status in [
            PaymentStatus.SUCCESS,
            PaymentStatus.PAID,
            PaymentStatus.UNPAID,
        ]:
            return Response(
                {"detail": "Payment already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success_url = request.data.get("success_url")
        cancel_url = request.data.get("cancel_url")

        if not success_url or not cancel_url:
            return Response(
                {"detail": "Both success_url and cancel_url are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Tạo Stripe section
        # Stripe amount phải là số nguyên nhỏ nhất, VND không có decimal
        amount = int(payment.amount)  # nếu VND: 100_000 -> 100000
        currency = "vnd"  # hoặc usd, eur
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {
                                "name": f"Booking {payment.booking.booking_code}",
                            },
                            "unit_amount": amount,  # Stripe tính theo smallest currency unit
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
            )
            # Lưu session id vào transaction_id để theo dõi
            payment.transaction_id = session.id
            payment.save()

            return Response(
                {"checkout_session_id": session.id, "checkout_url": session.url}
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    # 💳 Capture sau khi thanh toán thành công
    @action(detail=True, methods=["post"])
    def capture(self, request, pk=None):
        payment = self.get_object()
        session = stripe.checkout.Session.retrieve(payment.transaction_id)
        email_to = self.get_booking_email(payment.booking)
        if session.payment_status == "paid":
            payment.status = PaymentStatus.SUCCESS
            payment.save()

            booking = payment.booking
            booking.payment_status = PaymentStatus.PAID
            booking.status = BookingStatus.CONFIRMED
            booking.save()

            # ✅ Gửi thông báo cho user
            if email_to:
                Notification.objects.create(
                    user=booking.user if booking.user else None,  # user có thể null
                    email=email_to,
                    title="Thanh toán thành công",
                    message=f"Đơn đặt {booking.booking_code} của bạn đã được thanh toán thành công!",
                )
            return Response({"detail": "Payment completed successfully"})
        else:
            payment.status = PaymentStatus.FAILED
            payment.save()

            # ❌ Gửi thông báo khi thất bại
            if email_to:
                Notification.objects.create(
                    user=booking.user if booking.user else None,
                    email=email_to,
                    title="Thanh toán thất bại",
                    message=f"Đơn đặt {payment.booking.booking_code} thanh toán không thành công. Vui lòng thử lại.",
                )

            return Response({"detail": "Payment not completed"}, status=400)

    @action(detail=True, methods=["post"])
    def confirm_cash(self, request, pk=None):
        payment = self.get_object()
        email_to = self.get_booking_email(payment.booking)

        # ❌ Kiểm tra phương thức
        if payment.method != PaymentMethod.CASH:
            return Response(
                {"detail": "This payment is not a cash payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = payment.booking

        # ✅ Cập nhật trạng thái
        payment.status = PaymentStatus.UNPAID
        booking.status = BookingStatus.CONFIRMED
        booking.payment_status = PaymentStatus.UNPAID

        payment.save(update_fields=["status"])
        booking.save(update_fields=["status", "payment_status"])

        # ✅ Chuẩn bị thông báo linh hoạt theo loại dịch vụ
        service_label = dict(ServiceType.choices).get(booking.service_type, "Booking")
        user = getattr(booking, "user", None)

        # Thông điệp riêng cho từng loại dịch vụ
        if booking.service_type == ServiceType.HOTEL:
            title = "Đặt phòng thành công"
            message = (
                f"Đơn đặt phòng {booking.booking_code} của bạn đã được xác nhận. "
                "Vui lòng thanh toán khi nhận phòng."
            )
        elif booking.service_type == ServiceType.CAR:
            title = "Đặt xe thành công"
            message = (
                f"Đơn thuê xe {booking.booking_code} của bạn đã được xác nhận. "
                "Vui lòng thanh toán khi nhận xe."
            )
        elif booking.service_type == ServiceType.FLIGHT:
            title = "Đặt vé máy bay thành công"
            message = (
                f"Đơn đặt vé {booking.booking_code} của bạn đã được xác nhận. "
                "Vui lòng thanh toán tại quầy check-in hoặc theo hướng dẫn của hãng."
            )
        elif booking.service_type == ServiceType.ACTIVITY:
            title = "Đặt vé hoạt động thành công"
            message = (
                f"Đơn đặt vé hoạt động {booking.booking_code} của bạn đã được xác nhận. "
                "Vui lòng thanh toán tại quầy check-in hoặc theo hướng dẫn của hãng."
            )
        else:
            title = "Đặt dịch vụ thành công"
            message = f"Đơn đặt {booking.booking_code} của bạn đã được xác nhận."

        # ✅ Gửi thông báo
        if email_to:
            Notification.objects.create(
                user=booking.user if booking.user else None,
                email=email_to,
                title=title,
                message=message,
            )

        return Response({"success": True, "detail": message}, status=status.HTTP_200_OK)


# payments/views.py
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Payment
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from bookings.models import Booking
from bookings.constants.booking_status import BookingStatus
from rest_framework import status
from .serializers import PaymentCreateSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication


# Phân trang
class PaymentPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    filters = {}

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")
        booking__service_type = request.query_params.get("booking__service_type")
        booking__service_ref_id = request.query_params.get("booking__service_ref_id")
        owner_hotel_id = request.query_params.get("owner_hotel_id")
        event_organizer_activity_id = request.query_params.get(
            "event_organizer_activity_id"
        )
        driver_id = request.query_params.get("driver_id")

        if booking__service_type:
            self.filters["booking__service_type"] = booking__service_type

        if booking__service_ref_id:
            self.filters["booking__service_ref_id"] = booking__service_ref_id

        # ✅ Lưu filter theo owner_hotel_id (RoomBookingDetail)
        if owner_hotel_id:
            # chỉ áp dụng cho booking có service_type là HOTEL
            self.filters["booking__service_type"] = ServiceType.HOTEL
            self.filters["booking__hotel_detail__owner_hotel_id"] = owner_hotel_id

        if event_organizer_activity_id:
            # chỉ áp dụng cho booking có service_type là ACTIVITY
            self.filters["booking__service_type"] = ServiceType.ACTIVITY
            self.filters[
                "booking__activity_date_detail__event_organizer_activity_id"
            ] = event_organizer_activity_id

        if driver_id:
            # chỉ áp dụng cho booking có service_type là CAR
            self.filters["booking__service_type"] = ServiceType.CAR
            self.filters["booking__car_detail__driver_id"] = driver_id

        for field, value in request.query_params.items():
            if field not in [
                "current",
                "pageSize",
                "booking__service_type",
                "booking__service_ref_id",
                "owner_hotel_id",
                "event_organizer_activity_id",
                "driver_id",
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
        total_count = Payment.objects.filter(**self.filters).count()
        total_pages = math.ceil(total_count / self.page_size)

        self.filters.clear()

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched payments successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách hóa đơn (với phân trang)
class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.all().order_by("-created_at")
    serializer_class = PaymentSerializer
    pagination_class = PaymentPagination
    authentication_classes = [JWTAuthentication]  # ✅ cần có để lấy user
    permission_classes = []
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Payment.objects.all().order_by("-created_at")

        # Lọc dữ liệu theo query params
        filter_params = self.request.query_params
        query_filter = Q()

        # lọc theo service_type (service_type là FK trong model Hotel)
        booking__service_type = filter_params.get("booking__service_type")
        if booking__service_type:
            query_filter &= Q(booking__service_type=booking__service_type)

        booking__service_ref_id = filter_params.get("booking__service_ref_id")
        if booking__service_ref_id:
            query_filter &= Q(booking__service_ref_id=booking__service_ref_id)

        # --- Lọc theo owner_hotel (truy ngược qua RoomBookingDetail) ---
        owner_hotel_id = filter_params.get("owner_hotel_id")
        if owner_hotel_id:
            query_filter &= Q(
                booking__hotel_detail__owner_hotel_id=owner_hotel_id,
                booking__service_type=ServiceType.HOTEL,  # chỉ lọc khi service_type là HOTEL
            )

        event_organizer_activity_id = filter_params.get("event_organizer_activity_id")
        if event_organizer_activity_id:
            query_filter &= Q(
                booking__activity_date_detail__event_organizer_activity_id=event_organizer_activity_id,
                booking__service_type=ServiceType.ACTIVITY,  # chỉ lọc khi service_type là ACTIVITY
            )

        driver_id = filter_params.get("driver_id")
        if driver_id:
            query_filter &= Q(
                booking__car_detail__driver_id=driver_id,
                booking__service_type=ServiceType.CAR,  # chỉ lọc khi service_type là CAR
            )

        for field, value in filter_params.items():
            if field not in [
                "pageSize",
                "current",
                "booking__service_type",
                "booking__service_ref_id",
                "owner_hotel_id",
                "event_organizer_activity_id",
                "driver_id",
            ]:  # Bỏ qua các trường phân trang
                query_filter &= Q(**{f"{field}__icontains": value})

        # Áp dụng lọc cho queryset
        queryset = queryset.filter(query_filter).order_by("-created_at")

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


class PaymentListOverviewView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]  # hoặc [] nếu bạn không cần xác thực

    def get_queryset(self):
        queryset = Payment.objects.all()
        params = self.request.query_params

        min_date = params.get("min_date")
        max_date = params.get("max_date")
        booking__service_type = params.get("booking__service_type")
        booking__service_ref_id = params.get("booking__service_ref_id")
        owner_hotel_id = params.get("owner_hotel_id")
        event_organizer_activity_id = params.get("event_organizer_activity_id")
        driver_id = params.get("driver_id")
        hotel_id = params.get("hotel_id")
        activity_id = params.get("activity_id")
        car_id = params.get("car_id")

        if min_date and max_date:
            queryset = queryset.filter(created_at__range=[min_date, max_date])
        elif min_date:
            queryset = queryset.filter(created_at__gte=min_date)
        elif max_date:
            queryset = queryset.filter(created_at__lte=max_date)

        if booking__service_type:
            queryset = queryset.filter(booking__service_type=booking__service_type)

        if booking__service_ref_id:
            queryset = queryset.filter(booking__service_ref_id=booking__service_ref_id)

        if owner_hotel_id:
            queryset = queryset.filter(
                booking__hotel_detail__owner_hotel_id=owner_hotel_id,
                booking__service_type=ServiceType.HOTEL,
            )

        if event_organizer_activity_id:
            queryset = queryset.filter(
                booking__activity_date_detail__event_organizer_activity_id=event_organizer_activity_id,
                booking__service_type=ServiceType.ACTIVITY,
            )

        if driver_id:
            queryset = queryset.filter(
                booking__car_detail__driver_id=driver_id,
                booking__service_type=ServiceType.CAR,
            )

        if hotel_id:
            queryset = queryset.filter(
                booking__hotel_detail__room__hotel_id=hotel_id,
                booking__service_type=ServiceType.HOTEL,
            )

        if activity_id:
            queryset = queryset.filter(
                booking__activity_date_detail__activity_date__activity_package__activity_id=activity_id,
                booking__service_type=ServiceType.ACTIVITY,
            )

        if car_id:
            queryset = queryset.filter(
                booking__car_detail__car_id=car_id,
                booking__service_type=ServiceType.CAR,
            )

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        params = self.request.query_params
        statistic_by = params.get("statistic_by", "month")  # mặc định là month

        # 🧮 Chọn hàm group theo statistic_by
        if statistic_by == "day":
            trunc_func = TruncDay
        elif statistic_by == "quarter":
            trunc_func = TruncQuarter
        elif statistic_by == "year":
            trunc_func = TruncYear
        else:
            trunc_func = TruncMonth

        # 🔹 Gom nhóm dữ liệu theo thời gian
        grouped_data = (
            queryset.annotate(period=trunc_func("created_at"))
            .values("period")
            .annotate(
                total_revenue=Sum("amount"),
                customer_count=Count("booking__user", distinct=True),
                order_count=Count("id", distinct=True),
            )
            .order_by("period")
        )

        labels, revenues, total, customers, orders = [], [], 0, [], []

        for entry in grouped_data:
            date_obj = entry["period"]
            if not date_obj:
                continue

            if statistic_by == "day":
                label = date_obj.strftime("%d %b %Y")
            elif statistic_by == "month":
                label = date_obj.strftime("%b %Y")
            elif statistic_by == "quarter":
                q = (date_obj.month - 1) // 3 + 1
                label = f"Q{q} {date_obj.year}"
            else:
                label = str(date_obj.year)

            labels.append(label)
            revenue = entry["total_revenue"] or 0
            revenues.append(revenue)
            total += revenue
            customers.append(entry["customer_count"])
            orders.append(entry["order_count"])

        # ✅ Tính phần trăm tăng trưởng an toàn
        def calc_growth(arr):
            if len(arr) < 2 or arr[-2] == 0:
                return 0.0
            return round(((arr[-1] - arr[-2]) / arr[-2]) * 100, 2)

        revenue_growth = calc_growth(revenues)
        customer_growth = calc_growth(customers)
        order_growth = calc_growth(orders)

        return Response(
            {
                "isSuccess": True,
                "message": (
                    "Get payment overview successfully!" if queryset else "No data"
                ),
                "data": {
                    "labels": labels,
                    "revenues": revenues,
                    "total_revenue": total,
                    "revenue_growth": revenue_growth,
                    "customers": customers,
                    "customer_growth": customer_growth,
                    "orders": orders,
                    "order_growth": order_growth,
                    "statistic_by": statistic_by,
                },
            }
        )


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    authentication_classes = []
    permission_classes = []

    def retrieve(self, request, *args, **kwargs):
        payment = self.get_object()
        serializer = self.get_serializer(payment)
        return Response(
            {
                "isSuccess": True,
                "message": "Payment details fetched successfully",
                "data": serializer.data,
            }
        )


# API POST tạo hóa đơn
class PaymentCreateView(generics.CreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể tạo hóa đơn

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Payment created successfully",
                    "data": PaymentCreateSerializer(payment).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create payment",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật hóa đơn
class PaymentUpdateView(generics.UpdateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể sửa hóa đơn

    def update(self, request, *args, **kwargs):
        payment = self.get_object()
        serializer = self.get_serializer(payment, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Payment updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update payment",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa hóa đơn
class PaymentDeleteView(generics.DestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập mới có thể xóa hóa đơn

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Payment deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
