from rest_framework import serializers
from .models import Promotion, HotelPromotion, FlightPromotion
from hotels.models import Hotel 
from hotels.serializers import HotelSerializer
from airports.serializers import AirportSerializer 

class HotelSimpleSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            "id", 
            "name", 
            "thumbnail", 
            "min_price", 
            "location",
            "avg_star",
            "point",
            "review_count",
            "city"
            ]

    def get_thumbnail(self, obj):
        if obj.images.exists():
            return obj.images.first().image
        return None

class HotelPromotionSerializer(serializers.ModelSerializer):
    hotel = HotelSimpleSerializer(read_only=True)
    hotel_id = serializers.PrimaryKeyRelatedField(queryset=Hotel.objects.all(), source="hotel", write_only=True)
    # hotel_name = serializers.CharField(source="hotel.name", read_only=True)
    effective_discount_percent = serializers.SerializerMethodField()
    effective_discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = HotelPromotion
        fields = [
            "id",
            "promotion",
            "hotel",
            "hotel_id",
            # "hotel_name",
            "custom_discount_percent",
            "custom_discount_amount",
            "effective_discount_percent",
            "effective_discount_amount",
        ]
    def get_effective_discount_percent(self, obj):
        return obj.custom_discount_percent or obj.promotion.discount_percent

    def get_effective_discount_amount(self, obj):
        return obj.custom_discount_amount or obj.promotion.discount_amount

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        # Lọc city
        city_id = self.context.get("city_id")
        if city_id and str(instance.hotel.city_id) != str(city_id):
            return None

        # Lọc active promotion
        # active_only = self.context.get("active_only", True)
        # now = timezone.now()
        # promo = instance.promotion
        # if active_only and not (promo.is_active and promo.start_date <= now <= promo.end_date):
        #     return None

        # Lọc rating và giá
        min_rating = self.context.get("min_rating")
        min_price = self.context.get("min_price")
        hotel = instance.hotel

        if min_rating and hotel.avg_star < float(min_rating):
            return None
        if min_price and hotel.min_price < float(min_price):
            return None

        data.pop("custom_discount_percent", None)
        data.pop("custom_discount_amount", None)

        return data


class FlightPromotionSerializer(serializers.ModelSerializer):
    airport = AirportSerializer(read_only=True)
    # airport_name = serializers.CharField(source="airport.name", read_only=True)
    effective_discount_percent = serializers.SerializerMethodField()
    effective_discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = FlightPromotion
        fields = [
            "id",
            "promotion",
            "airport",
            # "airport_name",
            "custom_discount_percent",
            "custom_discount_amount",
            "effective_discount_percent",
            "effective_discount_amount",
        ]
    def get_effective_discount_percent(self, obj):
        return obj.custom_discount_percent or obj.promotion.discount_percent

    def get_effective_discount_amount(self, obj):
        return obj.custom_discount_amount or obj.promotion.discount_amount
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        data.pop("custom_discount_percent", None)
        data.pop("custom_discount_amount", None)

        return data

# class ActivityPromotionSerializer(serializers.ModelSerializer):
#     activity_name = serializers.CharField(source="activity.name", read_only=True)

#     class Meta:
#         model = ActivityPromotion
#         fields = ["id", "promotion", "activity", "activity_name"]


class PromotionSerializer(serializers.ModelSerializer):
    promotion_type_display = serializers.CharField(source="get_promotion_type_display", read_only=True)
    hotel_promotions = HotelPromotionSerializer(many=True, read_only=True)
    flight_promotions = FlightPromotionSerializer(many=True, read_only=True)
    # activity_promotions = ActivityPromotionSerializer(many=True, read_only=True)
    image = serializers.ImageField(required=False)

    class Meta:
        model = Promotion
        fields = [
            "id",
            "title",
            "description",
            "discount_percent",
            "discount_amount",
            "start_date",
            "end_date",
            "is_active",
            "promotion_type",
            "promotion_type_display",
            "image", 
            "created_at",
            "hotel_promotions",
            "flight_promotions",
            # "activity_promotions",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.promotion_type == 1:  # HOTEL
            data.pop("flight_promotions", None)
        elif instance.promotion_type == 2:  # FLIGHT
            data.pop("hotel_promotions", None)
        # Nếu có ACTIVITY thì tương tự

        return data