from rest_framework import serializers
from .models import Handbook, UserHandbookInteraction
from cities.models import City
from cities.serializers import CitySerializer, CityCreateSerializer
from accounts.models import CustomUser
from accounts.serializers import UserSerializer


class HandbookSerializer(serializers.ModelSerializer):
    author = UserSerializer()
    city = CitySerializer()

    class Meta:
        model = Handbook
        fields = "__all__"


class HandbookCreateSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    class Meta:
        model = Handbook
        fields = [
            "id",
            "author",
            "city",
            "title",
            "category",
            "short_description",
            "description",
            "created_at",
            "image",
        ]  # Chỉ có những trường cần thiết


class UserHandbookInteractionSerializer(serializers.ModelSerializer):
    handbook = HandbookCreateSerializer(read_only=True)

    class Meta:
        model = UserHandbookInteraction
        fields = "__all__"


class UserHandbookInteractionCreateSerializer(serializers.ModelSerializer):
    handbook = serializers.PrimaryKeyRelatedField(queryset=Handbook.objects.all())

    class Meta:
        model = UserHandbookInteraction
        fields = "__all__"
        read_only_fields = ["weighted_score", "last_interacted"]
