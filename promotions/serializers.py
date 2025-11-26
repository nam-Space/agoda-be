from rest_framework import serializers
from .models import Promotion, FlightPromotion, ActivityPromotion, RoomPromotion, CarPromotion
from flights.serializers import FlightSimpleSerializer
from cars.models import Car
from datetime import datetime

class FlightPromotionSerializer(serializers.ModelSerializer):
    flight = FlightSimpleSerializer(read_only=True)
    effective_discount_percent = serializers.SerializerMethodField()
    effective_discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = FlightPromotion
        fields = [
            "id",
            "promotion",
            "flight",
            "discount_percent",
            "discount_amount",
            "effective_discount_percent",
            "effective_discount_amount",
        ]
    def get_effective_discount_percent(self, obj):
        return obj.discount_percent or obj.promotion.discount_percent

    def get_effective_discount_amount(self, obj):
        return obj.discount_amount or obj.promotion.discount_amount
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        flight = instance.flight

        # Get first and last leg for filtering
        first_leg = flight.legs.order_by('departure_time').first()
        last_leg = flight.legs.order_by('arrival_time').last()
        
        if not first_leg or not last_leg:
            return None

        # Filters from context
        origin_id = self.context.get("origin_id")
        if origin_id and str(first_leg.departure_airport_id) != str(origin_id):
            return None

        destination_id = self.context.get("destination_id")
        if destination_id and str(last_leg.arrival_airport_id) != str(destination_id):
            return None

        # Filter by airline_id
        airline_id = self.context.get("airline_id")
        if airline_id and str(flight.airline_id) != str(airline_id):
            return None

        # Filter by start_date (departure date >= start_date)
        start_date = self.context.get("start_date")
        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(start_date).date()
                if first_leg.departure_time.date() < start_date_obj:
                    return None
            except Exception:
                pass

        data.pop("discount_percent", None)
        data.pop("discount_amount", None)

        return data

class ActivityPromotionSerializer(serializers.ModelSerializer):
    activity_date_id = serializers.IntegerField(source='activity_date.id', read_only=True, allow_null=True)
    effective_discount_percent = serializers.SerializerMethodField()
    effective_discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = ActivityPromotion
        fields = [
            "id",
            "promotion",
            "activity_date",
            "activity_date_id",
            "discount_percent",
            "discount_amount",
            "effective_discount_percent",
            "effective_discount_amount",
        ]

    def get_effective_discount_percent(self, obj):
        return obj.discount_percent or obj.promotion.discount_percent

    def get_effective_discount_amount(self, obj):
        return obj.discount_amount or obj.promotion.discount_amount

    def to_representation(self, instance):
        data = super().to_representation(instance)
        activity = getattr(instance, "activity", None)
        if not activity:
            return None

        # get filters from context
        city_id = self.context.get("city_id")
        category = self.context.get("category")
        min_price = self.context.get("min_price")
        max_price = self.context.get("max_price")
        min_rating = self.context.get("min_rating")
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")
        search = self.context.get("search")

        # basic checks
        if city_id and str(getattr(activity, "city_id", "")) != str(city_id):
            return None
        if category and getattr(activity, "category", "") != category:
            return None
        if min_rating and float(getattr(activity, "avg_star", 0) or 0) < float(min_rating):
            return None
        if min_price:
            try:
                if float(getattr(activity, "avg_price", 0) or 0) < float(min_price):
                    return None
            except Exception:
                pass
        if max_price:
            try:
                if float(getattr(activity, "avg_price", 0) or 0) > float(max_price):
                    return None
            except Exception:
                pass

        # optional date range: check related ActivityDate if exists
        if start_date or end_date:
            try:
                dates_qs = activity.activitypackage_set.prefetch_related("activitydate_set").all()
                has_date_in_range = False
                for pkg in dates_qs:
                    for ad in getattr(pkg, "activitydate_set", []).all():
                        ad_date = getattr(ad, "date_launch", None)
                        if not ad_date:
                            continue
                        ad_dt = ad_date.date() if hasattr(ad_date, "date") else ad_date
                        if start_date:
                            sd = datetime.fromisoformat(start_date).date()
                            if ad_dt < sd:
                                continue
                        if end_date:
                            ed = datetime.fromisoformat(end_date).date()
                            if ad_dt > ed:
                                continue
                        has_date_in_range = True
                        break
                    if has_date_in_range:
                        break
                if (start_date or end_date) and not has_date_in_range:
                    return None
            except Exception:
                # if anything fails, skip date filtering
                pass

        if search:
            s = search.lower()
            if s not in (getattr(activity, "name", "") or "").lower() and s not in (getattr(activity, "short_description", "") or "").lower():
                return None

        # remove internal fields if needed
        data.pop("some_internal_field", None)

        return data

