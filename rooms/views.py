# # rooms/views.py
# from rest_framework import generics
# from rest_framework.response import Response
# from django.db.models import Q, Prefetch
# from datetime import datetime
# from .models import Room, RoomImage
# from .serializers import RoomSerializer, RoomImageSerializer
# from bookings.models import Booking


# class RoomListView(generics.ListAPIView):
#     serializer_class = RoomSerializer

#     def get_queryset(self):
#         queryset = Room.objects.all()
#         hotel_id = self.request.query_params.get("hotel_id")
#         hotel_name = self.request.query_params.get("hotel_name")
#         capacity = self.request.query_params.get("capacity")
#         start_date = self.request.query_params.get("start_date")
#         end_date = self.request.query_params.get("end_date")

#         try:
#             if hotel_id:
#                 queryset = queryset.filter(hotel_id=int(hotel_id))

#             if hotel_name:
#                 queryset = queryset.filter(hotel__name__icontains=hotel_name)

#             if capacity:
#                 cap = int(capacity)
#                 if cap > 0:
#                     queryset = queryset.filter(capacity__gte=cap)

#             if start_date and end_date:
#                 sd = datetime.strptime(start_date, "%Y-%m-%d").date()
#                 ed = datetime.strptime(end_date, "%Y-%m-%d").date()
#                 if sd <= ed:
#                     booked_room_ids = Booking.objects.filter(
#                         Q(check_in_date__lt=ed) & Q(check_out_date__gt=sd)
#                     ).values_list("room_id", flat=True)
#                     queryset = queryset.exclude(id__in=booked_room_ids)
#         except Exception as e:
#             print("get_queryset error:", e)
#             return Room.objects.none()

#         queryset = queryset.prefetch_related(
#             Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
#         )
#         return queryset

#     def list(self, request, *args, **kwargs):
#         try:
#             queryset = self.get_queryset()
#             serializer = self.get_serializer(queryset, many=True)
#             data_with_images = []

#             for idx, room in enumerate(queryset):
#                 room_data = serializer.data[idx]
#                 room_data["images"] = RoomImageSerializer(room.room_images, many=True).data
#                 data_with_images.append(room_data)

#             return Response({"message": "Danh sách phòng", "data": data_with_images}, status=200)
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)


# class RoomSearchByHotelNameView(generics.ListAPIView):
#     serializer_class = RoomSerializer

#     def get_queryset(self):
#         queryset = Room.objects.all()
#         hotel_name = self.request.query_params.get("hotel_name")
#         capacity = self.request.query_params.get("capacity")
#         start_date = self.request.query_params.get("start_date")
#         end_date = self.request.query_params.get("end_date")

#         try:
#             if hotel_name:
#                 queryset = queryset.filter(hotel__name__icontains=hotel_name)

#             if capacity:
#                 cap = int(capacity)
#                 if cap > 0:
#                     queryset = queryset.filter(capacity__gte=cap)

#             if start_date and end_date:
#                 sd = datetime.strptime(start_date, "%Y-%m-%d").date()
#                 ed = datetime.strptime(end_date, "%Y-%m-%d").date()
#                 if sd <= ed:
#                     booked_room_ids = Booking.objects.filter(
#                         Q(check_in_date__lt=ed) & Q(check_out_date__gt=sd)
#                     ).values_list("room_id", flat=True)
#                     queryset = queryset.exclude(id__in=booked_room_ids)
#         except Exception as e:
#             print("get_queryset error:", e)
#             return Room.objects.none()

#         queryset = queryset.prefetch_related(
#             Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
#         )
#         return queryset

#     def list(self, request, *args, **kwargs):
#         try:
#             queryset = self.get_queryset()
#             serializer = self.get_serializer(queryset, many=True)
#             data_with_images = []

#             for idx, room in enumerate(queryset):
#                 room_data = serializer.data[idx]
#                 room_data["images"] = RoomImageSerializer(room.room_images, many=True).data
#                 data_with_images.append(room_data)

#             return Response(
#                 {"message": "Danh sách phòng theo tên khách sạn", "data": data_with_images},
#                 status=200
#             )
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)


# class RoomDetailView(generics.RetrieveAPIView):
#     queryset = Room.objects.all()
#     serializer_class = RoomSerializer

#     def retrieve(self, request, *args, **kwargs):
#         try:
#             instance = self.get_object()
#             instance = Room.objects.prefetch_related(
#                 Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
#             ).get(id=instance.id)
#             serializer = self.get_serializer(instance)
#             data = serializer.data
#             data["images"] = RoomImageSerializer(instance.room_images, many=True).data
#             return Response({"message": "Chi tiết phòng", "data": data}, status=200)
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)


# class RoomCreateView(generics.CreateAPIView):
#     queryset = Room.objects.all()
#     serializer_class = RoomSerializer

