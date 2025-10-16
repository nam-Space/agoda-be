from rest_framework import serializers
from .models import TravelGuide


class TravelGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelGuide
        fields = "__all__"
