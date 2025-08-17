from django.db import models


class Hotel(models.Model):
    name = models.CharField(max_length=255)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    avg_star = models.FloatField(default=0.0)
    rating_count = models.PositiveIntegerField(default=0)

    regulation = models.TextField(blank=True)
    facilities = models.JSONField(blank=True, null=True)
    amenities = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="rooms")
    room_type = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.IntegerField()
    beds = models.IntegerField(default=1)
    area_m2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    available = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.hotel.name} - {self.room_type}"


# Model để lưu thông tin về hình ảnh khách sạn
class HotelImage(models.Model):
    hotel = models.ForeignKey("Hotel", related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="hotel_images/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.hotel.name}"


# Model để lưu thông tin về hình ảnh phòng
class RoomImage(models.Model):
    room = models.ForeignKey("Room", related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="room_images/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.room.room_type} in {self.room.hotel.name}"
