from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from .models import Booking, RefundPolicy
from .serializers import BookingSerializer, RefundPolicySerializer, RefundPolicySerializer
from django.db.models import Q
from rooms.serializers import (
    RoomBookingDetailSerializer,
    RoomBookingDetailCreateSerializer,
)
from cars.serializers import (
    CarBookingDetailSerializer,
    CarBookingDetailCreateSerializer,
)
from flights.serializers import (
    FlightBookingDetailSerializer,
    FlightBookingDetailCreateSerializer,
)
from activities.serializers import (
    ActivityDateBookingDetailSerializer,
    ActivityDateBookingCreateSerializer,
)
from .constants.service_type import ServiceType
from .constants.booking_status import BookingStatus
from rooms.models import RoomBookingDetail
from cars.models import CarBookingDetail
from flights.models import FlightBookingDetail
from activities.models import ActivityDateBookingDetail
from rest_framework_simplejwt.authentication import JWTAuthentication
from payments.models import Payment
from payments.constants.payment_status import PaymentStatus
from payments.constants.payment_method import PaymentMethod
from datetime import datetime, timedelta
import stripe
from django.conf import settings

# Phân trang chung cho Booking và RefundPolicy
class BookingCommonPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "isSuccess": True,
            "message": self.context.get('message', "Fetched data successfully!"),
            "meta": {
                "totalItems": self.page.paginator.count,
                "currentPage": self.page.number,
                "itemsPerPage": self.get_page_size(self.request),
                "totalPages": self.page.paginator.num_pages,
            },
            "data": data,
        })

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền
    pagination_class = BookingCommonPagination

    def get_queryset(self):
        queryset = Booking.objects.all().order_by("-id")
        # Lọc theo email của user hoặc guest_info
        email = self.request.query_params.get("email")
        if email:
            queryset = queryset.filter(
                Q(user__email=email) | Q(guest_info__email=email)
            )
        # Lọc theo service_type
        service_type = self.request.query_params.get("service_type")
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            self.paginator.context = {'message': "Fetched all bookings successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "isSuccess": True,
            "message": "Fetched all bookings successfully!",
            "meta": {
                "totalItems": queryset.count(),
                "pagination": None
            },
            "data": serializer.data,
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        service_type = booking.service_type
        data = None

        if service_type == ServiceType.HOTEL:
            room_data = request.data.get("room_details")
            if room_data:
                room_serializer = RoomBookingDetailCreateSerializer(data=room_data, many=isinstance(room_data, list))
                room_serializer.is_valid(raise_exception=True)
                if isinstance(room_data, list):
                    details = room_serializer.save(booking=booking)
                    booking.service_ref_ids = [d.id for d in details]
                    data = RoomBookingDetailSerializer(details, many=True).data
                else:
                    detail = room_serializer.save(booking=booking)
                    booking.service_ref_ids = [detail.id]
                    data = RoomBookingDetailSerializer(detail).data
                booking.save(update_fields=["service_ref_ids"])

        elif service_type == ServiceType.CAR:
            car_data = request.data.get("car_detail")
            if car_data:
                car_serializer = CarBookingDetailCreateSerializer(data=car_data, many=isinstance(car_data, list))
                car_serializer.is_valid(raise_exception=True)
                if isinstance(car_data, list):
                    details = car_serializer.save(booking=booking)
                    booking.service_ref_ids = [d.id for d in details]
                    data = CarBookingDetailSerializer(details, many=True).data
                else:
                    detail = car_serializer.save(booking=booking)
                    booking.service_ref_ids = [detail.id]
                    data = CarBookingDetailSerializer(detail).data
                booking.save(update_fields=["service_ref_ids"])

        elif service_type == ServiceType.FLIGHT:
            flight_data = request.data.get("flight_detail")
            if flight_data:
                flight_serializer = FlightBookingDetailCreateSerializer(data=flight_data, many=isinstance(flight_data, list))
                flight_serializer.is_valid(raise_exception=True)
                if isinstance(flight_data, list):
                    details = flight_serializer.save(booking=booking)
                    booking.service_ref_ids = [d.id for d in details]
                    data = FlightBookingDetailSerializer(details, many=True).data
                else:
                    detail = flight_serializer.save(booking=booking)
                    booking.service_ref_ids = [detail.id]
                    data = FlightBookingDetailSerializer(detail).data
                booking.save(update_fields=["service_ref_ids"])
        
        elif service_type == ServiceType.ACTIVITY:
            activity_date_data = request.data.get("activity_date_detail")
            if activity_date_data:
                activity_date_serializer = ActivityDateBookingCreateSerializer(
                    data=activity_date_data, many=isinstance(activity_date_data, list)
                )
                activity_date_serializer.is_valid(raise_exception=True)
                if isinstance(activity_date_data, list):
                    details = activity_date_serializer.save(booking=booking)
                    booking.service_ref_ids = [d.id for d in details]
                    data = ActivityDateBookingDetailSerializer(details, many=True).data
                else:
                    detail = activity_date_serializer.save(booking=booking)
                    booking.service_ref_ids = [detail.id]
                    data = ActivityDateBookingDetailSerializer(detail).data
                booking.save(update_fields=["service_ref_ids"])

        return Response(
            {
                "isSuccess": True,
                "message": "Booking created successfully",
                "booking_id": booking.id,
                "booking_code": booking.booking_code,
                "data": data,
            },
            status=status.HTTP_201_CREATED,
        )

    def ensure_datetime(self, dt):
        """Chuyển date hoặc datetime về datetime object"""
        from datetime import time
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt
        # Nếu là date object, convert sang datetime với time min
        from datetime import date
        if isinstance(dt, date):
            return datetime.combine(dt, time.min)
        return dt

    def get_start_time_for_booking(self, booking):
        return self.ensure_datetime(booking.created_at)

    def calculate_refund_amount(self, booking):
        """Tính toán số tiền hoàn lại dựa trên policy, promotion và thời gian"""
        # Lấy policy cho service type
        try:
            policy = RefundPolicy.objects.filter(
                service_type=booking.service_type,
                is_active=True
            ).order_by('-hours_before_start').first()
        except RefundPolicy.DoesNotExist:
            policy = None
        
        if not policy:
            # Nếu không có policy, mặc định hoàn 100%
            return booking.final_price
        
        # Lấy thời gian bắt đầu
        start_time = self.get_start_time_for_booking(booking)
        if not start_time:
            # Nếu không lấy được thời gian, hoàn 100%
            return booking.final_price
        
        # Tính số giờ trước khi bắt đầu
        # Đảm bảo start_time là datetime object
        start_time = self.ensure_datetime(start_time)
        if not start_time:
            return booking.final_price
        
        # Lấy timezone từ start_time nếu có, nếu không dùng timezone naive
        try:
            if hasattr(start_time, 'tzinfo') and start_time.tzinfo:
                from django.utils import timezone as django_timezone
                now = django_timezone.now()
            else:
                now = datetime.now()
        except:
            now = datetime.now()
        
        hours_before = (start_time - now).total_seconds() / 3600
        
        # Kiểm tra policy có áp dụng không
        if policy.hours_before_start and hours_before < policy.hours_before_start:
            # Quá thời hạn hủy, không hoàn tiền
            if policy.policy_type == RefundPolicy.PolicyType.NO_REFUND:
                return 0.0
            # Hoặc áp dụng policy khác nếu có
        
        # Tính refund dựa trên policy type
        if policy.policy_type == RefundPolicy.PolicyType.NO_REFUND:
            return 0.0
        elif policy.policy_type == RefundPolicy.PolicyType.FULL_REFUND:
            refund = booking.final_price
        elif policy.policy_type == RefundPolicy.PolicyType.PARTIAL_REFUND:
            if policy.refund_percentage:
                refund = booking.final_price * (policy.refund_percentage / 100)
            elif policy.refund_amount:
                refund = min(policy.refund_amount, booking.final_price)
            else:
                refund = booking.final_price * 0.5  # Mặc định 50%
        else:
            refund = booking.final_price
        
        # Trừ đi discount amount từ promotion (nếu có)
        # Vì promotion đã được áp dụng, không hoàn lại phần discount
        if booking.discount_amount > 0:
            refund = max(0, refund - booking.discount_amount)
        
        return round(refund, 2)

    def process_payment_refund(self, booking, refund_amount):
        """Gọi API refund của payment gateway nếu đã thanh toán"""
        payments = Payment.objects.filter(
            booking=booking,
            status__in=[PaymentStatus.PAID, PaymentStatus.SUCCESS]
        )
        
        if not payments.exists():
            return None
        
        payment = payments.first()
        
        # Nếu thanh toán qua Stripe
        if payment.method == PaymentMethod.ONLINE and payment.transaction_id:
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                # Refund qua Stripe
                refund = stripe.Refund.create(
                    payment_intent=payment.transaction_id,
                    amount=int(refund_amount * 100),  # Stripe tính theo cent
                )
                return refund
            except Exception as e:
                # Log error nhưng vẫn tiếp tục
                print(f"Stripe refund error: {e}")
                return None
        
        # Có thể thêm VNPAY, MOMO ở đây
        return None

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_booking(self, request, pk=None):
        """API hủy booking"""
        try:
            booking = self.get_object()
        except Booking.DoesNotExist:
            return Response(
                {"isSuccess": False, "message": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Kiểm tra trạng thái booking
        if booking.status == BookingStatus.CANCELLED:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Booking đã bị hủy rồi"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if booking.status == BookingStatus.COMPLETED:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Không thể hủy booking đã hoàn thành"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Chỉ cho hủy nếu ở trạng thái PENDING, CONFIRMED hoặc payment_status là UNPAID
        if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
            if booking.payment_status != PaymentStatus.UNPAID:
                return Response(
                    {
                        "isSuccess": False,
                        "message": "Chỉ có thể hủy booking ở trạng thái PENDING, CONFIRMED hoặc UNPAID"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Tính toán refund amount
        refund_amount = self.calculate_refund_amount(booking)
        
        # Nếu đã thanh toán, gọi API refund
        refund_result = None
        if booking.payment_status in [PaymentStatus.PAID, PaymentStatus.SUCCESS]:
            refund_result = self.process_payment_refund(booking, refund_amount)
        
        # Cập nhật booking
        booking.status = BookingStatus.CANCELLED
        if refund_amount > 0:
            booking.payment_status = PaymentStatus.REFUNDED
            booking.refund_amount = refund_amount
        else:
            booking.payment_status = PaymentStatus.CANCELLED
        
        # Giữ nguyên final_price để audit
        booking.save()
        
        return Response(
            {
                "isSuccess": True,
                "message": "Booking đã được hủy thành công",
                "booking_id": booking.id,
                "booking_code": booking.booking_code,
                "status": booking.get_status_display(),
                "payment_status": booking.get_payment_status_display(),
                "refund_amount": refund_amount,
                "final_price": booking.final_price,  # Giữ nguyên để audit
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='rebook')
    def rebook_booking(self, request, pk=None):
        """API đặt lại booking từ booking cũ"""
        try:
            old_booking = self.get_object()
        except Booking.DoesNotExist:
            return Response(
                {"isSuccess": False, "message": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Kiểm tra booking đã hủy chưa
        if old_booking.status != BookingStatus.CANCELLED:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Chỉ có thể đặt lại từ booking đã hủy"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Clone dữ liệu booking
        new_booking_data = {
            'service_type': old_booking.service_type,
            'service_ref_ids': old_booking.service_ref_ids.copy() if old_booking.service_ref_ids else [],
            'user': old_booking.user,
            'total_price': old_booking.total_price,  # Có thể tính lại sau
            'discount_amount': 0.0,  # Reset discount, sẽ tính lại
            'final_price': old_booking.total_price,  # Tạm thời, sẽ tính lại
            'status': BookingStatus.PENDING,
            'payment_status': PaymentStatus.PENDING,
            'refund_amount': None,  # Không copy refund_amount
        }
        
        # Tạo booking mới
        new_booking = Booking.objects.create(**new_booking_data)
        
        # Copy guest info nếu có
        if hasattr(old_booking, 'guest_info'):
            from .models import GuestInfo
            old_guest = old_booking.guest_info
            GuestInfo.objects.create(
                booking=new_booking,
                full_name=old_guest.full_name,
                email=old_guest.email,
                phone=old_guest.phone,
                country=old_guest.country,
                special_request=old_guest.special_request,
            )
        
        # Clone service details dựa trên service_type
        service_type = old_booking.service_type
        data = None
        
        if service_type == ServiceType.HOTEL:
            # Số lượng phòng lấy từ request, nếu không có thì dùng từ old_detail hoặc mặc định 1
            num_rooms = int(request.data.get("num_rooms", 1))
            old_details = RoomBookingDetail.objects.filter(booking=old_booking)
            if old_details.exists():
                new_details = []
                old_detail = old_details.first()  # Lấy detail đầu tiên làm mẫu
                
                # Tạo đúng số bản ghi RoomBookingDetail mới theo num_rooms
                for i in range(num_rooms):
                    new_detail = RoomBookingDetail.objects.create(
                        booking=new_booking,
                        room=old_detail.room,
                        check_in=old_detail.check_in,
                        check_out=old_detail.check_out,
                        num_guests=old_detail.num_guests,
                        owner_hotel=old_detail.owner_hotel,
                        room_type=old_detail.room.room_type if old_detail.room else (old_detail.room_type or "N/A"),
                        room_count=1,  # Mỗi detail là 1 phòng
                    )
                    new_details.append(new_detail)
                
                new_booking.service_ref_ids = [d.id for d in new_details]
                new_booking.save(update_fields=["service_ref_ids"])
                
                # Serialize và thêm room_type vào response
                serialized_data = RoomBookingDetailSerializer(new_details, many=True).data
                data = [
                    {
                        **item,
                        "room_type": detail.room.room_type if detail.room else (detail.room_type or "N/A")
                    }
                    for item, detail in zip(serialized_data, new_details)
                ]
        
        elif service_type == ServiceType.CAR:
            old_details = CarBookingDetail.objects.filter(booking=old_booking)
            if old_details.exists():
                new_details = []
                for old_detail in old_details:
                    new_detail = CarBookingDetail.objects.create(
                        booking=new_booking,
                        car=old_detail.car,
                        pickup_location=old_detail.pickup_location,
                        dropoff_location=old_detail.dropoff_location,
                        lat1=old_detail.lat1,
                        lng1=old_detail.lng1,
                        lat2=old_detail.lat2,
                        lng2=old_detail.lng2,
                        pickup_datetime=old_detail.pickup_datetime,
                        driver_required=old_detail.driver_required,
                        distance_km=old_detail.distance_km,
                        total_time_estimate=old_detail.total_time_estimate,
                        passenger_quantity_booking=old_detail.passenger_quantity_booking,
                        driver=old_detail.driver,
                        total_price=old_detail.total_price,
                        discount_amount=0.0,  # Reset discount
                        final_price=old_detail.total_price,  # Tạm thời
                    )
                    new_details.append(new_detail)
                new_booking.service_ref_ids = [d.id for d in new_details]
                new_booking.save(update_fields=["service_ref_ids"])
                data = CarBookingDetailSerializer(new_details, many=True).data
        
        elif service_type == ServiceType.FLIGHT:
            old_details = FlightBookingDetail.objects.filter(booking=old_booking)
            if old_details.exists():
                new_details = []
                for old_detail in old_details:
                    new_detail_data = {
                        'booking': new_booking,
                        'flight': old_detail.flight,
                    }
                    for field in old_detail._meta.fields:
                        if field.name not in ['id', 'booking', 'flight']:
                            if hasattr(old_detail, field.name):
                                new_detail_data[field.name] = getattr(old_detail, field.name)
                    new_detail = FlightBookingDetail.objects.create(**new_detail_data)
                    new_details.append(new_detail)
                new_booking.service_ref_ids = [d.id for d in new_details]
                new_booking.save(update_fields=["service_ref_ids"])
                data = FlightBookingDetailSerializer(new_details, many=True).data
        
        elif service_type == ServiceType.ACTIVITY:
            old_details = ActivityDateBookingDetail.objects.filter(booking=old_booking)
            if old_details.exists():
                new_details = []
                for old_detail in old_details:
                    new_detail_data = {
                        'booking': new_booking,
                        'activity_date': old_detail.activity_date,
                    }
                    for field in old_detail._meta.fields:
                        if field.name not in ['id', 'booking', 'activity_date']:
                            if hasattr(old_detail, field.name):
                                new_detail_data[field.name] = getattr(old_detail, field.name)
                    new_detail = ActivityDateBookingDetail.objects.create(**new_detail_data)
                    new_details.append(new_detail)
                new_booking.service_ref_ids = [d.id for d in new_details]
                new_booking.save(update_fields=["service_ref_ids"])
                data = ActivityDateBookingDetailSerializer(new_details, many=True).data
        
        # TODO: Tính lại giá nếu giá thay đổi theo ngày hiện tại
        # Có thể gọi lại logic tính giá từ service tương ứng
        
        # TODO: Tính lại promotion mới (vì có thể hết hạn)
        # Có thể để user chọn promotion mới hoặc tự động tìm promotion active
        
        return Response(
            {
                "isSuccess": True,
                "message": "Booking đã được đặt lại thành công",
                "old_booking_id": old_booking.id,
                "old_booking_code": old_booking.booking_code,
                "new_booking_id": new_booking.id,
                "new_booking_code": new_booking.booking_code,
                "data": data,
            },
            status=status.HTTP_201_CREATED,
        )



class RefundPolicyViewSet(viewsets.ModelViewSet):
    """API CRUD cho RefundPolicy"""
    queryset = RefundPolicy.objects.all()
    serializer_class = RefundPolicySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Có thể thêm permission sau
    pagination_class = BookingCommonPagination

    def get_queryset(self):
        queryset = RefundPolicy.objects.all().order_by("-id")
        # Lọc theo service_type
        service_type = self.request.query_params.get("service_type")
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        # Lọc theo is_active
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            is_active_bool = is_active.lower() == "true"
            queryset = queryset.filter(is_active=is_active_bool)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            self.paginator.context = {'message': "Fetched all refund policies successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "isSuccess": True,
            "message": "Fetched all refund policies successfully!",
            "meta": {
                "totalItems": queryset.count(),
                "pagination": None
            },
            "data": serializer.data,
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refund_policy = serializer.save()
        
        return Response(
            {
                "isSuccess": True,
                "message": "RefundPolicy created successfully",
                "data": RefundPolicySerializer(refund_policy).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        refund_policy = serializer.save()
        
        return Response(
            {
                "isSuccess": True,
                "message": "RefundPolicy updated successfully",
                "data": RefundPolicySerializer(refund_policy).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "RefundPolicy deleted successfully",
            },
            status=status.HTTP_200_OK,
        )
