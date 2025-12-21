from django.db import models
from hotels.models import Hotel
from django.utils import timezone
from bookings.models import Booking
from accounts.models import CustomUser
from datetime import timedelta


# Create your models here.
class Room(models.Model):
    hotel = models.ForeignKey(
        Hotel, on_delete=models.CASCADE, related_name="rooms", null=True
    )
    room_type = models.CharField(max_length=100)
    price_per_night = models.FloatField(default=0.0)
    stay_type = models.CharField(max_length=50, choices=[('overnight', 'Overnight'), ('dayuse', 'Day Use')], default='overnight')
    price_per_day = models.FloatField(default=0.0)  # For day use
    dayuse_duration_hours = models.PositiveIntegerField(default=0)  # Hours for day use
    # capacity = models.IntegerField()

    # Capacity chia thành adults và children
    adults_capacity = models.PositiveIntegerField(default=1)
    children_capacity = models.PositiveIntegerField(default=0)

    # Số lượng phòng
    total_rooms = models.PositiveIntegerField(default=1)
    available_rooms = models.PositiveIntegerField(default=1)

    # Ngày phòng có sẵn
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    beds = models.IntegerField(default=1)
    area_m2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    available = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def capacity(self):
        return self.adults_capacity + self.children_capacity

    def __str__(self):
        return f"{self.hotel.name} - {self.room_type}"

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        if self.available_rooms == 0 or (self.end_date and today > self.end_date):
            self.available = False
        else:
            self.available = True
        super().save(*args, **kwargs)
        if self.hotel:
            self.hotel.update_min_price()

    def decrease_available_rooms(self, num=1):
        """Gọi khi booking thành công"""
        self.available_rooms = max(0, self.available_rooms - num)
        self.save()

    def delete(self, *args, **kwargs):
        hotel = self.hotel
        super().delete(*args, **kwargs)
        if hotel:
            hotel.update_min_price()

    def get_active_promotion(self):
        from django.utils import timezone

        now = timezone.now()
        room_promotions = self.promotions.select_related("promotion").all()

        # Chỉ lấy những promotion đang active
        active_promos = [
            rp
            for rp in room_promotions
            if rp.promotion.is_active
            and rp.promotion.start_date <= now <= rp.promotion.end_date
        ]

        if not active_promos:
            return None

        # Lấy promotion có discount lớn nhất
        best_promo = max(
            active_promos,
            key=lambda rp: (
                rp.discount_percent
                if rp.discount_percent is not None
                else (rp.promotion.discount_percent or 0)
            ),
        )

        promo = best_promo.promotion
        return {
            "id": promo.id,
            "title": promo.title,
            "discount_percent": best_promo.discount_percent or promo.discount_percent,
            "discount_amount": best_promo.discount_amount or promo.discount_amount,
            "start_date": promo.start_date,
            "end_date": promo.end_date,
        }


# Model để lưu thông tin về hình ảnh phòng
class RoomImage(models.Model):
    room = models.ForeignKey("Room", related_name="images", on_delete=models.CASCADE)
    image = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.room.room_type} in {self.room.hotel.name}"


# ✅ Bảng phụ lưu tiện ích phòng
class RoomAmenity(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="amenities")
    name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.room.room_type})"


# Thông tin chi tiết đặt phòng khách sạn
class RoomBookingDetail(models.Model):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="hotel_detail"
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="room_bookings"
    )
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    num_guests = models.IntegerField()
    # Thêm loại phòng và số lượng phòng
    room_type = models.CharField(
        max_length=100, blank=True, null=True, help_text="Loại phòng (copy từ Room)"
    )
    room_count = models.PositiveIntegerField(default=1, help_text="Số lượng phòng đặt")
    owner_hotel = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="room_bookings",
        null=True,
        blank=True,
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.FloatField(default=0.0)
    final_price = models.FloatField(default=0.0)

    def save(self, *args, **kwargs):
        # Tự động gán loại phòng nếu chưa có
        if not self.room_type and self.room:
            self.room_type = self.room.room_type
        # Tự động gán chủ khách sạn khi tạo booking
        if self.room and self.room.hotel and not self.owner_hotel:
            self.owner_hotel = self.room.hotel.owner

        # Tính tổng tiền phòng dựa trên stay_type
        if self.room and self.check_in and self.check_out:
            if self.room.stay_type == 'dayuse':
                # Cho dayuse, dùng price_per_day, và có lẽ num_days = 1
                self.total_price = float(self.room.price_per_day) * self.room_count
            else:
                # Overnight: price_per_night * num_nights
                check_in = self.check_in
                check_out = self.check_out
                if hasattr(check_in, "date"):
                    check_in = check_in.date()
                if hasattr(check_out, "date"):
                    check_out = check_out.date()
                num_nights = (check_out - check_in).days
                if num_nights < 1:
                    num_nights = 1
                self.total_price = (
                    float(self.room.price_per_night) * num_nights * self.room_count
                )
        else:
            self.total_price = 0

        # Tính giảm giá nếu có promotion (ưu tiên lấy promotion từ room)
        promo = None
        if self.room and hasattr(self.room, "get_active_promotion"):
            promo = self.room.get_active_promotion()
        if promo:
            percent = float(promo.get("discount_percent") or 0)
            amount = float(promo.get("discount_amount") or 0)
            if amount > 0:
                self.discount_amount = min(amount, float(self.total_price))
            elif percent > 0:
                self.discount_amount = float(self.total_price) * percent / 100
            else:
                self.discount_amount = 0
            self.final_price = float(self.total_price) - self.discount_amount
        else:
            self.discount_amount = 0
            self.final_price = float(self.total_price)

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Khi booking mới được tạo, giảm available_rooms
        if is_new and self.room and self.room_count > 0:
            self.room.decrease_available_rooms(self.room_count)

        # Cập nhật tổng discount, final_price, total_price lên Booking (nếu có nhiều RoomBookingDetail thì sum lại, ở đây là OneToOne nên chỉ lấy 1)
        if self.booking:
            self.booking.discount_amount = self.discount_amount
            self.booking.final_price = self.final_price
            self.booking.total_price = self.total_price
            self.booking.save(
                update_fields=["discount_amount", "final_price", "total_price"]
            )

    def __str__(self):
        return f"HotelBooking for {self.booking.booking_code} | {self.room_type} x {self.room_count}"
