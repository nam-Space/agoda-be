from rest_framework import serializers
from .models import Activity, ActivityImage, ActivityPackage, ActivityDate
from cities.models import City
from cities.serializers import CityCreateSerializer


class ActivityDateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityDate
        fields = "__all__"


class ActivityPackagesListSerializer(serializers.ModelSerializer):
    activities_dates = ActivityDateSerializer(many=True, read_only=True)

    class Meta:
        model = ActivityPackage
        fields = "__all__"


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


class ActivityDetailSerializer(serializers.ModelSerializer):
    images = ActivityImageSerializer(many=True, read_only=True)
    city = CityCreateSerializer(read_only=True)
    activities_packages = ActivityPackagesListSerializer(many=True, read_only=True)

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
            "category",
            "short_description",
            "more_information",
            "cancellation_policy",
            "departure_information",
            "avg_price",
            "avg_star",
            "total_time",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết


class ActivityPackageSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer()
    activities_dates = ActivityDateSerializer(many=True, read_only=True)

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
            "activity_package",
            "price_adult",
            "price_child",
            "adult_quantity",
            "child_quantity",
            "date_launch",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết
