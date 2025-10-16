from rest_framework import serializers
from .models import QuickInfo
from cities.serializers import CitySerializer
from cities.models import City


class QuickInfoSerializer(serializers.ModelSerializer):
    city = CitySerializer()

    class Meta:
        model = QuickInfo
        fields = "__all__"


class QuickInfoCreateSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    class Meta:
        model = QuickInfo
        fields = ["id", "label", "value", "highlight", "city"]