#     def create(self, request, *args, **kwargs):
#         try:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)

#             if serializer.validated_data.get("capacity") is not None and serializer.validated_data.get("capacity") <= 0:
#                 raise Exception("capacity phải lớn hơn 0")
#             if serializer.validated_data.get("price_per_night") is not None and serializer.validated_data.get("price_per_night") < 0:
#                 raise Exception("price_per_night phải >= 0")

#             self.perform_create(serializer)
#             return Response({"message": "Phòng đã được tạo thành công", "data": serializer.data}, status=201)
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)


# class RoomUpdateView(generics.UpdateAPIView):
#     queryset = Room.objects.all()
#     serializer_class = RoomSerializer

#     def update(self, request, *args, **kwargs):
#         try:
#             partial = kwargs.pop("partial", False)
#             instance = self.get_object()
#             serializer = self.get_serializer(instance, data=request.data, partial=partial)
#             serializer.is_valid(raise_exception=True)

#             if serializer.validated_data.get("capacity") is not None and serializer.validated_data.get("capacity") <= 0:
#                 raise Exception("capacity phải lớn hơn 0")
#             if serializer.validated_data.get("price_per_night") is not None and serializer.validated_data.get("price_per_night") < 0:
#                 raise Exception("price_per_night phải >= 0")

#             self.perform_update(serializer)
#             return Response({"message": "Cập nhật phòng thành công", "data": serializer.data}, status=200)
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)


# class RoomDeleteView(generics.DestroyAPIView):
#     queryset = Room.objects.all()
#     serializer_class = RoomSerializer

#     def destroy(self, request, *args, **kwargs):
#         try:
#             instance = self.get_object()
#             self.perform_destroy(instance)
#             return Response({"message": "Phòng đã được xóa thành công"}, status=200)
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)


# class RoomImageDeleteView(generics.DestroyAPIView):
#     queryset = RoomImage.objects.all()
#     serializer_class = RoomImageSerializer

#     def destroy(self, request, *args, **kwargs):
#         try:
#             instance = self.get_object()
#             self.perform_destroy(instance)
#             return Response({"message": "Hình ảnh phòng đã được xóa thành công"}, status=200)
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)

# rooms/views.py
from cities.serializers import CitySerializer
from hotels.models import Hotel, HotelImage
from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from datetime import datetime
from .models import Room, RoomImage, RoomAmenity
from .serializers import RoomSerializer, RoomImageSerializer, RoomAmenitySerializer
from bookings.models import Booking


