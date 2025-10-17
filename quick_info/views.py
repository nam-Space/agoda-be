from rest_framework import generics
from .models import QuickInfo
from .serializers import QuickInfoSerializer, QuickInfoCreateSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


class QuickInfoListView(generics.ListAPIView):
    queryset = QuickInfo.objects.all()
    serializer_class = QuickInfoSerializer
    authentication_classes = []
    permission_classes = []


class QuickInfoDetailView(generics.RetrieveAPIView):
    queryset = QuickInfo.objects.all()
    serializer_class = QuickInfoSerializer
    authentication_classes = []
    permission_classes = []


class QuickInfoCreateView(generics.CreateAPIView):
    queryset = QuickInfo.objects.all()
    serializer_class = QuickInfoCreateSerializer
    permission_classes = [IsAuthenticated]


class QuickInfoUpdateView(generics.UpdateAPIView):
    queryset = QuickInfo.objects.all()
    serializer_class = QuickInfoCreateSerializer
    permission_classes = [IsAuthenticated]


class QuickInfoDeleteView(generics.DestroyAPIView):
    queryset = QuickInfo.objects.all()
    serializer_class = QuickInfoSerializer
    permission_classes = [IsAuthenticated]


class QuickInfoByCityView(generics.ListAPIView):
    serializer_class = QuickInfoSerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        city_id = self.request.query_params.get("city_id")
        if city_id:
            return QuickInfo.objects.filter(city_id=city_id)
        return QuickInfo.objects.none()
