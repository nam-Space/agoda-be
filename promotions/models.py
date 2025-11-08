from django.db import models

class PromotionType(models.IntegerChoices):
    HOTEL = 1, "Chỗ ở"
    FLIGHT = 2, "Chuyến bay"
    ACTIVITY = 3, "Hoạt động"


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
        upload_to='promotions/',  # folder lưu file trong MEDIA_ROOT
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_promotion_type_display()})"


class HotelPromotion(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="hotel_promotions")
    hotel = models.ForeignKey("hotels.Hotel", on_delete=models.CASCADE, related_name="promotions")

    # Cho phép khách sạn tùy chỉnh
    custom_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    custom_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.promotion.title} -> Hotel: {self.hotel.name}"


class FlightPromotion(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="flight_promotions")
    airport = models.ForeignKey("airports.Airport", on_delete=models.CASCADE, related_name="promotions")

    # Cho phép sân bay tùy chỉnh
    custom_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    custom_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.promotion.title} -> Flight: {self.airport.name}"


# class ActivityPromotion(models.Model):
#     promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="activity_promotions")
#     activity = models.ForeignKey("activities.Activity", on_delete=models.CASCADE, related_name="promotions")

#     def __str__(self):
#         return f"{self.promotion.title} -> Activity: {self.activity.name}"
