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
        booking_id = self.request.query_params.get('booking_id')
        if booking_id:
            queryset = queryset.filter(booking_id=booking_id)
        return queryset

    # 🧩 Tạo Payment mới (POST /api/payments/)
    def create(self, request, *args, **kwargs):
        booking_id = request.data.get("booking_id")

        if not booking_id:
            return Response(
                {"detail": "booking_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Nếu đã có payment trước đó → không tạo mới
        if hasattr(booking, "payment"):
            return Response(
                {"detail": "Payment already exists for this booking"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = Payment.objects.create(
            booking=booking,
            amount=request.data.get("amount", booking.total_price),
            status=PaymentStatus.PENDING,
            method=request.data.get("method", PaymentMethod.ONLINE)
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    # 🪙 Bắt đầu thanh toán PayPal
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        payment = self.get_object()

        if payment.status in [PaymentStatus.SUCCESS, PaymentStatus.PAID, PaymentStatus.UNPAID]:
            return Response(
                {"detail": "Payment already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success_url = request.data.get("success_url")
        cancel_url = request.data.get("cancel_url")

        if not success_url or not cancel_url:
            return Response(
                {"detail": "Both success_url and cancel_url are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        #Tạo Stripe section
        # Stripe amount phải là số nguyên nhỏ nhất, VND không có decimal
        amount = int(payment.amount)  # nếu VND: 100_000 -> 100000
        currency = "vnd"  # hoặc usd, eur
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': f"Booking {payment.booking.booking_code}",
                        },
                        'unit_amount': amount,  # Stripe tính theo smallest currency unit
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            # Lưu session id vào transaction_id để theo dõi
            payment.transaction_id = session.id
            payment.save()

            return Response({
                "checkout_session_id": session.id,
                "checkout_url": session.url
            })
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    # 💳 Capture sau khi thanh toán thành công
    @action(detail=True, methods=['post'])
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
                    message=f"Đơn đặt {booking.booking_code} của bạn đã được thanh toán thành công!"
                )
            return Response({"detail": "Payment completed successfully"})
        else:
            payment.status = PaymentStatus.FAILED
            payment.save()

            # ❌ Gửi thông báo khi thất bại
            if email_to:
                Notification.objects.create(
                    user=booking.user if booking.user else None,
                    email= email_to,
                    title="Thanh toán thất bại",
                    message=f"Đơn đặt {payment.booking.booking_code} thanh toán không thành công. Vui lòng thử lại."
                )

            return Response({"detail": "Payment not completed"}, status=400)

    @action(detail=True, methods=['post'])
    def confirm_cash(self, request, pk=None):
        payment = self.get_object()
        email_to = self.get_booking_email(payment.booking)

        # ❌ Kiểm tra phương thức
        if payment.method != PaymentMethod.CASH:
            return Response(
                {"detail": "This payment is not a cash payment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking = payment.booking

        # ✅ Cập nhật trạng thái
        payment.status = PaymentStatus.UNPAID
        booking.status = BookingStatus.CONFIRMED
        booking.payment_status = PaymentStatus.UNPAID

        payment.save(update_fields=['status'])
        booking.save(update_fields=['status', 'payment_status'])

        # ✅ Chuẩn bị thông báo linh hoạt theo loại dịch vụ
        service_label = dict(ServiceType.choices).get(booking.service_type, "Booking")
        user = getattr(booking, "user", None)

        # Thông điệp riêng cho từng loại dịch vụ
        if booking.service_type == ServiceType.HOTEL:
            title = "Đặt phòng thành công"
            message = f"Đơn đặt phòng {booking.booking_code} của bạn đã được xác nhận. " \
                    "Vui lòng thanh toán khi nhận phòng."
        elif booking.service_type == ServiceType.CAR:
            title = "Đặt xe thành công"
            message = f"Đơn thuê xe {booking.booking_code} của bạn đã được xác nhận. " \
                    "Vui lòng thanh toán khi nhận xe."
        elif booking.service_type == ServiceType.FLIGHT:
            title = "Đặt vé máy bay thành công"
            message = f"Đơn đặt vé {booking.booking_code} của bạn đã được xác nhận. " \
                    "Vui lòng thanh toán tại quầy check-in hoặc theo hướng dẫn của hãng."
        else:
            title = "Đặt dịch vụ thành công"
            message = f"Đơn đặt {booking.booking_code} của bạn đã được xác nhận."

        # ✅ Gửi thông báo
        if email_to:
            Notification.objects.create(
                user=booking.user if booking.user else None,
                email=email_to,
                title=title,
                message=message
            )

        return Response(
            {
                "success": True,
                "detail": message
            },
            status=status.HTTP_200_OK
        )

