from django.db import models
from cities.models import City
from django.db.models import Avg
from django.utils import timezone

class Hotel(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="hotels", null=True
    )
    owner = models.OneToOneField( 
        "accounts.CustomUser",
        on_delete=models.SET_NULL,  
        related_name="hotel",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    nearbyLocation = models.TextField(blank=True, null=True)
    point = models.FloatField(default=0.0)
    mostFeature = models.TextField(blank=True, null=True)
    facilities = models.TextField(blank=True, null=True)
    withUs = models.TextField(blank=True, null=True)
    usefulInformation = models.TextField(blank=True, null=True)
    amenitiesAndFacilities = models.TextField(blank=True, null=True)
    locationInfo = models.TextField(null=True, blank=True)
    regulation = models.TextField(blank=True)
    avg_star = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    min_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0
    )

    def __str__(self):
        return self.name

    def get_active_promotion(self):
        now = timezone.now()
        hotel_promotions = self.promotions.select_related("promotion").all()

        # Chỉ lấy những promotion đang active
        active_promos = [
            hp for hp in hotel_promotions
            if hp.promotion.is_active and hp.promotion.start_date <= now <= hp.promotion.end_date
        ]
        
        if not active_promos:
            return None

        # Lấy promotion có effective discount lớn nhất
        best_promo = max(
            active_promos,
            key=lambda hp: hp.custom_discount_percent if hp.custom_discount_percent is not None else hp.promotion.discount_percent
        )

        promo = best_promo.promotion
        return {
            "title": promo.title,
            "discount_percent": best_promo.custom_discount_percent or promo.discount_percent,
            "discount_amount": best_promo.custom_discount_amount or promo.discount_amount,
            "start_date": promo.start_date,
            "end_date": promo.end_date,
        }

    # ✅ Hàm tự cập nhật giá trung bình của các phòng còn available
    def update_min_price(self):
        from rooms.models import Room

        avg_price = (
            Room.objects.filter(hotel=self, available=True)
            .aggregate(avg_price=models.Avg("price_per_night"))
            .get("avg_price")
        )
        self.min_price = avg_price or 0
        self.save(update_fields=["min_price"])


# Model để lưu thông tin về hình ảnh khách sạn
class HotelImage(models.Model):
    hotel = models.ForeignKey("Hotel", related_name="images", on_delete=models.CASCADE)
    image = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.hotel.name}"
