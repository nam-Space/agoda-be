from rest_framework import serializers
from .models import City
from countries.serializers import CountrySerializer
from countries.models import Country


class CitySerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = City
        fields = "__all__"


class CityCreateSerializer(serializers.ModelSerializer):
    # Sử dụng PrimaryKeyRelatedField để nhận ID của quốc gia
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())

    class Meta:
        model = City
        fields = [
            "name",
            "description",
            "image",
            "country",
        ]  # Chỉ có những trường cần thiết