class RoomPromotionSerializer(serializers.ModelSerializer):
    effective_discount_percent = serializers.SerializerMethodField()
    effective_discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = RoomPromotion
        fields = [
            "id",
            "promotion",
            "room",
            "discount_percent",
            "discount_amount",
            "effective_discount_percent",
            "effective_discount_amount",
        ]
        read_only_fields = ["room"]

    def get_effective_discount_percent(self, obj):
        return obj.discount_percent or obj.promotion.discount_percent

    def get_effective_discount_amount(self, obj):
        return obj.discount_amount or obj.promotion.discount_amount

class CarSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ["id", "name", "capacity", "luggage", "price_per_km", "avg_star", "image"]

class CarPromotionSerializer(serializers.ModelSerializer):
    car = CarSimpleSerializer(read_only=True)
    effective_discount_percent = serializers.SerializerMethodField()
    effective_discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = CarPromotion
        fields = [
            "id",
            "promotion",
            "car",
            "discount_percent",
            "discount_amount",
            "effective_discount_percent",
            "effective_discount_amount",
        ]

    def get_effective_discount_percent(self, obj):
        return obj.discount_percent or obj.promotion.discount_percent

    def get_effective_discount_amount(self, obj):
        return obj.discount_amount or obj.promotion.discount_amount

# Serializers cho cấu trúc mới khi tạo promotion
class RoomPromotionItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

class FlightPromotionItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

class ActivityDatePromotionItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

class CarPromotionItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

class PromotionSerializer(serializers.ModelSerializer):
    promotion_type_display = serializers.CharField(source="get_promotion_type_display", read_only=True)
    flight_promotions = FlightPromotionSerializer(many=True, read_only=True)
    activity_promotions = ActivityPromotionSerializer(many=True, read_only=True)
    room_promotions = RoomPromotionSerializer(many=True, read_only=True)
    car_promotions = CarPromotionSerializer(many=True, read_only=True)
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
            "flight_promotions",
            "activity_promotions",
            "room_promotions",
            "car_promotions",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.promotion_type == 1:  # HOTEL
            data.pop("flight_promotions", None)
            data.pop("activity_promotions", None)
            data.pop("car_promotions", None)
        elif instance.promotion_type == 2:  # FLIGHT
            data.pop("activity_promotions", None)
            data.pop("room_promotions", None)
            data.pop("car_promotions", None)
        elif instance.promotion_type == 3:  # ACTIVITY
            data.pop("flight_promotions", None)
            data.pop("room_promotions", None)
            data.pop("car_promotions", None)
        elif instance.promotion_type == 4:  # CAR
            data.pop("flight_promotions", None)
            data.pop("activity_promotions", None)
            data.pop("room_promotions", None)

        return data

# Serializer chung để tạo promotion với cấu trúc mới
class PromotionCreateSerializer(serializers.Serializer):
    promotion_id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=['hotel', 'flight', 'activity', 'car'])
    
    # Hotel fields
    hotel_id = serializers.IntegerField(required=False)
    rooms = RoomPromotionItemSerializer(many=True, required=False)
    
    # Flight fields
    airline_id = serializers.IntegerField(required=False)
    flights = FlightPromotionItemSerializer(many=True, required=False)
    
    # Activity fields (chỉ dùng cho ActivityDate)
    activity_id = serializers.IntegerField(required=False)
    activity_package = serializers.IntegerField(required=False)
    actDates = ActivityDatePromotionItemSerializer(many=True, required=False)
    
    # Car fields
    cars = CarPromotionItemSerializer(many=True, required=False)
    
    def validate(self, data):
        promotion_type = data.get('type')
        
        if promotion_type == 'hotel':
            if not data.get('hotel_id'):
                raise serializers.ValidationError("hotel_id is required for hotel promotion")
            if not data.get('rooms'):
                raise serializers.ValidationError("rooms is required for hotel promotion")
        elif promotion_type == 'flight':
            if not data.get('airline_id'):
                raise serializers.ValidationError("airline_id is required for flight promotion")
            if not data.get('flights'):
                raise serializers.ValidationError("flights is required for flight promotion")
        elif promotion_type == 'activity':
            # Chỉ hỗ trợ actDates (ActivityDate)
            if not data.get('actDates'):
                raise serializers.ValidationError("actDates is required for activity promotion")
        elif promotion_type == 'car':
            if not data.get('cars'):
                raise serializers.ValidationError("cars is required for car promotion")
        
        return data