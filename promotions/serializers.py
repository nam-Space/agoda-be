from rest_framework import serializers
from .models import Promotion, HotelPromotion, FlightPromotion

class HotelPromotionSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source="hotel.name", read_only=True)

    class Meta:
        model = HotelPromotion
        fields = ["id", "promotion", "hotel", "hotel_name"]


class FlightPromotionSerializer(serializers.ModelSerializer):
    airport_name = serializers.CharField(source="airport.name", read_only=True)

    class Meta:
        model = FlightPromotion
        fields = ["id", "promotion", "airport", "airport_name"]


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