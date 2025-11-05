from rest_framework import serializers
from .models import Airport
from cities.models import City
from cities.serializers import CityCreateSerializer


class AirportSerializer(serializers.ModelSerializer):
    city = CityCreateSerializer(read_only=True)

    class Meta:
        model = Airport
        fields = "__all__"


class AirportCreateSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    class Meta:
        model = Airport
        fields = "__all__"
