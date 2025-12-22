# rooms/views.py
from cities.serializers import CitySerializer
from hotels.models import Hotel, HotelImage
from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from datetime import datetime
from .models import Room, RoomImage, RoomAmenity, RoomBookingDetail
from .serializers import (
    RoomSerializer,
    RoomImageSerializer,
    RoomAmenitySerializer,
    RoomBookingDetailSerializer,
    RoomCreateSerializer,
    RoomAmenityCreateSerializer,
)
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
import os
from django.conf import settings
from rest_framework import status


class CommonPagination(PageNumberPagination):
    page_size = 10
    page_query_param = "current"
    page_size_query_param = "pageSize"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "isSuccess": True,
                "message": self.context.get("message", "Fetched data successfully!"),
                "meta": {
                    "totalItems": self.page.paginator.count,
                    "currentPage": self.page.number,
                    "itemsPerPage": self.get_page_size(self.request),
                    "totalPages": self.page.paginator.num_pages,
                },
                "data": data,
            }
        )


class RoomListView(generics.ListAPIView):
    serializer_class = RoomSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    pagination_class = CommonPagination

    def get_queryset(self):
        queryset = Room.objects.all()
        filter_params = self.request.query_params
        hotel_id = filter_params.get("hotel_id")
        owner_id = filter_params.get("owner_id")
        hotel_name = filter_params.get("hotel_name")
        adults = filter_params.get("adults")
        children = filter_params.get("children")
        start_date = filter_params.get("start_date")
        end_date = filter_params.get("end_date")
        stay_type = filter_params.get("stay_type")

        try:
            if hotel_id:
                queryset = queryset.filter(hotel_id=int(hotel_id))

            if owner_id:
                queryset = queryset.filter(hotel__owner_id=int(owner_id))

            if hotel_name:
                queryset = queryset.filter(hotel__name__icontains=hotel_name)

            if adults:
                queryset = queryset.filter(adults_capacity__gte=int(adults))

            if children:
                queryset = queryset.filter(children_capacity__gte=int(children))

            if stay_type:
                queryset = queryset.filter(stay_type=stay_type)

            # Chỉ lấy phòng có còn ít nhất 1 phòng trống
            queryset = queryset.filter(available_rooms__gt=0)

            # Chỉ lấy phòng còn hạn (start_date <= today <= end_date)
            today = datetime.now().date()
            queryset = queryset.filter(start_date__lte=today, end_date__gte=today)

            # Filter theo ngày tìm kiếm (chỉ loại loại phòng đã đặt hết)
            if start_date and end_date:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                if sd <= ed:
                    from django.db.models import Count

                    # Đếm số booking giao ngày cho từng loại phòng
                    booking_counts = (
                        RoomBookingDetail.objects.filter(
                            check_in__lt=ed,
                            check_out__gt=sd,
                        )
                        .values("room_id")
                        .annotate(num_booked=Count("id"))
                    )
                    booked_dict = {
                        b["room_id"]: b["num_booked"] for b in booking_counts
                    }
                    # Lọc lại queryset: chỉ giữ loại phòng còn trống (giữ QuerySet)
                    available_room_ids = [
                        room.id
                        for room in queryset
                        if booked_dict.get(room.id, 0) < room.available_rooms
                    ]
                    queryset = queryset.filter(id__in=available_room_ids)

        except Exception as e:
            print("get_queryset error:", e)
            return Room.objects.none()

        queryset = queryset.prefetch_related(
            Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
        )
        sort_params = filter_params.get("sort")
        order_fields = []

        if sort_params:
            # Ví dụ: sort=avg_price-desc,avg_star-asc
            sort_list = sort_params.split(",")
            for sort_item in sort_list:
                try:
                    field, direction = sort_item.split("-")
                    if direction == "desc":
                        order_fields.append(f"-{field}")
                    else:
                        order_fields.append(field)
                except ValueError:
                    continue  # bỏ qua format không hợp lệ

        queryset = queryset.order_by(*order_fields)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Truyền message vào context để phân trang trả về đúng message
            self.paginator.context = {"message": "Fetched all rooms successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all rooms successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )


class RoomAdminListView(generics.ListAPIView):
    serializer_class = RoomSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    pagination_class = CommonPagination

    def get_queryset(self):
        queryset = Room.objects.all()
        filter_params = self.request.query_params
        hotel_id = filter_params.get("hotel_id")
        owner_id = filter_params.get("owner_id")
        hotel_name = filter_params.get("hotel_name")
        adults = filter_params.get("adults")
        children = filter_params.get("children")

        if hotel_id:
            queryset = queryset.filter(hotel_id=int(hotel_id))

        if owner_id:
            queryset = queryset.filter(hotel__owner_id=int(owner_id))

        if hotel_name:
            queryset = queryset.filter(hotel__name__icontains=hotel_name)

        if adults:
            queryset = queryset.filter(adults_capacity__gte=int(adults))

        if children:
            queryset = queryset.filter(children_capacity__gte=int(children))

        queryset = queryset.prefetch_related(
            Prefetch("images", queryset=RoomImage.objects.all(), to_attr="room_images")
        )
        sort_params = filter_params.get("sort")
        order_fields = []

        if sort_params:
            # Ví dụ: sort=avg_price-desc,avg_star-asc
            sort_list = sort_params.split(",")
            for sort_item in sort_list:
                try:
                    field, direction = sort_item.split("-")
                    if direction == "desc":
                        order_fields.append(f"-{field}")
                    else:
                        order_fields.append(field)
                except ValueError:
                    continue  # bỏ qua format không hợp lệ

        queryset = queryset.order_by(*order_fields)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Truyền message vào context để phân trang trả về đúng message
            self.paginator.context = {"message": "Fetched all rooms successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all rooms successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )


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
                    booked_room_ids = RoomBookingDetail.objects.filter(
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
                {"isSuccess": True, "message": "Lấy phòng thành công", "data": data},
                status=200,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RoomCreateView(generics.CreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            room = serializer.save()
            new_images = request.data.get("images", [])
            for image in new_images:
                RoomImage.objects.create(room=room, image=image)
            return Response(
                {
                    "isSuccess": True,
                    "message": "Room created successfully",
                    "data": RoomCreateSerializer(room).data,
                },
                status=200,
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create room",
                "data": serializer.errors,
            },
            status=400,
        )


class RoomUpdateView(generics.UpdateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomCreateSerializer

    def update(self, request, *args, **kwargs):
        room = self.get_object()
        serializer = self.get_serializer(room, data=request.data, partial=True)
        if serializer.is_valid():
            updated_room = serializer.save()
            # xóa ảnh cũ
            RoomImage.objects.filter(room=updated_room).delete()
            new_images = request.data.get("images", [])
            for image in new_images:
                RoomImage.objects.create(room=updated_room, image=image)
            return Response(
                {
                    "isSuccess": True,
                    "message": "Room updated successfully",
                    "data": RoomCreateSerializer(updated_room).data,
                }
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update room",
                "data": serializer.errors,
            },
            status=400,
        )


class RoomDeleteView(generics.DestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomCreateSerializer

    def perform_destroy(self, instance):
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Room deleted successfully",
                "data": {},
            },
            status=200,
        )


class RoomImageDeleteView(generics.DestroyAPIView):
    queryset = RoomImage.objects.all()
    serializer_class = RoomImageSerializer

    def perform_destroy(self, instance):
        image_path = instance.image
        if image_path.startswith("/media"):
            image_path = image_path.lstrip("/media")
        full_path = os.path.join(settings.MEDIA_ROOT, image_path.lstrip("/"))
        if os.path.exists(full_path):
            os.remove(full_path)
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "RoomImage deleted successfully",
                "data": {},
            },
            status=200,
        )


