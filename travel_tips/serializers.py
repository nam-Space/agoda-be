from rest_framework import serializers
from .models import TravelTip


class TravelTipSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelTip
        fields = "__all__"