class RoomListView(generics.ListAPIView):
    serializer_class = RoomSerializer

    def get_queryset(self):
        queryset = Room.objects.all()
        hotel_id = self.request.query_params.get("hotel_id")
        hotel_name = self.request.query_params.get("hotel_name")
        adults = self.request.query_params.get("adults")
        children = self.request.query_params.get("children")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        try:
            if hotel_id:
                queryset = queryset.filter(hotel_id=int(hotel_id))

            if hotel_name:
                queryset = queryset.filter(hotel__name__icontains=hotel_name)

            if adults:
                queryset = queryset.filter(adults_capacity__gte=int(adults))

            if children:
                queryset = queryset.filter(children_capacity__gte=int(children))

            # Chỉ lấy phòng có còn ít nhất 1 phòng trống
            queryset = queryset.filter(available_rooms__gt=0)

            # Chỉ lấy phòng còn hạn (start_date <= today <= end_date)
            today = datetime.now().date()
            queryset = queryset.filter(start_date__lte=today, end_date__gte=today)

            # Filter theo ngày tìm kiếm (loại bỏ các phòng đã đặt)
            if start_date and end_date:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                if sd <= ed:
                    booked_room_ids = Booking.objects.filter(
                        # Q(service_type=1),  # giả sử service_type=1 là Room
                        # Q(check_in_date__lt=ed) & Q(check_out_date__gt=sd)
                        check_in_date__lt=ed,
                        check_out_date__gt=sd,
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
                room_data["images"] = RoomImageSerializer(
                    room.room_images, many=True
                ).data
                data_with_images.append(room_data)

            return Response(
                {"message": "Danh sách phòng", "data": data_with_images}, status=200
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
                Prefetch(
                    "images", queryset=RoomImage.objects.all(), to_attr="room_images"
                )
            ).get(id=instance.id)
            serializer = self.get_serializer(instance)
            data = serializer.data
            data["images"] = RoomImageSerializer(instance.room_images, many=True).data
            return Response(
                {"isSuccess": True, "message": "Chi tiết phòng", "data": data},
                status=200,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomCreateView(generics.CreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data

            if data.get("adults_capacity", 0) <= 0:
                raise Exception("adults_capacity phải > 0")
            if data.get("children_capacity", 0) < 0:
                raise Exception("children_capacity phải >= 0")
            if data.get("price_per_night", 0) < 0:
                raise Exception("price_per_night phải >= 0")
            if data.get("total_rooms", 0) <= 0:
                raise Exception("total_rooms phải > 0")
            if data.get("available_rooms", 0) < 0:
                raise Exception("available_rooms phải >= 0")

            self.perform_create(serializer)
            return Response(
                {"message": "Phòng đã được tạo thành công", "data": serializer.data},
                status=201,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomUpdateView(generics.UpdateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data

            if "adults_capacity" in data and data["adults_capacity"] <= 0:
                raise Exception("adults_capacity phải > 0")
            if "children_capacity" in data and data["children_capacity"] < 0:
                raise Exception("children_capacity phải >= 0")
            if "price_per_night" in data and data["price_per_night"] < 0:
                raise Exception("price_per_night phải >= 0")
            if "total_rooms" in data and data["total_rooms"] <= 0:
                raise Exception("total_rooms phải > 0")
            if "available_rooms" in data and data["available_rooms"] < 0:
                raise Exception("available_rooms phải >= 0")

            self.perform_update(serializer)
            return Response(
                {"message": "Cập nhật phòng thành công", "data": serializer.data},
                status=200,
            )
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
            return Response(
                {"message": "Hình ảnh phòng đã được xóa thành công"}, status=200
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomAmenityListView(generics.ListAPIView):
    serializer_class = RoomAmenitySerializer

    def get_queryset(self):
        room_id = self.kwargs.get("room_id")
        return RoomAmenity.objects.filter(room_id=room_id).order_by("id")


class RoomSearchView(generics.ListAPIView):
    serializer_class = RoomSerializer

    def get(self, request, *args, **kwargs):
        hotel_name = request.query_params.get("hotel_name")
        adults = request.query_params.get("adults")
        children = request.query_params.get("children")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not hotel_name:
            return Response(
                {"isSuccess": False, "message": "Thiếu tham số hotel_name"}, status=400
            )

        hotel = (
            Hotel.objects.prefetch_related(
                Prefetch(
                    "images", queryset=HotelImage.objects.all(), to_attr="hotel_images"
                )
            )
            .select_related("city")
            .filter(name__icontains=hotel_name)
            .first()
        )

        if not hotel:
            return Response(
                {"isSuccess": False, "message": "Không tìm thấy khách sạn"}, status=404
            )

        queryset = (
            Room.objects.select_related("hotel")
            .prefetch_related(
                Prefetch(
                    "images", queryset=RoomImage.objects.all(), to_attr="room_images"
                )
            )
            .filter(hotel=hotel, available_rooms__gt=0)
        )

        if adults:
            queryset = queryset.filter(adults_capacity__gte=int(adults))
        if children:
            queryset = queryset.filter(children_capacity__gte=int(children))

        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                if sd <= ed:
                    booked_room_ids = Booking.objects.filter(
                        check_in_date__lt=ed, check_out_date__gt=sd
                    ).values_list("room_id", flat=True)
                    queryset = queryset.exclude(id__in=booked_room_ids)
            except Exception as e:
                print("Parse date error:", e)

        rooms = queryset.all()

        hotel_data = {
            "id": hotel.id,
            "name": hotel.name,
            "description": hotel.description,
            "lat": hotel.lat,
            "lng": hotel.lng,
            "location": hotel.location,
            "nearbyLocation": hotel.nearbyLocation,
            "point": hotel.point,
            "avg_star": hotel.avg_star,
            "facilities": hotel.facilities,
            "withUs": hotel.withUs,
            "usefulInformation": hotel.usefulInformation,
            "amenitiesAndFacilities": hotel.amenitiesAndFacilities,
            "locationInfo": hotel.locationInfo,
            "regulation": hotel.regulation,
            "city": CitySerializer(hotel.city).data if hotel.city else None,
            "images": [
                {
                    "id": img.id,
                    "hotel": img.hotel_id,
                    "image": getattr(img.image, "url", None),
                    "created_at": img.created_at,
                }
                for img in getattr(hotel, "hotel_images", [])
            ],
        }

        hotel_data["rooms"] = []
        for room in rooms:
            hotel_data["rooms"].append(
                {
                    "id": room.id,
                    "name": room.room_type,  # ✅ hiển thị room_type làm name
                    "price": room.price_per_night,  # ✅ đúng field trong model
                    "available_rooms": room.available_rooms,
                    "adults_capacity": room.adults_capacity,
                    "children_capacity": room.children_capacity,
                    "images": [
                        {"id": img.id, "image": getattr(img.image, "url", None)}
                        for img in getattr(room, "room_images", [])
                    ],
                }
            )

        return Response(
            {
                "isSuccess": True,
                "message": "Hotel details fetched successfully",
                "data": hotel_data,
            },
            status=200,
        )
