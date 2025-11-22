from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.conf import settings
from notifications.models import Notification
from django.core.mail import send_mail

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
from accounts.models import CustomUser
from django.core.files.storage import default_storage
import os

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_base64_image(image_path):
    """
    image_path: có thể là đường dẫn tương đối kiểu '/media/activity_images/xxx.jpg'
    """
    # Bỏ '/media/' ở đầu nếu có, vì MEDIA_ROOT là thư mục media
    if image_path.startswith("/media/"):
        relative_path = image_path[
            len("/media/") :
        ]  # 'activity_images/img1_H19Tg4Q.jpg'
    else:
        relative_path = image_path.lstrip("/")  # đảm bảo không có dấu /

    local_path = os.path.join(settings.MEDIA_ROOT, relative_path)

    try:
        with open(local_path, "rb") as img_file:
            import base64

            encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
            ext = local_path.split(".")[-1].lower()
            if ext == "jpg":
                ext = "jpeg"
            return f"data:image/{ext};base64,{encoded_string}"
    except Exception as e:
        print("Lỗi khi đọc file ảnh:", e)
        return ""


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
                scheme = request.scheme  # http hoặc https
                host = request.get_host()  # 127.0.0.1:8000
                baseUrl = f"{scheme}://{host}"

                user_obj = booking.user
                username = user_obj.username if user_obj else "Khách"
                avatar = (
                    f"{user_obj.avatar}"
                    if user_obj and user_obj.avatar
                    else f"/media/user_images/default-avatar.png"
                )

                if booking.service_type == ServiceType.HOTEL:
                    images = booking.hotel_detail.room.hotel.images.all()
                    image_url = images[0].image if images.exists() else ""

                    # gửi thông báo cho user
                    Notification.objects.create(
                        user=booking.user if booking.user else None,  # user có thể null
                        email=email_to,
                        title="Thanh toán thành công",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{image_url}' alt={booking.hotel_detail.room.hotel.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span class='font-bold'>{booking.hotel_detail.room.hotel.name}</span> - <span>{booking.hotel_detail.room.room_type}</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Nhận phòng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Trả phòng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email=f"""
                            <div style="padding:20px;font-family:sans-serif;background:#f8f8f8">
                                <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px">
                                    <h2 style="color:#4CAF50">Thanh toán thành công 🎉</h2>
                                    <p>Xin chào <b>{booking.guest_info.full_name if booking.user else "Khách"}</b>,</p>
                                    <p>Bạn đã thanh toán thành công mã đặt phòng <b>{booking.booking_code}</b>.</p>

                                    <img src={get_base64_image(image_url)} 
                                        style="width:100%;height:250px;object-fit:cover;border-radius:10px" />

                                    <h3 style="margin-top:20px">Thông tin đặt phòng</h3>
                                    <ul>
                                        <li>Khách sạn: <b>{booking.hotel_detail.room.hotel.name}</b></li>
                                        <li>Loại phòng: <b>{booking.hotel_detail.room.room_type}</b></li>
                                        <li>Nhận phòng: {booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</li>
                                        <li>Trả phòng: {booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</li>
                                    </ul>

                                    <p style="margin-top:20px">
                                        Cảm ơn bạn đã đặt phòng tại hệ thống của chúng tôi ❤️
                                    </p>
                                </div>
                            </div>
                        """,
                        link=f"/profile/hotel",
                        send_mail_flag=True,
                    )

                    # gửi thông báo cho chủ khách sạn (không gửi email)
                    Notification.objects.create(
                        user=(
                            booking.hotel_detail.owner_hotel
                            if booking.hotel_detail.owner_hotel
                            else None
                        ),  # user có thể null
                        email=booking.hotel_detail.owner_hotel.email,
                        title="Thanh toán thành công",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{image_url}' alt={booking.hotel_detail.room.hotel.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span>Khách hàng </span><span className="font-bold text-blue-700">{booking.guest_info.full_name} </span><span>đã đặt: </span><span class='font-bold'>{booking.hotel_detail.room.hotel.name}</span> - <span>{booking.hotel_detail.room.room_type}</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div class="flex items-center gap-[4px]">
                                        <img alt={username} class="w-[24px] h-[24px] object-cover rounded-[50%]" src='{baseUrl}{avatar}'>
                                        <div>
                                            <p class="text-gray-600 text-[12px]">Nhận phòng</p>
                                            <p class="font-semibold text-[12px] text-gray-900">{booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                        </div>
                                    </div>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Trả phòng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email="",
                        link=f"/room-payment",
                        send_mail_flag=False,
                    )

                    # gửi thông báo cho nhân viên của khách sạn đó (không gửi email)
                    staffs = booking.hotel_detail.owner_hotel.staffs.all()
                    for staff in staffs:
                        Notification.objects.create(
                            user=staff,
                            email=staff.email,
                            title="Thanh toán thành công",
                            message=f"""
                            <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                                <div class='flex-shrink-0'><img src='{baseUrl}{image_url}' alt={booking.hotel_detail.room.hotel.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                                <div class='flex-grow'>
                                    <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                        <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                        <span>Khách hàng </span><span className="font-bold text-blue-700">{booking.guest_info.full_name} </span><span>đã đặt: </span><span class='font-bold'>{booking.hotel_detail.room.hotel.name}</span> - <span>{booking.hotel_detail.room.room_type}</span>
                                    </h3>
                                    <div class='flex gap-[20px]'>
                                        <div class="flex items-center gap-[4px]">
                                            <img alt={username} class="w-[24px] h-[24px] object-cover rounded-[50%]" src='{baseUrl}{avatar}'>
                                            <div>
                                                <p class="text-gray-600 text-[12px]">Nhận phòng</p>
                                                <p class="font-semibold text-[12px] text-gray-900">{booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                            </div>
                                        </div>
                                        <div>
                                            <p class='text-gray-600 text-[12px]'>Trả phòng</p>
                                            <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>""",
                            message_email="",
                            link=f"/room-payment",  # hoặc link phù hợp cho admin
                            send_mail_flag=False,
                        )

                    # gửi thông báo cho tất cả admin (không gửi email)
                    admins = CustomUser.objects.filter(
                        role="admin"
                    )  # sửa 'role' + 'admin' theo model của bạn
                    for admin in admins:
                        Notification.objects.create(
                            user=admin,
                            email=admin.email,
                            title="Thanh toán thành công",
                            message=f"""
                            <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                                <div class='flex-shrink-0'><img src='{baseUrl}{image_url}' alt={booking.hotel_detail.room.hotel.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                                <div class='flex-grow'>
                                    <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                        <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                        <span>Khách hàng </span><span className="font-bold text-blue-700">{booking.guest_info.full_name} </span><span>đã đặt: </span><span class='font-bold'>{booking.hotel_detail.room.hotel.name}</span> - <span>{booking.hotel_detail.room.room_type}</span>
                                    </h3>
                                    <div class='flex gap-[20px]'>
                                        <div class="flex items-center gap-[4px]">
                                            <img alt={username} class="w-[24px] h-[24px] object-cover rounded-[50%]" src='{baseUrl}{avatar}'>
                                            <div>
                                                <p class="text-gray-600 text-[12px]">Nhận phòng</p>
                                                <p class="font-semibold text-[12px] text-gray-900">{booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                            </div>
                                        </div>
                                        <div>
                                            <p class='text-gray-600 text-[12px]'>Trả phòng</p>
                                            <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>""",
                            message_email="",
                            link=f"/room-payment",  # hoặc link phù hợp cho admin
                            send_mail_flag=False,
                        )

                elif booking.service_type == ServiceType.CAR:
                    # gửi thông báo cho user
                    Notification.objects.create(
                        user=booking.user if booking.user else None,  # user có thể null
                        email=email_to,
                        title="Thanh toán thành công",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{booking.car_detail.car.image}' alt={booking.car_detail.car.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span class='font-bold'>{booking.car_detail.car.name}</span> <span>({booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location})</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời điểm bắt đầu</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>

                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời gian ước lượng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.total_time_estimate} tiếng</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email=f"""
                        <table width="100%" cellpadding="0" cellspacing="0" 
                            style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:30px 0;">
                            <tr>
                                <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" 
                                        style="background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                                    <!-- Header -->
                                    <tr>
                                    <td style="background:#0ea5e9; padding:20px; text-align:center; color:white;">
                                        <h2 style="margin:0; font-size:22px;">🎉 Thanh toán thành công!</h2>
                                        <p style="margin:0; font-size:14px;">Cảm ơn bạn đã đặt chuyến xe tại hệ thống</p>
                                    </td>
                                    </tr>

                                    <!-- Body -->
                                    <tr>
                                        <td style="padding:25px;">

                                            <h3 style="margin-top:0;">Thông tin chuyến đi</h3>

                                            <table width="100%" cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <!-- Car image -->
                                                    <td width="120">
                                                    <img src={get_base64_image(booking.car_detail.car.image)} 
                                                        alt="{booking.car_detail.car.name}"
                                                        style="width:120px; height:80px; object-fit:cover; border-radius:8px;">
                                                    </td>

                                                    <!-- Trip details -->
                                                    <td style="padding-left:15px;">
                                                    <p style="margin:0; font-size:15px;">
                                                        <strong>Mã đặt chỗ:</strong>
                                                        <span style="color:#0284c7; font-weight:bold;">{booking.booking_code}</span>
                                                    </p>

                                                    <p style="margin:6px 0 0;">
                                                        <strong>Xe:</strong> {booking.car_detail.car.name}
                                                    </p>

                                                    <p style="margin:4px 0 0;">
                                                        <strong>Hành trình:</strong>
                                                        {booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location}
                                                    </p>
                                                    </td>
                                                </tr>
                                            </table>

                                            <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                            <!-- Dates -->
                                            <h3 style="margin-bottom:10px;">Thời gian</h3>

                                            <p style="margin:0;">
                                                <strong>Thời điểm bắt đầu:</strong><br>
                                                {booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}
                                            </p>

                                            <p style="margin:10px 0 0;">
                                                <strong>Thời gian ước lượng:</strong><br>
                                                {booking.car_detail.total_time_estimate} tiếng
                                            </p>

                                            <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                            <p style="margin-bottom:0; font-size:14px; color:#475569;">
                                            Nếu bạn có bất kỳ câu hỏi nào, đừng ngần ngại liên hệ với chúng tôi.
                                            </p>

                                        </td>
                                    </tr>

                                    <!-- Footer -->
                                    <tr>
                                        <td style="background:#f1f5f9; padding:15px; text-align:center; font-size:12px; color:#64748b;">
                                            © 2024 Booking System. All rights reserved.
                                        </td>
                                    </tr>

                                </table>
                                </td>
                            </tr>
                        </table>
                        """,
                        link=f"",
                        send_mail_flag=True,
                    )

                    # gửi thông báo cho tài xế taxi (không gửi email)
                    Notification.objects.create(
                        user=(
                            booking.car_detail.driver
                            if booking.car_detail.driver
                            else None
                        ),  # user có thể null
                        email=booking.car_detail.driver.email,
                        title="Thanh toán thành công",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{booking.car_detail.car.image}' alt={booking.car_detail.car.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span>Khách hàng </span><span className="font-bold text-blue-700">{booking.guest_info.full_name} </span><span>đã đặt: </span><span class='font-bold'>{booking.car_detail.car.name}</span> <span>({booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location})</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div class="flex items-center gap-[4px]">
                                        <img alt={username} class="w-[24px] h-[24px] object-cover rounded-[50%]" src='{baseUrl}{avatar}'>
                                        <div>
                                            <p class='text-gray-600 text-[12px]'>Thời điểm bắt đầu</p>
                                            <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                        </div>
                                    </div>

                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời gian ước lượng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.total_time_estimate} tiếng</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email="",
                        link=f"",
                        send_mail_flag=False,
                    )

                    # gửi thông báo cho tất cả admin (không gửi email)
                    admins = CustomUser.objects.filter(
                        role="admin"
                    )  # sửa 'role' + 'admin' theo model của bạn
                    for admin in admins:
                        Notification.objects.create(
                            user=admin,
                            email=admin.email,
                            title="Thanh toán thành công",
                            message=f"""
                            <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                                <div class='flex-shrink-0'><img src='{baseUrl}{booking.car_detail.car.image}' alt={booking.car_detail.car.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                                <div class='flex-grow'>
                                    <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                        <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                        <span>Khách hàng </span><span className="font-bold text-blue-700">{booking.guest_info.full_name} </span><span>đã đặt: </span><span class='font-bold'>{booking.car_detail.car.name}</span> <span>({booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location})</span>
                                    </h3>
                                    <div class='flex gap-[20px]'>
                                        <div class="flex items-center gap-[4px]">
                                            <img alt={username} class="w-[24px] h-[24px] object-cover rounded-[50%]" src='{baseUrl}{avatar}'>
                                            <div>
                                                <p class='text-gray-600 text-[12px]'>Thời điểm bắt đầu</p>
                                                <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                            </div>
                                        </div>

                                        <div>
                                            <p class='text-gray-600 text-[12px]'>Thời gian ước lượng</p>
                                            <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.total_time_estimate} tiếng</p>
                                        </div>
                                    </div>
                                </div>
                            </div>""",
                            message_email="",
                            link=f"/room-payment",  # hoặc link phù hợp cho admin
                            send_mail_flag=False,
                        )

                elif booking.service_type == ServiceType.ACTIVITY:

                    # gửi thông báo cho user
                    Notification.objects.create(
                        user=booking.user if booking.user else None,  # user có thể null
                        email=email_to,
                        title="Thanh toán thành công",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{booking.activity_date_detail.activity_image}' alt={booking.activity_date_detail.activity_name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span class='font-bold'>{booking.activity_date_detail.activity_name}</span> - <span>{booking.activity_date_detail.activity_package_name}</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời điểm hoạt động</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}</p>
                                    </div>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời gian</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email=f"""
                        <table width="100%" cellpadding="0" cellspacing="0" 
                            style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:30px 0;">
                        <tr>
                            <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" 
                                    style="background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                                <!-- Header -->
                                <tr>
                                <td style="background:#10b981; padding:20px; text-align:center; color:white;">
                                    <h2 style="margin:0; font-size:22px;">🎉 Thanh toán thành công!</h2>
                                    <p style="margin:0; font-size:14px;">Bạn đã đặt thành công hoạt động trải nghiệm</p>
                                </td>
                                </tr>

                                <!-- Body -->
                                <tr>
                                <td style="padding:25px;">

                                    <h3 style="margin-top:0;">Thông tin hoạt động</h3>

                                    <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <!-- Activity image -->
                                        <td width="120">
                                        <img src={get_base64_image(booking.activity_date_detail.activity_image)} 
                                            alt="{booking.activity_date_detail.activity_name}"
                                            style="width:120px; height:80px; object-fit:cover; border-radius:8px;">
                                        </td>

                                        <!-- Description -->
                                        <td style="padding-left:15px;">
                                        <p style="margin:0; font-size:15px;">
                                            <strong>Mã đặt chỗ:</strong>
                                            <span style="color:#059669; font-weight:bold;">{booking.booking_code}</span>
                                        </p>

                                        <p style="margin:6px 0 0;">
                                            <strong>Hoạt động:</strong> {booking.activity_date_detail.activity_name}
                                        </p>

                                        <p style="margin:4px 0 0;">
                                            <strong>Gói trải nghiệm:</strong> {booking.activity_date_detail.activity_package_name}
                                        </p>
                                        </td>
                                    </tr>
                                    </table>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <!-- Schedule -->
                                    <h3 style="margin-bottom:10px;">Thời gian</h3>

                                    <p style="margin:0;">
                                    <strong>Ngày diễn ra:</strong><br>
                                    {booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}
                                    </p>

                                    <p style="margin:10px 0 0;">
                                    <strong>Thời lượng:</strong><br>
                                    {booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng
                                    </p>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <p style="margin-bottom:0; font-size:14px; color:#475569;">
                                    Chúc bạn có một trải nghiệm tuyệt vời!  
                                    Nếu cần hỗ trợ, đừng ngần ngại liên hệ với chúng tôi.
                                    </p>

                                </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                <td style="background:#f1f5f9; padding:15px; text-align:center; font-size:12px; color:#64748b;">
                                    © 2024 Booking System. All rights reserved.
                                </td>
                                </tr>

                            </table>
                            </td>
                        </tr>
                        </table>
                        """,
                        link=f"/profile/activity",
                        send_mail_flag=True,
                    )

                    # gửi thông báo cho người tổ chức hoạt động (không gửi email)
                    Notification.objects.create(
                        user=(
                            booking.activity_date_detail.event_organizer_activity
                            if booking.activity_date_detail.event_organizer_activity
                            else None
                        ),  # user có thể null
                        email=booking.activity_date_detail.event_organizer_activity.email,
                        title="Thanh toán thành công",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{booking.activity_date_detail.activity_image}' alt={booking.activity_date_detail.activity_name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span>Khách hàng </span><span className="font-bold text-blue-700">{booking.guest_info.full_name} </span><span>đã đặt: </span><span class='font-bold'>{booking.activity_date_detail.activity_name}</span> - <span>{booking.activity_date_detail.activity_package_name}</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div class="flex items-center gap-[4px]">
                                        <img alt={username} class="w-[24px] h-[24px] object-cover rounded-[50%]" src='{baseUrl}{avatar}'>
                                        <div>
                                            <p class='text-gray-600 text-[12px]'>Thời điểm hoạt động</p>
                                            <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}</p>
                                        </div>
                                    </div>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời gian</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email="",
                        link=f"/activity-payment",
                        send_mail_flag=False,
                    )

                    # gửi thông báo cho tất cả admin (không gửi email)
                    admins = CustomUser.objects.filter(
                        role="admin"
                    )  # sửa 'role' + 'admin' theo model của bạn
                    for admin in admins:
                        Notification.objects.create(
                            user=admin,
                            email=admin.email,
                            title="Thanh toán thành công",
                            message=f"""
                            <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                                <div class='flex-shrink-0'><img src='{baseUrl}{booking.activity_date_detail.activity_image}' alt={booking.activity_date_detail.activity_name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                                <div class='flex-grow'>
                                    <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                        <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                        <span>Khách hàng </span><span className="font-bold text-blue-700">{booking.guest_info.full_name} </span><span>đã đặt: </span><span class='font-bold'>{booking.activity_date_detail.activity_name}</span> - <span>{booking.activity_date_detail.activity_package_name}</span>
                                    </h3>
                                    <div class='flex gap-[20px]'>
                                        <div class="flex items-center gap-[4px]">
                                            <img alt={username} class="w-[24px] h-[24px] object-cover rounded-[50%]" src='{baseUrl}{avatar}'>
                                            <div>
                                                <p class='text-gray-600 text-[12px]'>Thời điểm hoạt động</p>
                                                <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}</p>
                                            </div>
                                        </div>
                                        <div>
                                            <p class='text-gray-600 text-[12px]'>Thời gian</p>
                                            <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng</p>
                                        </div>
                                    </div>
                                </div>
                            </div>""",
                            message_email="",
                            link=f"/activity-payment",  # hoặc link phù hợp cho admin
                            send_mail_flag=False,
                        )

            return Response({"detail": "Payment completed successfully"})
        else:
            payment.status = PaymentStatus.FAILED
            payment.save()

            # ❌ Gửi thông báo khi thất bại
            if email_to:
                scheme = request.scheme  # http hoặc https
                host = request.get_host()  # 127.0.0.1:8000
                baseUrl = f"{scheme}://{host}"

                user_obj = booking.user
                username = user_obj.username if user_obj else "Khách"
                avatar = (
                    f"{user_obj.avatar}"
                    if user_obj and user_obj.avatar
                    else f"/media/user_images/default-avatar.png"
                )

                if booking.service_type == ServiceType.HOTEL:
                    images = booking.hotel_detail.room.hotel.images.all()
                    image_url = images[0].image if images.exists() else ""

                    Notification.objects.create(
                        user=booking.user if booking.user else None,  # user có thể null
                        email=email_to,
                        title="Thanh toán thất bại",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{image_url}' alt={booking.hotel_detail.room.hotel.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <div class="flex items-center gap-[6px] text-red-500 font-bold">
                                    <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 384 512" class="text-[20px]" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M342.6 150.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192 210.7 86.6 105.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L146.7 256 41.4 361.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L192 301.3 297.4 406.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L237.3 256 342.6 150.6z"></path>
                                    </svg>
                                    Thanh toán thất bại
                                </div>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span class='font-bold'>{booking.hotel_detail.room.hotel.name}</span> - <span>{booking.hotel_detail.room.room_type}</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Nhận phòng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Trả phòng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email=f"""
                        <table width="100%" cellpadding="0" cellspacing="0" 
                            style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:30px 0;">
                        <tr>
                            <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" 
                                    style="background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                                <!-- Header -->
                                <tr>
                                <td style="background:#dc2626; padding:20px; text-align:center; color:white;">
                                    <h2 style="margin:0; font-size:22px;">⚠️ Thanh toán thất bại</h2>
                                    <p style="margin:0; font-size:14px;">Đơn đặt phòng của bạn chưa thể hoàn tất</p>
                                </td>
                                </tr>

                                <!-- Body -->
                                <tr>
                                <td style="padding:25px;">

                                    <h3 style="margin-top:0;">Thông tin đặt phòng</h3>

                                    <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <!-- Hotel image -->
                                        <td width="120">
                                        <img src={get_base64_image(image_url)}
                                            alt="{booking.hotel_detail.room.hotel.name}"
                                            style="width:120px; height:80px; object-fit:cover; border-radius:8px;">
                                        </td>

                                        <!-- Description -->
                                        <td style="padding-left:15px;">
                                        <p style="margin:0; font-size:15px;">
                                            <strong>Mã đặt chỗ:</strong>
                                            <span style="color:#dc2626; font-weight:bold;">{booking.booking_code}</span>
                                        </p>

                                        <p style="margin:6px 0 0;">
                                            <strong>Khách sạn:</strong> {booking.hotel_detail.room.hotel.name}
                                        </p>

                                        <p style="margin:4px 0 0;">
                                            <strong>Loại phòng:</strong> {booking.hotel_detail.room.room_type}
                                        </p>
                                        </td>
                                    </tr>
                                    </table>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <!-- Schedule -->
                                    <h3 style="margin-bottom:10px;">Thời gian</h3>

                                    <p style="margin:0;">
                                    <strong>Nhận phòng:</strong><br>
                                    {booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}
                                    </p>

                                    <p style="margin:10px 0 0;">
                                    <strong>Trả phòng:</strong><br>
                                    {booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}
                                    </p>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <!-- Error Message -->
                                    <p style="margin:0; font-size:15px; color:#dc2626; font-weight:bold;">
                                    ❌ Thanh toán không thành công.
                                    </p>

                                    <p style="margin:8px 0 0; font-size:14px; color:#475569;">
                                    Vui lòng kiểm tra lại phương thức thanh toán hoặc thử lại sau vài phút.
                                    Nếu bạn cần hỗ trợ, đội ngũ chăm sóc khách hàng luôn sẵn sàng!
                                    </p>

                                </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                <td style="background:#f1f5f9; padding:15px; text-align:center; font-size:12px; color:#64748b;">
                                    © 2024 Booking System. All rights reserved.
                                </td>
                                </tr>

                            </table>
                            </td>
                        </tr>
                        </table>
                        """,
                        link=f"/profile/hotel",
                        send_mail_flag=True,
                        is_error=True,
                    )

                elif booking.service_type == ServiceType.CAR:
                    Notification.objects.create(
                        user=booking.user if booking.user else None,  # user có thể null
                        email=email_to,
                        title="Thanh toán thất bại",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{booking.car_detail.car.image}' alt={booking.car_detail.car.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <div class="flex items-center gap-[6px] text-red-500 font-bold">
                                    <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 384 512" class="text-[20px]" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M342.6 150.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192 210.7 86.6 105.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L146.7 256 41.4 361.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L192 301.3 297.4 406.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L237.3 256 342.6 150.6z"></path>
                                    </svg>
                                    Thanh toán thất bại
                                </div>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span class='font-bold'>{booking.car_detail.car.name}</span> <span>({booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location})</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời điểm bắt đầu</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời gian ước lượng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.total_time_estimate} tiếng</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email=f"""
                        <table width="100%" cellpadding="0" cellspacing="0" 
                            style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:30px 0;">
                        <tr>
                            <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" 
                                    style="background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                                <!-- Header -->
                                <tr>
                                <td style="background:#dc2626; padding:20px; text-align:center; color:white;">
                                    <h2 style="margin:0; font-size:22px;">⚠️ Thanh toán thất bại</h2>
                                    <p style="margin:0; font-size:14px;">Đặt xe của bạn chưa thể hoàn tất</p>
                                </td>
                                </tr>

                                <!-- Body -->
                                <tr>
                                <td style="padding:25px;">

                                    <h3 style="margin-top:0;">Thông tin chuyến xe</h3>

                                    <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <!-- Car image -->
                                        <td width="120">
                                        <img src={get_base64_image(booking.car_detail.car.image)} 
                                            alt="{booking.car_detail.car.name}"
                                            style="width:120px; height:80px; object-fit:cover; border-radius:8px;">
                                        </td>

                                        <!-- Description -->
                                        <td style="padding-left:15px;">
                                        <p style="margin:0; font-size:15px;">
                                            <strong>Mã đặt chỗ:</strong>
                                            <span style="color:#dc2626; font-weight:bold;">{booking.booking_code}</span>
                                        </p>

                                        <p style="margin:6px 0 0;">
                                            <strong>Xe:</strong> {booking.car_detail.car.name}
                                        </p>

                                        <p style="margin:4px 0 0;">
                                            <strong>Lộ trình:</strong> {booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location}
                                        </p>
                                        </td>
                                    </tr>
                                    </table>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <!-- Schedule -->
                                    <h3 style="margin-bottom:10px;">Thời gian</h3>

                                    <p style="margin:0;">
                                    <strong>Bắt đầu:</strong><br>
                                    {booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}
                                    </p>

                                    <p style="margin:10px 0 0;">
                                    <strong>Thời gian ước lượng:</strong><br>
                                    {booking.car_detail.total_time_estimate} tiếng
                                    </p>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <!-- Error Message -->
                                    <p style="margin:0; font-size:15px; color:#dc2626; font-weight:bold;">
                                    ❌ Thanh toán không thành công.
                                    </p>

                                    <p style="margin:8px 0 0; font-size:14px; color:#475569;">
                                    Vui lòng kiểm tra lại phương thức thanh toán hoặc thử lại sau ít phút.
                                    Nếu bạn cần hỗ trợ, đội ngũ chăm sóc khách hàng luôn sẵn sàng đồng hành cùng bạn.
                                    </p>

                                </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                <td style="background:#f1f5f9; padding:15px; text-align:center; font-size:12px; color:#64748b;">
                                    © 2024 Booking System. All rights reserved.
                                </td>
                                </tr>

                            </table>
                            </td>
                        </tr>
                        </table>
                        """,
                        link=f"",
                        send_mail_flag=True,
                        is_error=True,
                    )

                elif booking.service_type == ServiceType.ACTIVITY:
                    Notification.objects.create(
                        user=booking.user if booking.user else None,  # user có thể null
                        email=email_to,
                        title="Thanh toán thất bại",
                        message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{booking.activity_date_detail.activity_image}' alt={booking.activity_date_detail.activity_name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <div class="flex items-center gap-[6px] text-red-500 font-bold">
                                    <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 384 512" class="text-[20px]" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M342.6 150.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192 210.7 86.6 105.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L146.7 256 41.4 361.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L192 301.3 297.4 406.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L237.3 256 342.6 150.6z"></path>
                                    </svg>
                                    Thanh toán thất bại
                                </div>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span class='font-bold'>{booking.activity_date_detail.activity_name}</span> - <span>{booking.activity_date_detail.activity_package_name}</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời điểm hoạt động</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}</p>
                                    </div>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời gian</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                        message_email=f"""
                        <table width="100%" cellpadding="0" cellspacing="0" 
                            style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:30px 0;">
                        <tr>
                            <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" 
                                    style="background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                                <!-- Header -->
                                <tr>
                                <td style="background:#dc2626; padding:20px; text-align:center; color:white;">
                                    <h2 style="margin:0; font-size:22px;">⚠️ Thanh toán thất bại</h2>
                                    <p style="margin:0; font-size:14px;">Hoạt động của bạn chưa được xác nhận</p>
                                </td>
                                </tr>

                                <!-- Body -->
                                <tr>
                                <td style="padding:25px;">

                                    <h3 style="margin-top:0;">Thông tin hoạt động</h3>

                                    <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <!-- Activity image -->
                                        <td width="120">
                                        <img src={get_base64_image(booking.activity_date_detail.activity_image)} 
                                            alt="{booking.activity_date_detail.activity_name}"
                                            style="width:120px; height:80px; object-fit:cover; border-radius:8px;">
                                        </td>

                                        <!-- Description -->
                                        <td style="padding-left:15px;">
                                        <p style="margin:0; font-size:15px;">
                                            <strong>Mã đặt chỗ:</strong>
                                            <span style="color:#dc2626; font-weight:bold;">{booking.booking_code}</span>
                                        </p>

                                        <p style="margin:6px 0 0;">
                                            <strong>Hoạt động:</strong> {booking.activity_date_detail.activity_name}
                                        </p>

                                        <p style="margin:4px 0 0;">
                                            <strong>Gói dịch vụ:</strong> {booking.activity_date_detail.activity_package_name}
                                        </p>
                                        </td>
                                    </tr>
                                    </table>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <!-- Schedule -->
                                    <h3 style="margin-bottom:10px;">Thời gian hoạt động</h3>

                                    <p style="margin:0;">
                                    <strong>Ngày diễn ra:</strong><br>
                                    {booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}
                                    </p>

                                    <p style="margin:10px 0 0;">
                                    <strong>Thời lượng:</strong><br>
                                    {booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng
                                    </p>

                                    <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                    <!-- Error Message -->
                                    <p style="margin:0; font-size:15px; color:#dc2626; font-weight:bold;">
                                    ❌ Thanh toán không thành công.
                                    </p>

                                    <p style="margin:8px 0 0; font-size:14px; color:#475569;">
                                    Vui lòng kiểm tra lại phương thức thanh toán hoặc thử lại sau.
                                    Nếu cần hỗ trợ, chúng tôi luôn sẵn sàng hỗ trợ bạn.
                                    </p>

                                </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                <td style="background:#f1f5f9; padding:15px; text-align:center; font-size:12px; color:#64748b;">
                                    © 2024 Booking System. All rights reserved.
                                </td>
                                </tr>

                            </table>
                            </td>
                        </tr>
                        </table>
                        """,
                        link=f"/profile/activity",
                        send_mail_flag=True,
                        is_error=True,
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
            # Notification.objects.create(
            #     user=booking.user if booking.user else None,
            #     email=email_to,
            #     title=title,
            #     message=message,
            # )
            scheme = request.scheme  # http hoặc https
            host = request.get_host()  # 127.0.0.1:8000
            baseUrl = f"{scheme}://{host}"

            if booking.service_type == ServiceType.HOTEL:
                images = booking.hotel_detail.room.hotel.images.all()
                image_url = images[0].image if images.exists() else ""

                Notification.objects.create(
                    user=booking.user if booking.user else None,  # user có thể null
                    email=email_to,
                    title="Thanh toán thành công",
                    message=f"""
                    <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                        <div class='flex-shrink-0'><img src='{baseUrl}{image_url}' alt={booking.hotel_detail.room.hotel.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                        <div class='flex-grow'>
                            <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                <span class='font-bold'>{booking.hotel_detail.room.hotel.name}</span> - <span>{booking.hotel_detail.room.room_type}</span>
                            </h3>
                            <div class='flex gap-[20px]'>
                                <div>
                                    <p class='text-gray-600 text-[12px]'>Nhận phòng</p>
                                    <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                </div>
                                <div>
                                    <p class='text-gray-600 text-[12px]'>Trả phòng</p>
                                    <p class='font-semibold text-[12px] text-gray-900'>{booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                </div>
                            </div>
                        </div>
                    </div>""",
                    message_email=f"""
                        <div style="padding:20px;font-family:sans-serif;background:#f8f8f8">
                            <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px">
                                <h2 style="color:#4CAF50">Thanh toán thành công 🎉</h2>
                                <p>Xin chào <b>{booking.guest_info.full_name if booking.user else "Khách"}</b>,</p>
                                <p>Bạn đã thanh toán thành công mã đặt phòng <b>{booking.booking_code}</b>.</p>

                                <img src={get_base64_image(image_url)} 
                                    style="width:100%;height:250px;object-fit:cover;border-radius:10px" />

                                <h3 style="margin-top:20px">Thông tin đặt phòng</h3>
                                <ul>
                                    <li>Khách sạn: <b>{booking.hotel_detail.room.hotel.name}</b></li>
                                    <li>Loại phòng: <b>{booking.hotel_detail.room.room_type}</b></li>
                                    <li>Nhận phòng: {booking.hotel_detail.check_in.strftime("%Y-%m-%d %H:%M:%S")}</li>
                                    <li>Trả phòng: {booking.hotel_detail.check_out.strftime("%Y-%m-%d %H:%M:%S")}</li>
                                </ul>

                                <p style="margin-top:20px">
                                    Cảm ơn bạn đã đặt phòng tại hệ thống của chúng tôi ❤️
                                </p>
                            </div>
                        </div>
                    """,
                    link=f"/profile/hotel",
                    send_mail_flag=True,
                )

            elif booking.service_type == ServiceType.CAR:
                Notification.objects.create(
                    user=booking.user if booking.user else None,  # user có thể null
                    email=email_to,
                    title="Thanh toán thành công",
                    message=f"""
                        <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                            <div class='flex-shrink-0'><img src='{baseUrl}{booking.car_detail.car.image}' alt={booking.car_detail.car.name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                            <div class='flex-grow'>
                                <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                    <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                    <span class='font-bold'>{booking.car_detail.car.name}</span> <span>({booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location})</span>
                                </h3>
                                <div class='flex gap-[20px]'>
                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời điểm bắt đầu</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}</p>
                                    </div>

                                    <div>
                                        <p class='text-gray-600 text-[12px]'>Thời gian ước lượng</p>
                                        <p class='font-semibold text-[12px] text-gray-900'>{booking.car_detail.total_time_estimate} tiếng</p>
                                    </div>
                                </div>
                            </div>
                        </div>""",
                    message_email=f"""
                        <table width="100%" cellpadding="0" cellspacing="0" 
                            style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:30px 0;">
                            <tr>
                                <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" 
                                        style="background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                                    <!-- Header -->
                                    <tr>
                                    <td style="background:#0ea5e9; padding:20px; text-align:center; color:white;">
                                        <h2 style="margin:0; font-size:22px;">🎉 Thanh toán thành công!</h2>
                                        <p style="margin:0; font-size:14px;">Cảm ơn bạn đã đặt chuyến xe tại hệ thống</p>
                                    </td>
                                    </tr>

                                    <!-- Body -->
                                    <tr>
                                        <td style="padding:25px;">

                                            <h3 style="margin-top:0;">Thông tin chuyến đi</h3>

                                            <table width="100%" cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <!-- Car image -->
                                                    <td width="120">
                                                    <img src={get_base64_image(booking.car_detail.car.image)} 
                                                        alt="{booking.car_detail.car.name}"
                                                        style="width:120px; height:80px; object-fit:cover; border-radius:8px;">
                                                    </td>

                                                    <!-- Trip details -->
                                                    <td style="padding-left:15px;">
                                                    <p style="margin:0; font-size:15px;">
                                                        <strong>Mã đặt chỗ:</strong>
                                                        <span style="color:#0284c7; font-weight:bold;">{booking.booking_code}</span>
                                                    </p>

                                                    <p style="margin:6px 0 0;">
                                                        <strong>Xe:</strong> {booking.car_detail.car.name}
                                                    </p>

                                                    <p style="margin:4px 0 0;">
                                                        <strong>Hành trình:</strong>
                                                        {booking.car_detail.pickup_location} → {booking.car_detail.dropoff_location}
                                                    </p>
                                                    </td>
                                                </tr>
                                            </table>

                                            <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                            <!-- Dates -->
                                            <h3 style="margin-bottom:10px;">Thời gian</h3>

                                            <p style="margin:0;">
                                                <strong>Thời điểm bắt đầu:</strong><br>
                                                {booking.car_detail.pickup_datetime.strftime("%Y-%m-%d %H:%M:%S")}
                                            </p>

                                            <p style="margin:10px 0 0;">
                                                <strong>Thời gian ước lượng:</strong><br>
                                                {booking.car_detail.total_time_estimate} tiếng
                                            </p>

                                            <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                            <p style="margin-bottom:0; font-size:14px; color:#475569;">
                                            Nếu bạn có bất kỳ câu hỏi nào, đừng ngần ngại liên hệ với chúng tôi.
                                            </p>

                                        </td>
                                    </tr>

                                    <!-- Footer -->
                                    <tr>
                                        <td style="background:#f1f5f9; padding:15px; text-align:center; font-size:12px; color:#64748b;">
                                            © 2024 Booking System. All rights reserved.
                                        </td>
                                    </tr>

                                </table>
                                </td>
                            </tr>
                        </table>
                        """,
                    link=f"",
                    send_mail_flag=True,
                )

            elif booking.service_type == ServiceType.ACTIVITY:
                Notification.objects.create(
                    user=booking.user if booking.user else None,  # user có thể null
                    email=email_to,
                    title="Thanh toán thành công",
                    message=f"""
                    <div class='border-t-[1px] border-[#f0f0f0] px-[10px] py-[10px] flex gap-[10px]'>
                        <div class='flex-shrink-0'><img src='{baseUrl}{booking.activity_date_detail.activity_image}' alt={booking.activity_date_detail.activity_name} class='w-[50px] h-[50px] object-cover rounded-lg'></div>
                        <div class='flex-grow'>
                            <h3 class='text-gray-900 mb-[6px] leading-[18px]'>
                                <div>Mã:<span class='text-blue-500 font-semibold'> {booking.booking_code}</span></div>
                                <span class='font-bold'>{booking.activity_date_detail.activity_name}</span> - <span>{booking.activity_date_detail.activity_package_name}</span>
                            </h3>
                            <div class='flex gap-[20px]'>
                                <div>
                                    <p class='text-gray-600 text-[12px]'>Thời điểm hoạt động</p>
                                    <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}</p>
                                </div>
                                <div>
                                    <p class='text-gray-600 text-[12px]'>Thời gian</p>
                                    <p class='font-semibold text-[12px] text-gray-900'>{booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng</p>
                                </div>
                            </div>
                        </div>
                    </div>""",
                    message_email=f"""
                    <table width="100%" cellpadding="0" cellspacing="0" 
                        style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:30px 0;">
                    <tr>
                        <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" 
                                style="background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                            <!-- Header -->
                            <tr>
                            <td style="background:#10b981; padding:20px; text-align:center; color:white;">
                                <h2 style="margin:0; font-size:22px;">🎉 Thanh toán thành công!</h2>
                                <p style="margin:0; font-size:14px;">Bạn đã đặt thành công hoạt động trải nghiệm</p>
                            </td>
                            </tr>

                            <!-- Body -->
                            <tr>
                            <td style="padding:25px;">

                                <h3 style="margin-top:0;">Thông tin hoạt động</h3>

                                <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <!-- Activity image -->
                                    <td width="120">
                                    <img src={get_base64_image( booking.activity_date_detail.activity_image)} 
                                        alt="{booking.activity_date_detail.activity_name}"
                                        style="width:120px; height:80px; object-fit:cover; border-radius:8px;">
                                    </td>

                                    <!-- Description -->
                                    <td style="padding-left:15px;">
                                    <p style="margin:0; font-size:15px;">
                                        <strong>Mã đặt chỗ:</strong>
                                        <span style="color:#059669; font-weight:bold;">{booking.booking_code}</span>
                                    </p>

                                    <p style="margin:6px 0 0;">
                                        <strong>Hoạt động:</strong> {booking.activity_date_detail.activity_name}
                                    </p>

                                    <p style="margin:4px 0 0;">
                                        <strong>Gói trải nghiệm:</strong> {booking.activity_date_detail.activity_package_name}
                                    </p>
                                    </td>
                                </tr>
                                </table>

                                <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                <!-- Schedule -->
                                <h3 style="margin-bottom:10px;">Thời gian</h3>

                                <p style="margin:0;">
                                <strong>Ngày diễn ra:</strong><br>
                                {booking.activity_date_detail.date_launch.strftime("%Y-%m-%d")}
                                </p>

                                <p style="margin:10px 0 0;">
                                <strong>Thời lượng:</strong><br>
                                {booking.activity_date_detail.activity_date.activity_package.activity.total_time} tiếng
                                </p>

                                <hr style="margin:20px 0; border:none; border-top:1px solid #e5e7eb;">

                                <p style="margin-bottom:0; font-size:14px; color:#475569;">
                                Chúc bạn có một trải nghiệm tuyệt vời!  
                                Nếu cần hỗ trợ, đừng ngần ngại liên hệ với chúng tôi.
                                </p>

                            </td>
                            </tr>

                            <!-- Footer -->
                            <tr>
                            <td style="background:#f1f5f9; padding:15px; text-align:center; font-size:12px; color:#64748b;">
                                © 2024 Booking System. All rights reserved.
                            </td>
                            </tr>

                        </table>
                        </td>
                    </tr>
                    </table>
                    """,
                    link=f"/profile/activity",
                    send_mail_flag=True,
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
        booking__user_id = request.query_params.get("booking__user_id")
        owner_hotel_id = request.query_params.get("owner_hotel_id")
        event_organizer_activity_id = request.query_params.get(
            "event_organizer_activity_id"
        )
        driver_id = request.query_params.get("driver_id")
        status = request.query_params.get("status")
        activity_id = request.query_params.get("activity_id")
        min_time_checkin_room = request.query_params.get("min_time_checkin_room")
        max_time_checkin_room = request.query_params.get("max_time_checkin_room")
        min_time_checkout_room = request.query_params.get("min_time_checkout_room")
        max_time_checkout_room = request.query_params.get("max_time_checkout_room")
        min_date_launch_activity = request.query_params.get("min_date_launch_activity")
        max_date_launch_activity = request.query_params.get("max_date_launch_activity")

        if booking__service_type:
            self.filters["booking__service_type"] = booking__service_type

        if booking__service_ref_id:
            self.filters["booking__service_ref_id"] = booking__service_ref_id

        if booking__user_id:
            self.filters["booking__user_id"] = booking__user_id

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

        if status:
            self.filters["status"] = status

        if activity_id:
            self.filters[
                "booking__activity_date_detail__activity_date__activity_package__activity_id"
            ] = activity_id

        if min_time_checkin_room:
            self.filters["booking__hotel_detail__check_in__gte"] = min_time_checkin_room
        if max_time_checkin_room:
            self.filters["booking__hotel_detail__check_in__lte"] = max_time_checkin_room

        if min_time_checkout_room:
            self.filters["booking__hotel_detail__check_out__gte"] = (
                min_time_checkout_room
            )
        if max_time_checkout_room:
            self.filters["booking__hotel_detail__check_out__lte"] = (
                max_time_checkout_room
            )

        if min_date_launch_activity:
            self.filters["booking__activity_date_detail__date_launch__gte"] = (
                min_date_launch_activity
            )
        if max_date_launch_activity:
            self.filters["booking__activity_date_detail__date_launch__lte"] = (
                max_date_launch_activity
            )

        for field, value in request.query_params.items():
            if field not in [
                "current",
                "pageSize",
                "booking__service_type",
                "booking__service_ref_id",
                "booking__user_id",
                "owner_hotel_id",
                "event_organizer_activity_id",
                "driver_id",
                "status",
                "sort",
                "activity_id",
                "min_time_checkin_room",
                "max_time_checkin_room",
                "min_time_checkout_room",
                "max_time_checkout_room",
                "min_date_launch_activity",
                "max_date_launch_activity",
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

        booking__user_id = filter_params.get("booking__user_id")
        if booking__user_id:
            query_filter &= Q(booking__user_id=booking__user_id)

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

        status = filter_params.get("status")
        if status:
            query_filter &= Q(
                status=status,
            )

        activity_id = filter_params.get("activity_id")
        if activity_id:
            queryset = queryset.filter(
                booking__activity_date_detail__activity_date__activity_package__activity_id=activity_id,
                booking__service_type=ServiceType.ACTIVITY,
            )

        min_time_checkin_room = filter_params.get("min_time_checkin_room")
        max_time_checkin_room = filter_params.get("max_time_checkin_room")

        # 🔹 Lọc theo khoảng thời gian checkout phòng (từ - đến)
        if min_time_checkin_room and max_time_checkin_room:
            queryset = queryset.filter(
                booking__hotel_detail__check_in__range=[
                    min_time_checkin_room,
                    max_time_checkin_room,
                ]
            )
        elif min_time_checkin_room:
            queryset = queryset.filter(
                booking__hotel_detail__check_in__gte=min_time_checkin_room
            )
        elif max_time_checkin_room:
            queryset = queryset.filter(
                booking__hotel_detail__check_in__lte=max_time_checkin_room
            )

        min_time_checkout_room = filter_params.get("min_time_checkout_room")
        max_time_checkout_room = filter_params.get("max_time_checkout_room")

        # 🔹 Lọc theo khoảng thời gian checkout phòng (từ - đến)
        if min_time_checkout_room and max_time_checkout_room:
            queryset = queryset.filter(
                booking__hotel_detail__check_out__range=[
                    min_time_checkout_room,
                    max_time_checkout_room,
                ]
            )
        elif min_time_checkout_room:
            queryset = queryset.filter(
                booking__hotel_detail__check_out__gte=min_time_checkout_room
            )
        elif max_time_checkout_room:
            queryset = queryset.filter(
                booking__hotel_detail__check_out__lte=max_time_checkout_room
            )

        min_date_launch_activity = filter_params.get("min_date_launch_activity")
        max_date_launch_activity = filter_params.get("max_date_launch_activity")

        # 🔹 Lọc theo khoảng thời gian hoạt động activity (từ - đến)
        if min_date_launch_activity and max_date_launch_activity:
            queryset = queryset.filter(
                booking__activity_date_detail__date_launch__range=[
                    min_date_launch_activity,
                    max_date_launch_activity,
                ]
            )
        elif min_date_launch_activity:
            queryset = queryset.filter(
                booking__activity_date_detail__date_launch__gte=min_date_launch_activity
            )
        elif max_date_launch_activity:
            queryset = queryset.filter(
                booking__activity_date_detail__date_launch__lte=max_date_launch_activity
            )

        for field, value in filter_params.items():
            if field not in [
                "pageSize",
                "current",
                "booking__service_type",
                "booking__service_ref_id",
                "booking__user_id",
                "owner_hotel_id",
                "event_organizer_activity_id",
                "driver_id",
                "status",
                "sort",
                "activity_id",
                "min_time_checkin_room",
                "max_time_checkin_room",
                "min_time_checkout_room",
                "max_time_checkout_room",
                "min_date_launch_activity",
                "max_date_launch_activity",
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

        if order_fields:
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
            total = revenue
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
