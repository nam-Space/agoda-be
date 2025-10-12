from django.db import models
from hotels.models import Hotel
from bookings.models import Booking

# Create your models here.
class Room(models.Model):
    hotel = models.ForeignKey(
        Hotel, on_delete=models.CASCADE, related_name="rooms", null=True
    )
    room_type = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.IntegerField()
    beds = models.IntegerField(default=1)
    area_m2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    available = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.hotel.name} - {self.room_type}"


# Model để lưu thông tin về hình ảnh phòng
class RoomImage(models.Model):
    room = models.ForeignKey("Room", related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="rooms/", null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.room.room_type} in {self.room.hotel.name}"

class RoomBookingDetail(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='hotel_detail')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_bookings')  
    check_in = models.DateField()
    check_out = models.DateField()
    num_guests = models.IntegerField()

    def __str__(self):
        return f"HotelBooking for {self.booking.booking_code}"