from rest_framework import serializers
from .models import Neighborhood
from cities.serializers import CitySerializer
from cities.models import City


class NeighborhoodSerializer(serializers.ModelSerializer):
    city = CitySerializer()

    class Meta:
        model = Neighborhood
        fields = "__all__"


class NeighborhoodCreateSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    class Meta:
        model = Neighborhood
        fields = ["id", "name", "description", "city"]