class RoomAmenityListView(generics.ListAPIView):
    serializer_class = RoomAmenitySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    pagination_class = CommonPagination

    def get_queryset(self):
        queryset = RoomAmenity.objects.all()
        filter_params = self.request.query_params

        query_filter = Q()

        # Duyệt qua các tham số query để tạo bộ lọc cho mỗi trường
        for field, value in filter_params.items():
            if (
                field != "current"
                and field != "pageSize"
                and field != "sort"
                and field != "room_id"
            ):
                query_filter &= Q(
                    **{f"{field}__icontains": value}
                )  # Thêm điều kiện lọc cho mỗi trường
            if field in ["room_id"]:
                query_filter &= Q(room_id=value)

        queryset = queryset.filter(query_filter)

        sort_params = filter_params.get("sort")
        order_fields = []

        if sort_params:
            # Ví dụ: sort=avg_price-desc,avg_star-asc
            sort_list = sort_params.split(",")
            for sort_item in sort_list:
                try:
                    field, direction = sort_item.split("-")
                    if direction == "desc":
                        order_fields.append(f"-{field}")
                    else:
                        order_fields.append(field)
                except ValueError:
                    continue  # bỏ qua format không hợp lệ

        queryset = queryset.order_by(*order_fields)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            page if page is not None else queryset, many=True
        )

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Truyền message vào context để phân trang trả về đúng message
            self.paginator.context = {"message": "Fetched all amenities successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all amenities successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )


# API GET chi tiết tiện nghi
class RoomAmenityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RoomAmenity.objects.all()
    serializer_class = RoomAmenitySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết tiện nghi.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(
            {
                "isSuccess": True,
                "message": " RoomAmenity detail fetched successfully",
                "data": serializer.data,  # Dữ liệu tiện nghi
            }
        )


# API POST tạo tiện nghi
class RoomAmenityCreateView(generics.CreateAPIView):
    queryset = RoomAmenity.objects.all()
    serializer_class = RoomAmenityCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            city = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "RoomAmenity created successfully",
                    "data": RoomAmenityCreateSerializer(city).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create RoomAmenity",
                "data": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật tiện nghi
class RoomAmenityUpdateView(generics.UpdateAPIView):
    queryset = RoomAmenity.objects.all()
    serializer_class = RoomAmenityCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def update(self, request, *args, **kwargs):
        room_amenity = self.get_object()
        serializer = self.get_serializer(room_amenity, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "RoomAmenity updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update RoomAmenity",
                "data": serializer.errors,
            },
            status=400,
        )


# API DELETE xóa tiện nghi
class RoomAmenityDeleteView(generics.DestroyAPIView):
    queryset = RoomAmenity.objects.all()
    serializer_class = RoomAmenityCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "RoomAmenity deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class RoomBookingDetailView(generics.RetrieveAPIView):
    queryset = RoomBookingDetail.objects.all()
    serializer_class = RoomBookingDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data
            return Response(
                {
                    "isSuccess": True,
                    "message": "Fetch RoomBookingDetailSerializer successfully!",
                    "data": data,
                },
                status=200,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)
