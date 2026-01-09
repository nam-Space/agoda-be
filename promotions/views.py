from rest_framework.pagination import PageNumberPagination
from rest_framework import generics, status
from rest_framework.response import Response
from .models import (
    Promotion,
    FlightPromotion,
    ActivityPromotion,
    RoomPromotion,
    CarPromotion,
    PromotionType,
)
from .serializers import (
    PromotionSerializer,
    PromotionCreateSerializer,
    PromotionAdminSerializer,
    PromotionAdminCreateSerializer,
    RoomPromotionAdminSerializer,
    RoomPromotionAdminCreateSerializer,
    CarPromotionAdminSerializer,
    CarPromotionAdminCreateSerializer,
    FlightPromotionAdminSerializer,
    FlightPromotionAdminCreateSerializer,
    ActivityPromotionAdminSerializer,
    ActivityPromotionAdminCreateSerializer,
)
from hotels.models import Hotel
from flights.models import Flight
from rooms.models import Room
from cars.models import Car
from airlines.models import Airline
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView


class PromotionCommonPagination(PageNumberPagination):
    page_size = 10
    page_query_param = "current"
    page_size_query_param = "pageSize"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "isSuccess": True,
                "message": self.context.get(
                    "message", "Fetched promotions successfully!"
                ),
                "meta": {
                    "totalItems": self.page.paginator.count,
                    "currentPage": self.page.number,
                    "itemsPerPage": self.get_page_size(self.request),
                    "totalPages": self.page.paginator.num_pages,
                },
                "data": data,
            }
        )


class PromotionListCreateView(generics.ListCreateAPIView):
    queryset = Promotion.objects.prefetch_related(
        "flight_promotions__flight",
        "activity_promotions__activity_date",
        "room_promotions__room__hotel",
        "car_promotions__car",
    ).all()
    serializer_class = PromotionSerializer
    pagination_class = PromotionCommonPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        min_date = params.get("min_date")

        if min_date:
            queryset = queryset.filter(end_date__gte=min_date)

        promotion_type = params.get("promotion_type")
        if promotion_type:
            queryset = queryset.filter(promotion_type=promotion_type)

        sort_params = params.get("sort")
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
            self.paginator.context = {"message": "Fetched promotions successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched promotions successfully!",
                "meta": {"totalItems": len(queryset), "pagination": None},
                "data": serializer.data,
            }
        )


class PromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Promotion.objects.prefetch_related(
        "flight_promotions__flight",
        "activity_promotions__activity_date",
        "room_promotions__room__hotel",
        "car_promotions__car",
    ).all()

    serializer_class = PromotionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        q = self.request.query_params
        # Flight filters
        context["origin_id"] = q.get("origin_id")
        context["destination_id"] = q.get("destination_id")
        # context["airline_id"] = q.get("airline_id")
        context["start_date"] = q.get("start_date")
        # Activity filters
        context["category"] = q.get("category")
        context["max_price"] = q.get("max_price")
        context["end_date"] = q.get("end_date")
        context["search"] = q.get("search")
        # Hotel filter
        context["city_id"] = q.get("city_id")
        return context

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        data = response.data
        promotion_type = data.get("promotion_type")
        if promotion_type == 1:  # HOTEL
            from rooms.models import Room
            from hotels.models import Hotel

            city_id = request.query_params.get("city_id")
            # Lấy tất cả room_promotions
            room_promotions = data.get("room_promotions", [])
            hotel_map = {}
            for rp in room_promotions:
                try:
                    room = Room.objects.select_related("hotel").get(id=rp["room"])
                    hotel = room.hotel
                    if city_id and str(hotel.city_id) != str(city_id):
                        continue
                    hid = hotel.id
                    discount = float(rp.get("effective_discount_percent") or 0)
                    images = getattr(hotel, "images", None)
                    thumbnail = None
                    if images and hasattr(images, "all"):
                        first_img = images.all().first()
                        if first_img and hasattr(first_img, "image"):
                            thumbnail = (
                                first_img.image
                            )  # Nếu là CharField thì không cần .url
                    if hid not in hotel_map:
                        hotel_map[hid] = {
                            "id": hid,
                            "name": hotel.name,
                            "min_price": hotel.min_price,
                            "max_discount": discount,
                            "avg_star": hotel.avg_star,
                            "review_count": hotel.review_count,
                            "locationInfo": hotel.locationInfo,
                            "total_weighted_score": hotel.total_weighted_score,
                            "thumbnail": thumbnail,
                        }
                    else:
                        hotel_map[hid]["max_discount"] = max(
                            hotel_map[hid]["max_discount"], discount
                        )
                except Exception:
                    continue
            data["hotels"] = list(hotel_map.values())
        elif promotion_type == 3:  # ACTIVITY
            from activities.models import Activity, ActivityImage

            instance = self.get_object()

            # Lấy tất cả ActivityPromotion của promotion này
            activity_promotions = (
                instance.activity_promotions.select_related(
                    "activity_date__activity_package__activity"
                )
                .prefetch_related("activity_date__activity_package__activity__images")
                .all()
            )

            # Tạo mảng activity_dates
            activity_dates = []
            activity_map = {}  # Để group theo Activity

            for ap in activity_promotions:
                if not ap.activity_date:
                    continue

                activity_date = ap.activity_date
                activity_package = activity_date.activity_package
                activity = activity_package.activity if activity_package else None

                # Tính discount từ ActivityPromotion hoặc Promotion
                discount_percent = (
                    float(ap.discount_percent)
                    if ap.discount_percent
                    else (
                        float(instance.discount_percent)
                        if instance.discount_percent
                        else None
                    )
                )
                discount_amount = (
                    float(ap.discount_amount)
                    if ap.discount_amount
                    else (
                        float(instance.discount_amount)
                        if instance.discount_amount
                        else None
                    )
                )

                # Thêm vào activity_dates
                activity_dates.append(
                    {
                        "id": activity_date.id,
                        "packageId": activity_package.id if activity_package else None,
                        "discount_percent": (
                            str(discount_percent)
                            if discount_percent is not None
                            else None
                        ),
                        "discount_amount": (
                            str(discount_amount)
                            if discount_amount is not None
                            else None
                        ),
                    }
                )

                # Group theo Activity để tạo mảng activitys
                if activity:
                    activity_id = activity.id
                    # Tính discount lớn nhất (ưu tiên discount_percent)
                    current_discount = (
                        discount_percent if discount_percent is not None else 0
                    )

                    if activity_id not in activity_map:
                        # Lấy thumbnail (chỉ 1 ảnh đầu tiên) từ ActivityImage
                        thumbnail = None
                        try:
                            first_image = activity.images.first()
                            if first_image and first_image.image:
                                thumbnail = first_image.image
                        except Exception:
                            pass

                        activity_map[activity_id] = {
                            "id": activity.id,
                            "name": activity.name,
                            "review_count": activity.review_count,
                            "avg_star": activity.avg_star,
                            "avg_price": activity.avg_price,
                            "thumbnails": thumbnail,
                            "discount": current_discount,
                        }
                    else:
                        # Cập nhật discount lớn nhất
                        activity_map[activity_id]["discount"] = max(
                            activity_map[activity_id]["discount"], current_discount
                        )

            # Thay thế activity_promotions bằng activity_dates và thêm activitys
            data.pop("activity_promotions", None)
            data["activity_dates"] = activity_dates
            data["activitys"] = list(activity_map.values())

        return Response(
            {
                "isSuccess": True,
                "message": "Lấy chi tiết promotion thành công",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


# Endpoint chung để tạo promotion với cấu trúc mới
class PromotionCreateView(generics.CreateAPIView):
    # serializer_class = PromotionCreateSerializer  # Không dùng serializer nữa

    def create(self, request, *args, **kwargs):
        data = request.data
        promotion_id = data.get("promotion_id")
        promotion_type = data.get("type")

        if not promotion_id:
            return Response(
                {
                    "isSuccess": False,
                    "message": "promotion_id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not promotion_type:
            return Response(
                {
                    "isSuccess": False,
                    "message": "type is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lấy promotion đã tồn tại
        try:
            promotion = Promotion.objects.get(id=promotion_id)
        except Promotion.DoesNotExist:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Tạo promotion thất bại",
                    "error": f"Promotion với id {promotion_id} không tồn tại",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Kiểm tra promotion_type phù hợp
        if (
            promotion_type == "hotel"
            and promotion.promotion_type != PromotionType.HOTEL
        ):
            return Response(
                {
                    "isSuccess": False,
                    "message": "Tạo promotion thất bại",
                    "error": "Promotion type không khớp. Promotion phải là loại HOTEL",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif (
            promotion_type == "flight"
            and promotion.promotion_type != PromotionType.FLIGHT
        ):
            return Response(
                {
                    "isSuccess": False,
                    "message": "Tạo promotion thất bại",
                    "error": "Promotion type không khớp. Promotion phải là loại FLIGHT",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif (
            promotion_type == "activity"
            and promotion.promotion_type != PromotionType.ACTIVITY
        ):
            return Response(
                {
                    "isSuccess": False,
                    "message": "Tạo promotion thất bại",
                    "error": "Promotion type không khớp. Promotion phải là loại ACTIVITY",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif promotion_type == "car" and promotion.promotion_type != PromotionType.CAR:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Tạo promotion thất bại",
                    "error": "Promotion type không khớp. Promotion phải là loại CAR",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        errors = []

        if promotion_type == "hotel":
            # hotel_id = data["hotel_id"]
            rooms_data = data["rooms"]

            # Tạo RoomPromotion cho từng room
            rooms_response = []
            for room_data in rooms_data:
                try:
                    room = Room.objects.get(id=room_data["id"], hotel=hotel)
                    discount_percent = (
                        room_data["discount_percent"]
                        if "discount_percent" in room_data
                        and room_data["discount_percent"] is not None
                        else promotion.discount_percent
                    )
                    discount_amount = (
                        room_data["discount_amount"]
                        if "discount_amount" in room_data
                        and room_data["discount_amount"] is not None
                        else promotion.discount_amount
                    )
                    room_promotion = RoomPromotion.objects.create(
                        promotion=promotion,
                        room=room,
                        discount_percent=discount_percent,
                        discount_amount=discount_amount,
                    )
                    rooms_response.append(
                        {
                            "id": room.id,
                            "discount_percent": (
                                str(room_promotion.discount_percent)
                                if room_promotion.discount_percent
                                else None
                            ),
                            "discount_amount": (
                                str(room_promotion.discount_amount)
                                if room_promotion.discount_amount
                                else None
                            ),
                        }
                    )

                except Exception as e:
                    errors.append(
                        f"Lỗi khi tạo promotion cho room {room_data['id']}: {str(e)}"
                    )

            response_data = {
                "promotion_id": promotion_id,
                "type": "hotel",
                # "hotel_id": hotel_id,
                "rooms": rooms_response,
            }

        elif promotion_type == "flight":
            # airline_id = data["airline_id"]
            flights_data = data["flights"]

            # Tạo FlightPromotion cho từng flight
            flights_response = []
            for flight_data in flights_data:
                try:
                    flight = Flight.objects.get(id=flight_data["id"])
                    discount_percent = (
                        flight_data["discount_percent"]
                        if "discount_percent" in flight_data
                        and flight_data["discount_percent"] is not None
                        else promotion.discount_percent
                    )
                    discount_amount = (
                        flight_data["discount_amount"]
                        if "discount_amount" in flight_data
                        and flight_data["discount_amount"] is not None
                        else promotion.discount_amount
                    )
                    flight_promotion = FlightPromotion.objects.create(
                        promotion=promotion,
                        flight=flight,
                        discount_percent=discount_percent,
                        discount_amount=discount_amount,
                    )
                    flights_response.append(
                        {
                            "id": flight.id,
                            "discount_percent": (
                                str(flight_promotion.discount_percent)
                                if flight_promotion.discount_percent
                                else None
                            ),
                            "discount_amount": (
                                str(flight_promotion.discount_amount)
                                if flight_promotion.discount_amount
                                else None
                            ),
                        }
                    )
                except Exception as e:
                    errors.append(
                        f"Lỗi khi tạo promotion cho flight {flight_data['id']}: {str(e)}"
                    )

            response_data = {
                "promotion_id": promotion_id,
                "type": "flight",
                # "airline_id": airline_id,
                "flights": flights_response,
            }

        elif promotion_type == "activity":
            # Chỉ hỗ trợ format mới: áp dụng promotion cho ActivityDate
            if "actDates" not in data or not data["actDates"]:
                errors.append("actDates is required for activity promotion")
            else:
                from activities.models import ActivityDate

                act_dates_data = data["actDates"]
                act_dates_response = []

                for act_date_data in act_dates_data:
                    try:
                        activity_date = ActivityDate.objects.get(id=act_date_data["id"])
                        discount_percent = (
                            act_date_data["discount_percent"]
                            if "discount_percent" in act_date_data
                            and act_date_data["discount_percent"] is not None
                            else promotion.discount_percent
                        )
                        discount_amount = (
                            act_date_data["discount_amount"]
                            if "discount_amount" in act_date_data
                            and act_date_data["discount_amount"] is not None
                            else promotion.discount_amount
                        )
                        activity_promotion = ActivityPromotion.objects.create(
                            promotion=promotion,
                            activity_date=activity_date,
                            discount_percent=discount_percent,
                            discount_amount=discount_amount,
                        )
                        act_dates_response.append(
                            {
                                "id": activity_date.id,
                                "discount_percent": (
                                    str(activity_promotion.discount_percent)
                                    if activity_promotion.discount_percent
                                    else None
                                ),
                                "discount_amount": (
                                    str(activity_promotion.discount_amount)
                                    if activity_promotion.discount_amount
                                    else None
                                ),
                            }
                        )
                    except ActivityDate.DoesNotExist:
                        errors.append(
                            f"ActivityDate {act_date_data['id']} không tồn tại"
                        )
                    except Exception as e:
                        errors.append(
                            f"Lỗi khi tạo promotion cho ActivityDate {act_date_data['id']}: {str(e)}"
                        )

                if not errors:
                    response_data = {
                        "promotion_id": promotion_id,
                        "type": "activity",
                        "activity_id": data.get("activity_id"),
                        "activity_package": data.get("activity_package"),
                        "actDates": act_dates_response,
                    }

        elif promotion_type == "car":
            cars_data = data["cars"]

            # Tạo CarPromotion cho từng car
            cars_response = []
            for car_data in cars_data:
                try:
                    car = Car.objects.get(id=car_data["id"])
                    discount_percent = (
                        car_data["discount_percent"]
                        if "discount_percent" in car_data
                        and car_data["discount_percent"] is not None
                        else promotion.discount_percent
                    )
                    discount_amount = (
                        car_data["discount_amount"]
                        if "discount_amount" in car_data
                        and car_data["discount_amount"] is not None
                        else promotion.discount_amount
                    )
                    car_promotion = CarPromotion.objects.create(
                        promotion=promotion,
                        car=car,
                        discount_percent=discount_percent,
                        discount_amount=discount_amount,
                    )
                    cars_response.append(
                        {
                            "id": car.id,
                            "discount_percent": (
                                str(car_promotion.discount_percent)
                                if car_promotion.discount_percent
                                else None
                            ),
                            "discount_amount": (
                                str(car_promotion.discount_amount)
                                if car_promotion.discount_amount
                                else None
                            ),
                        }
                    )
                except Car.DoesNotExist:
                    errors.append(f"Car {car_data['id']} không tồn tại")
                except Exception as e:
                    errors.append(
                        f"Lỗi khi tạo promotion cho car {car_data['id']}: {str(e)}"
                    )

            response_data = {
                "promotion_id": promotion_id,
                "type": "car",
                "cars": cars_response,
            }

        # Kiểm tra nếu có lỗi và không có item nào được tạo
        has_items = False
        if promotion_type == "hotel":
            has_items = len(response_data.get("rooms", [])) > 0
        elif promotion_type == "flight":
            has_items = len(response_data.get("flights", [])) > 0
        elif promotion_type == "activity":
            has_items = len(response_data.get("items", [])) > 0
        elif promotion_type == "car":
            has_items = len(response_data.get("cars", [])) > 0

        if errors and not has_items:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Tạo promotion thất bại",
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if errors:
            response_data["errors"] = errors

        return Response(
            {
                "isSuccess": True,
                "message": "Tạo promotion thành công",
                "data": response_data,
            },
            status=status.HTTP_201_CREATED,
        )


class PromotionListAdminView(generics.ListCreateAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionAdminSerializer
    pagination_class = PromotionCommonPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        min_date = params.get("min_date")

        if min_date:
            queryset = queryset.filter(end_date__gte=min_date)

        promotion_type = params.get("promotion_type")
        if promotion_type:
            queryset = queryset.filter(promotion_type=promotion_type)

        title = params.get("title")
        if title:
            queryset = queryset.filter(title__icontains=title)

        description = params.get("description")
        if description:
            queryset = queryset.filter(description__icontains=description)

        min_discount_percent = params.get("min_discount_percent")
        if min_discount_percent:
            queryset = queryset.filter(discount_percent__gte=min_discount_percent)

        max_discount_percent = params.get("max_discount_percent")
        if max_discount_percent:
            queryset = queryset.filter(discount_percent__lte=max_discount_percent)

        min_discount_amount = params.get("min_discount_amount")
        if min_discount_amount:
            queryset = queryset.filter(discount_amount__gte=min_discount_amount)

        max_discount_amount = params.get("max_discount_amount")
        if max_discount_amount:
            queryset = queryset.filter(discount_amount__lte=max_discount_amount)

        min_start_date = params.get("min_start_date")
        if min_start_date:
            queryset = queryset.filter(start_date__gte=min_start_date)

        max_start_date = params.get("max_start_date")
        if max_start_date:
            queryset = queryset.filter(start_date__lte=max_start_date)

        min_end_date = params.get("min_end_date")
        if min_end_date:
            queryset = queryset.filter(end_date__gte=min_end_date)

        max_end_date = params.get("max_end_date")
        if max_end_date:
            queryset = queryset.filter(end_date__lte=max_end_date)

        is_active = params.get("is_active")
        if is_active:
            queryset = queryset.filter(is_active=is_active)

        sort_params = params.get("sort")
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
            self.paginator.context = {"message": "Fetched promotions successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched promotions successfully!",
                "meta": {"totalItems": len(queryset), "pagination": None},
                "data": serializer.data,
            }
        )


class PromotionUpdateView(generics.UpdateAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def update(self, request, *args, **kwargs):
        promotion = self.get_object()
        serializer = self.get_serializer(promotion, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Promotion updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class PromotionDeleteView(generics.DestroyAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Promotion deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class RoomPromotionListAdminView(generics.ListCreateAPIView):
    queryset = RoomPromotion.objects.all()
    serializer_class = RoomPromotionAdminSerializer
    pagination_class = PromotionCommonPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        promotion_id = params.get("promotion_id")

        if promotion_id:
            queryset = queryset.filter(promotion_id=promotion_id)

        min_discount_percent = params.get("min_discount_percent")

        if min_discount_percent:
            queryset = queryset.filter(discount_percent__gte=min_discount_percent)

        max_discount_percent = params.get("max_discount_percent")

        if max_discount_percent:
            queryset = queryset.filter(discount_percent__lte=max_discount_percent)

        min_discount_amount = params.get("min_discount_amount")

        if min_discount_amount:
            queryset = queryset.filter(discount_percent__gte=min_discount_amount)

        max_discount_amount = params.get("max_discount_amount")

        if max_discount_amount:
            queryset = queryset.filter(discount_percent__lte=max_discount_amount)

        owner_id = params.get("owner_id")

        if owner_id:
            queryset = queryset.filter(room__hotel__owner_id=owner_id)

        sort_params = params.get("sort")
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
            self.paginator.context = {
                "message": "Fetched room promotions successfully!"
            }
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched room promotions successfully!",
                "meta": {"totalItems": len(queryset), "pagination": None},
                "data": serializer.data,
            }
        )


class RoomPromotionAdminCreateView(generics.CreateAPIView):
    queryset = RoomPromotion.objects.all()
    serializer_class = RoomPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            room_promotion = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Room promotion created successfully",
                    "data": RoomPromotionAdminCreateSerializer(room_promotion).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create room promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class RoomPromotionAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RoomPromotion.objects.all()
    serializer_class = RoomPromotionAdminSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "Room promotion details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


class RoomPromotionAdminUpdateView(generics.UpdateAPIView):
    queryset = RoomPromotion.objects.all()
    serializer_class = RoomPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def update(self, request, *args, **kwargs):
        room_promotion = self.get_object()
        serializer = self.get_serializer(
            room_promotion, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Room promotion updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update room promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class RoomPromotionAdminDeleteView(generics.DestroyAPIView):
    queryset = RoomPromotion.objects.all()
    serializer_class = RoomPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Room promotion deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class CarPromotionListAdminView(generics.ListCreateAPIView):
    queryset = CarPromotion.objects.all()
    serializer_class = CarPromotionAdminSerializer
    pagination_class = PromotionCommonPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        promotion_id = params.get("promotion_id")

        if promotion_id:
            queryset = queryset.filter(promotion_id=promotion_id)

        min_discount_percent = params.get("min_discount_percent")

        if min_discount_percent:
            queryset = queryset.filter(discount_percent__gte=min_discount_percent)

        max_discount_percent = params.get("max_discount_percent")

        if max_discount_percent:
            queryset = queryset.filter(discount_percent__lte=max_discount_percent)

        min_discount_amount = params.get("min_discount_amount")

        if min_discount_amount:
            queryset = queryset.filter(discount_percent__gte=min_discount_amount)

        max_discount_amount = params.get("max_discount_amount")

        if max_discount_amount:
            queryset = queryset.filter(discount_percent__lte=max_discount_amount)

        driver_id = params.get("driver_id")

        if driver_id:
            queryset = queryset.filter(car__user_id=driver_id)

        sort_params = params.get("sort")
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
            self.paginator.context = {"message": "Fetched car promotions successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched car promotions successfully!",
                "meta": {"totalItems": len(queryset), "pagination": None},
                "data": serializer.data,
            }
        )


class CarPromotionAdminCreateView(generics.CreateAPIView):
    queryset = CarPromotion.objects.all()
    serializer_class = CarPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            car_promotion = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Car promotion created successfully",
                    "data": CarPromotionAdminCreateSerializer(car_promotion).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create car promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class CarPromotionAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CarPromotion.objects.all()
    serializer_class = CarPromotionAdminSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "Car promotion details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


class CarPromotionAdminUpdateView(generics.UpdateAPIView):
    queryset = CarPromotion.objects.all()
    serializer_class = CarPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def update(self, request, *args, **kwargs):
        car_promotion = self.get_object()
        serializer = self.get_serializer(car_promotion, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Car promotion updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update car promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class CarPromotionAdminDeleteView(generics.DestroyAPIView):
    queryset = CarPromotion.objects.all()
    serializer_class = CarPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Car promotion deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class FlightPromotionListAdminView(generics.ListCreateAPIView):
    queryset = FlightPromotion.objects.all()
    serializer_class = FlightPromotionAdminSerializer
    pagination_class = PromotionCommonPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        promotion_id = params.get("promotion_id")

        if promotion_id:
            queryset = queryset.filter(promotion_id=promotion_id)

        min_discount_percent = params.get("min_discount_percent")

        if min_discount_percent:
            queryset = queryset.filter(discount_percent__gte=min_discount_percent)

        max_discount_percent = params.get("max_discount_percent")

        if max_discount_percent:
            queryset = queryset.filter(discount_percent__lte=max_discount_percent)

        min_discount_amount = params.get("min_discount_amount")

        if min_discount_amount:
            queryset = queryset.filter(discount_percent__gte=min_discount_amount)

        max_discount_amount = params.get("max_discount_amount")

        if max_discount_amount:
            queryset = queryset.filter(discount_percent__lte=max_discount_amount)

        flight_operations_staff_id = params.get("flight_operations_staff_id")

        if flight_operations_staff_id:
            queryset = queryset.filter(
                flight__airline__flight_operations_staff_id=flight_operations_staff_id
            )

        sort_params = params.get("sort")
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
            self.paginator.context = {
                "message": "Fetched flight promotions successfully!"
            }
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched flight promotions successfully!",
                "meta": {"totalItems": len(queryset), "pagination": None},
                "data": serializer.data,
            }
        )


class FlightPromotionAdminCreateView(generics.CreateAPIView):
    queryset = FlightPromotion.objects.all()
    serializer_class = FlightPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            flight_promotion = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Flight promotion created successfully",
                    "data": FlightPromotionAdminCreateSerializer(flight_promotion).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create flight promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class FlightPromotionAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FlightPromotion.objects.all()
    serializer_class = FlightPromotionAdminSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "Flight promotion details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


class FlightPromotionAdminUpdateView(generics.UpdateAPIView):
    queryset = FlightPromotion.objects.all()
    serializer_class = FlightPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def update(self, request, *args, **kwargs):
        flight_promotion = self.get_object()
        serializer = self.get_serializer(
            flight_promotion, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Flight promotion updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update flight promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class FlightPromotionAdminDeleteView(generics.DestroyAPIView):
    queryset = FlightPromotion.objects.all()
    serializer_class = FlightPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Flight promotion deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class ActivityPromotionListAdminView(generics.ListCreateAPIView):
    queryset = ActivityPromotion.objects.all()
    serializer_class = ActivityPromotionAdminSerializer
    pagination_class = PromotionCommonPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        promotion_id = params.get("promotion_id")

        if promotion_id:
            queryset = queryset.filter(promotion_id=promotion_id)

        min_discount_percent = params.get("min_discount_percent")

        if min_discount_percent:
            queryset = queryset.filter(discount_percent__gte=min_discount_percent)

        max_discount_percent = params.get("max_discount_percent")

        if max_discount_percent:
            queryset = queryset.filter(discount_percent__lte=max_discount_percent)

        min_discount_amount = params.get("min_discount_amount")

        if min_discount_amount:
            queryset = queryset.filter(discount_percent__gte=min_discount_amount)

        max_discount_amount = params.get("max_discount_amount")

        if max_discount_amount:
            queryset = queryset.filter(discount_percent__lte=max_discount_amount)

        event_organizer_id = params.get("event_organizer_id")

        if event_organizer_id:
            queryset = queryset.filter(
                activity_date__activity_package__activity__event_organizer_id=event_organizer_id
            )

        sort_params = params.get("sort")
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
            self.paginator.context = {
                "message": "Fetched activity promotions successfully!"
            }
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched activity promotions successfully!",
                "meta": {"totalItems": len(queryset), "pagination": None},
                "data": serializer.data,
            }
        )


class ActivityPromotionAdminCreateView(generics.CreateAPIView):
    queryset = ActivityPromotion.objects.all()
    serializer_class = ActivityPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            activity_promotion = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Activity promotion created successfully",
                    "data": ActivityPromotionAdminCreateSerializer(
                        activity_promotion
                    ).data,
                },
                status=200,
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create activity promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class ActivityPromotionAdminBulkCreateView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data.get("items", [])

        if not isinstance(data, list) or len(data) == 0:
            return Response(
                {"isSuccess": False, "message": "items must be a non-empty list"},
                status=400,
            )

        activity_promotions = []

        try:
            for item in data:
                activity_promotions.append(
                    ActivityPromotion(
                        promotion_id=item["promotion_id"],
                        activity_date_id=item["activity_date_id"],
                        discount_percent=item.get("discount_percent", 0.0),
                        discount_amount=item.get("discount_amount", 0.0),
                    )
                )

            # Bulk create
            ActivityPromotion.objects.bulk_create(activity_promotions)

            return Response(
                {
                    "isSuccess": True,
                    "message": "Bulk created successfully",
                    "data": {"created_count": len(activity_promotions)},
                },
                status=201,
            )

        except KeyError as e:
            return Response(
                {"isSuccess": False, "message": f"Missing field: {str(e)}"}, status=400
            )

        except Exception as e:
            return Response({"isSuccess": False, "message": str(e)}, status=500)


class ActivityPromotionAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ActivityPromotion.objects.all()
    serializer_class = ActivityPromotionAdminSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def retrieve(self, request, *args, **kwargs):
        """
        Override phương thức `retrieve` để trả về response chuẩn cho việc lấy thông tin chi tiết.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "Activity promotion details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


class ActivityPromotionAdminUpdateView(generics.UpdateAPIView):
    queryset = ActivityPromotion.objects.all()
    serializer_class = ActivityPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def update(self, request, *args, **kwargs):
        activity_promotion = self.get_object()
        serializer = self.get_serializer(
            activity_promotion, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Activity promotion updated successfully",
                    "data": serializer.data,
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update activity promotion",
                "data": serializer.errors,
            },
            status=400,
        )


class ActivityPromotionAdminDeleteView(generics.DestroyAPIView):
    queryset = ActivityPromotion.objects.all()
    serializer_class = ActivityPromotionAdminCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Không cần kiểm tra quyền

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Activity promotion deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class ActivityPromotionAdminBulkDeleteView(APIView):
    def delete(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        # Validate
        if not isinstance(ids, list) or len(ids) == 0:
            return Response(
                {"isSuccess": False, "message": "ids must be a non-empty list"},
                status=400,
            )

        try:
            # Đếm xem có bao nhiêu record khớp ID
            deleted_count, _ = ActivityPromotion.objects.filter(id__in=ids).delete()

            return Response(
                {
                    "isSuccess": True,
                    "message": "Bulk deleted successfully",
                    "data": {"deleted_count": deleted_count},
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {"isSuccess": False, "message": str(e)},
                status=500,
            )
