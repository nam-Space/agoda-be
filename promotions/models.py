from django.db import models

class PromotionType(models.IntegerChoices):
    HOTEL = 1, "Chỗ ở"
    FLIGHT = 2, "Chuyến bay"
    ACTIVITY = 3, "Hoạt động"
    CAR = 4, "Xe"

class Promotion(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    promotion_type = models.IntegerField(
        choices=PromotionType.choices,
        default=PromotionType.HOTEL,
    )

    image = models.ImageField(
        upload_to='promotions_images/',  # folder lưu file trong MEDIA_ROOT
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_promotion_type_display()})"


class FlightPromotion(models.Model):
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="flight_promotions"
    )
    flight = models.ForeignKey("flights.Flight", on_delete=models.CASCADE, related_name="promotions"
    , null=True, blank=True,
    )
    
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.promotion.title} -> Flight: {self.flight_id if self.flight else 'N/A'}"

class ActivityPromotion(models.Model):
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="activity_promotions"
    )
    activity = models.ForeignKey("activities.Activity", on_delete=models.CASCADE, related_name="promotions"
    , null=True, blank=True,
    )

    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.promotion.title} -> Activity: {self.activity.name}"


class RoomPromotion(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="room_promotions")
    room = models.ForeignKey("rooms.Room", on_delete=models.CASCADE, related_name="promotions")

    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.promotion.title} -> Room: {self.room.room_type}"


class CarPromotion(models.Model):
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="car_promotions"
    )
    car = models.ForeignKey("cars.Car", on_delete=models.CASCADE, related_name="promotions"
    , null=True, blank=True,
    )

    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.promotion.title} -> Car: {self.car.name if self.car else 'N/A'}"


