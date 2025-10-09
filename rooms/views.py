# rooms/views.py
from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from datetime import datetime
from .models import Room, RoomImage
from .serializers import RoomSerializer, RoomImageSerializer
from bookings.models import Booking


class RoomListView(generics.ListAPIView):
    serializer_class = RoomSerializer

    def get_queryset(self):
        queryset = Room.objects.all()
        hotel_id = self.request.query_params.get("hotel_id")
        hotel_name = self.request.query_params.get("hotel_name")
        capacity = self.request.query_params.get("capacity")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        try:
            if hotel_id:
                queryset = queryset.filter(hotel_id=int(hotel_id))

            if hotel_name:
                queryset = queryset.filter(hotel__name__icontains=hotel_name)

            if capacity:
                cap = int(capacity)
                if cap > 0:
                    queryset = queryset.filter(capacity__gte=cap)

            if start_date and end_date:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                if sd <= ed:
                    booked_room_ids = Booking.objects.filter(
                        Q(check_in_date__lt=ed) & Q(check_out_date__gt=sd)
                    ).values_list("room_id", flat=True)
                    queryset = queryset.exclude(id__in=booked_room_ids)
        except Exception as e:
            print("get_queryset error:", e)
            return Room.objects.none()

        queryset = queryset.prefetch_related(
            Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
        )
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data_with_images = []

            for idx, room in enumerate(queryset):
                room_data = serializer.data[idx]
                room_data["images"] = RoomImageSerializer(room.room_images, many=True).data
                data_with_images.append(room_data)

            return Response({"message": "Danh sách phòng", "data": data_with_images}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomSearchByHotelNameView(generics.ListAPIView):
    serializer_class = RoomSerializer

    def get_queryset(self):
        queryset = Room.objects.all()
        hotel_name = self.request.query_params.get("hotel_name")
        capacity = self.request.query_params.get("capacity")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        try:
            if hotel_name:
                queryset = queryset.filter(hotel__name__icontains=hotel_name)

            if capacity:
                cap = int(capacity)
                if cap > 0:
                    queryset = queryset.filter(capacity__gte=cap)

            if start_date and end_date:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                if sd <= ed:
                    booked_room_ids = Booking.objects.filter(
                        Q(check_in_date__lt=ed) & Q(check_out_date__gt=sd)
                    ).values_list("room_id", flat=True)
                    queryset = queryset.exclude(id__in=booked_room_ids)
        except Exception as e:
            print("get_queryset error:", e)
            return Room.objects.none()

        queryset = queryset.prefetch_related(
            Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
        )
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data_with_images = []

            for idx, room in enumerate(queryset):
                room_data = serializer.data[idx]
                room_data["images"] = RoomImageSerializer(room.room_images, many=True).data
                data_with_images.append(room_data)

            return Response(
                {"message": "Danh sách phòng theo tên khách sạn", "data": data_with_images},
                status=200
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomDetailView(generics.RetrieveAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance = Room.objects.prefetch_related(
                Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
            ).get(id=instance.id)
            serializer = self.get_serializer(instance)
            data = serializer.data
            data["images"] = RoomImageSerializer(instance.room_images, many=True).data
            return Response({"message": "Chi tiết phòng", "data": data}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomCreateView(generics.CreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if serializer.validated_data.get("capacity") is not None and serializer.validated_data.get("capacity") <= 0:
                raise Exception("capacity phải lớn hơn 0")
            if serializer.validated_data.get("price_per_night") is not None and serializer.validated_data.get("price_per_night") < 0:
                raise Exception("price_per_night phải >= 0")

            self.perform_create(serializer)
            return Response({"message": "Phòng đã được tạo thành công", "data": serializer.data}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomUpdateView(generics.UpdateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)

            if serializer.validated_data.get("capacity") is not None and serializer.validated_data.get("capacity") <= 0:
                raise Exception("capacity phải lớn hơn 0")
            if serializer.validated_data.get("price_per_night") is not None and serializer.validated_data.get("price_per_night") < 0:
                raise Exception("price_per_night phải >= 0")

            self.perform_update(serializer)
            return Response({"message": "Cập nhật phòng thành công", "data": serializer.data}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomDeleteView(generics.DestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"message": "Phòng đã được xóa thành công"}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomImageDeleteView(generics.DestroyAPIView):
    queryset = RoomImage.objects.all()
    serializer_class = RoomImageSerializer

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"message": "Hình ảnh phòng đã được xóa thành công"}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
