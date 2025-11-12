from rest_framework import serializers
from .models import Review
from hotels.models import Hotel
from bookings.models import ServiceType
from accounts.serializers import UserSerializer
from hotels.serializers import HotelSerializer
from activities.serializers import ActivitySerializer
from handbooks.serializers import HandbookSerializer


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    service_type_name = serializers.SerializerMethodField()
    service_ref_id = serializers.IntegerField(required=False, allow_null=True)
    hotel_detail = serializers.SerializerMethodField()
    activity_detail = serializers.SerializerMethodField()
    handbook_detail = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "service_type",
            "service_type_name",
            "service_ref_id",
            "rating",
            "comment",
            "sentiment",
            "confidence",
            "hotel_detail",
            "activity_detail",
            "handbook_detail",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "service_type_name",
            "hotel_detail",
            "activity_detail",
            "handbook_detail",
            "sentiment",  # 🆕 Đặt read-only để hệ thống tự tính
            "confidence",  # 🆕 Đặt read-only để hệ thống tự tính
        ]

    def get_service_type_name(self, obj):
        """Trả label của ServiceType, safe nếu obj.service_type là None"""
        try:
            return ServiceType(obj.service_type).label
        except Exception:
            return None

    def get_hotel_detail(self, obj):
        """Nếu review thuộc loại HOTEL thì trả dữ liệu HotelSerializer"""
        if obj.service_type != ServiceType.HOTEL or not obj.service_ref_id:
            return None
        hotel = Hotel.objects.filter(id=obj.service_ref_id).first()
        if not hotel:
            return None
        return HotelSerializer(hotel, context=self.context).data

    def get_activity_detail(self, obj):
        """Nếu review thuộc loại ACTIVITY thì trả dữ liệu ActivitySerializer"""
        if obj.service_type != ServiceType.ACTIVITY or not obj.service_ref_id:
            return None
        from activities.models import Activity  # tránh circular import

        activity = Activity.objects.filter(id=obj.service_ref_id).first()
        if not activity:
            return None
        return ActivitySerializer(activity, context=self.context).data

    def get_handbook_detail(self, obj):
        """Nếu review thuộc loại HANDBOOK thì trả dữ liệu HandbookSerializer"""
        if obj.service_type != ServiceType.HANDBOOK or not obj.service_ref_id:
            return None
        from handbooks.models import Handbook  # tránh circular import

        handbook = Handbook.objects.filter(id=obj.service_ref_id).first()
        if not handbook:
            return None
        return HandbookSerializer(handbook, context=self.context).data

    def to_representation(self, instance):
        """Chỉ giữ field tương ứng với service_type"""
        ret = super().to_representation(instance)
        service_type = instance.service_type
        if service_type == ServiceType.HOTEL:
            ret.pop("activity_detail", None)
            ret.pop("handbook_detail", None)
        elif service_type == ServiceType.ACTIVITY:
            ret.pop("hotel_detail", None)
            ret.pop("handbook_detail", None)
        elif service_type == ServiceType.HANDBOOK:
            ret.pop("hotel_detail", None)
            ret.pop("activity_detail", None)
        else:
            # nếu là loại khác thì bỏ cả hai
            ret.pop("hotel_detail", None)
            ret.pop("activity_detail", None)
            ret.pop("handbook_detail", None)
        return ret
