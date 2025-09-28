from rest_framework import serializers
from .models import Activity, ActivityImage, ActivityPackage, ActivityDate
from cities.models import City
from cities.serializers import CityCreateSerializer


class ActivityImageSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của hoạt động
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())

    class Meta:
        model = ActivityImage
        fields = "__all__"


class ActivitySerializer(serializers.ModelSerializer):
    images = ActivityImageSerializer(many=True, read_only=True)
    city = CityCreateSerializer(read_only=True)

    class Meta:
        model = Activity
        fields = "__all__"


class ActivityCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của hoạt động
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    class Meta:
        model = Activity
        fields = [
            "city",
            "name",
            "short_description",
            "more_information",
            "cancellation_policy",
            "avg_price",
            "avg_star",
            "total_time",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết


class ActivityPackageSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer()

    class Meta:
        model = ActivityPackage
        fields = "__all__"


class ActivityPackageCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của activity
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())

    class Meta:
        model = ActivityPackage
        fields = [
            "name",
            "activity",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết


class ActivityDateSerializer(serializers.ModelSerializer):
    activity_package = ActivityPackageSerializer()

    class Meta:
        model = ActivityDate
        fields = "__all__"


class ActivityDateCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của activity package
    activity_package = serializers.PrimaryKeyRelatedField(
        queryset=ActivityPackage.objects.all()
    )

    class Meta:
        model = ActivityDate
        fields = [
            "name",
            "activity_package",
            "price",
            "date_launch",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết
