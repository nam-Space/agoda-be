from rest_framework import serializers
from .models import (
    Activity,
    ActivityImage,
    ActivityPackage,
    ActivityDate,
    ActivityDateBookingDetail,
    UserActivityInteraction,
)
from cities.models import City
from cities.serializers import CityCreateSerializer
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


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
    event_organizer = UserSerializer(read_only=True)

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
    event_organizer = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False,  # ✅ Không bắt buộc
        allow_null=True,  # ✅ Cho phép giá trị null
    )

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
            "event_organizer",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết


class UserActivityInteractionSerializer(serializers.ModelSerializer):
    activity = ActivityCreateSerializer(read_only=True)

    class Meta:
        model = UserActivityInteraction
        fields = "__all__"


class UserActivityInteractionCreateSerializer(serializers.ModelSerializer):
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())

    class Meta:
        model = UserActivityInteraction
        fields = "__all__"
        read_only_fields = ["weighted_score", "last_interacted"]


class ActivityPackageSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer()
    activities_dates = ActivityDateSerializer(many=True, read_only=True)

    class Meta:
        model = ActivityPackage
        fields = "__all__"


class ActivityPackageListForActivityAndDateLaunchSerializer(
    serializers.ModelSerializer
):
    activity = ActivitySerializer()
    activities_dates = serializers.SerializerMethodField()

    class Meta:
        model = ActivityPackage
        fields = "__all__"

    def get_activities_dates(self, obj):
        request = self.context.get("request")
        params = request.query_params if request else {}

        date_launch = params.get("date_launch")
        min_date_launch = params.get("min_date_launch")
        max_date_launch = params.get("max_date_launch")

        dates = obj.activities_dates.all()

        if date_launch:
            dates = dates.filter(date_launch=date_launch)
        elif min_date_launch and max_date_launch:
            dates = dates.filter(date_launch__range=[min_date_launch, max_date_launch])
        elif min_date_launch:
            dates = dates.filter(date_launch__gte=min_date_launch)
        elif max_date_launch:
            dates = dates.filter(date_launch__lte=max_date_launch)

        return ActivityDateSerializer(dates, many=True).data


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


class ActivityDateBookingDetailSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của activity date
    activity_date = ActivityDateSerializer(read_only=True)

    event_organizer_activity = UserSerializer(read_only=True)

    class Meta:
        model = ActivityDateBookingDetail
        fields = [
            "id",
            "activity_date",
            "price_adult",
            "price_child",
            "adult_quantity_booking",
            "child_quantity_booking",
            "date_launch",
            "activity_package_name",
            "activity_name",
            "activity_image",
            "avg_price",
            "avg_star",
            "city_name",
            "created_at",
            "updated_at",
            "event_organizer_activity",
        ]  # Chỉ có những trường cần thiết


class ActivityDateBookingCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của activity date
    activity_date = serializers.PrimaryKeyRelatedField(
        queryset=ActivityDate.objects.all()
    )

    class Meta:
        model = ActivityDateBookingDetail
        fields = [
            "id",
            "activity_date",
            "price_adult",
            "price_child",
            "adult_quantity_booking",
            "child_quantity_booking",
            "date_launch",
            "activity_package_name",
            "activity_name",
            "activity_image",
            "avg_price",
            "avg_star",
            "city_name",
            "created_at",
            "updated_at",
        ]  # Chỉ có những trường cần thiết
