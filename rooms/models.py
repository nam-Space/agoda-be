# from django.db import models
# from hotels.models import Hotel
# from bookings.models import Booking

# # Create your models here.
# class Room(models.Model):
#     hotel = models.ForeignKey(
#         Hotel, on_delete=models.CASCADE, related_name="rooms", null=True
#     )
#     room_type = models.CharField(max_length=100)
#     price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
#     capacity = models.IntegerField()
#     beds = models.IntegerField(default=1)
#     area_m2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
#     available = models.BooleanField(default=True)
#     description = models.TextField(blank=True)

#     def __str__(self):
#         return f"{self.hotel.name} - {self.room_type}"


# # Model để lưu thông tin về hình ảnh phòng
# class RoomImage(models.Model):
#     room = models.ForeignKey("Room", related_name="images", on_delete=models.CASCADE)
#     image = models.ImageField(upload_to="rooms/", null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Image for {self.room.room_type} in {self.room.hotel.name}"

# class RoomBookingDetail(models.Model):
#     booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='hotel_detail')
#     room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_bookings')
#     check_in = models.DateField()
#     check_out = models.DateField()
#     num_guests = models.IntegerField()

#     def __str__(self):
#         return f"HotelBooking for {self.booking.booking_code}"

from django.db import models
from hotels.models import Hotel
from django.utils import timezone
from bookings.models import Booking
from accounts.models import CustomUser


# Create your models here.
class Room(models.Model):
    hotel = models.ForeignKey(
        Hotel, on_delete=models.CASCADE, related_name="rooms", null=True
    )
    room_type = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
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

    @property
    def capacity(self):
        return self.adults_capacity + self.children_capacity

    def __str__(self):
        return f"{self.hotel.name} - {self.room_type}"

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if self.hotel:
    #         self.hotel.update_min_price()
    # ✅ Thêm property hiển thị tổng

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
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.room.room_type})"


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
    owner_hotel = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="room_bookings",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        # ✅ Tự động gán chủ khách sạn khi tạo booking
        if self.room and self.room.hotel and not self.owner_hotel:
            self.owner_hotel = self.room.hotel.owner
        super().save(*args, **kwargs)

    def __str__(self):
        return f"HotelBooking for {self.booking.booking_code}"
