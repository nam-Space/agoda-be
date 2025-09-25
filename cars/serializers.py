from rest_framework import serializers
from .models import Car
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


class CarSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Car
        fields = "__all__"


class CarCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của người dùng
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = Car
        fields = [
            "user",
            "name",
            "description",
            "capacity",
            "luggage",
            "point",
            "avg_star",
            "price_per_km",
            "avg_speed",
            "image",
        ]  # Chỉ có những trường cần thiết
