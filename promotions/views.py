from rest_framework.pagination import PageNumberPagination
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Promotion, FlightPromotion, ActivityPromotion, RoomPromotion, CarPromotion, PromotionType
from .serializers import PromotionSerializer, PromotionCreateSerializer
from hotels.models import Hotel
from flights.models import Flight
from activities.models import Activity
from rooms.models import Room
from cars.models import Car
from airlines.models import Airline
from django.utils import timezone

class PromotionCommonPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "isSuccess": True,
            "message": self.context.get('message', "Fetched promotions successfully!"),
            "meta": {
                "totalItems": self.page.paginator.count,
                "currentPage": self.page.number,
                "itemsPerPage": self.get_page_size(self.request),
                "totalPages": self.page.paginator.num_pages,
            },
            "data": data,
        })

class PromotionListCreateView(generics.ListCreateAPIView):
    serializer_class = PromotionSerializer
    pagination_class = PromotionCommonPagination

    def get_queryset(self):
        now = timezone.now()
        queryset = Promotion.objects.prefetch_related(
            "flight_promotions__flight",
            "activity_promotions__activity_date",
            "room_promotions__room__hotel",
            "car_promotions__car",
        ).filter(end_date__gte=now).order_by("-id")
        
        promotion_type = self.request.query_params.get("promotion_type")
        if promotion_type:
            queryset = queryset.filter(promotion_type=promotion_type)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            self.paginator.context = {'message': "Fetched promotions successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "isSuccess": True,
            "message": "Fetched promotions successfully!",
            "meta": {
                "totalItems": len(queryset),
                "pagination": None
            },
            "data": serializer.data,
        })


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
        context["airline_id"] = q.get("airline_id")
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
                            thumbnail = first_img.image  # Nếu là CharField thì không cần .url
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
                        hotel_map[hid]["max_discount"] = max(hotel_map[hid]["max_discount"], discount)
                except Exception:
                    continue
            data["hotels"] = list(hotel_map.values())
        elif promotion_type == 3:  # ACTIVITY
            from activities.models import Activity, ActivityImage
            instance = self.get_object()
            
            # Lấy tất cả ActivityPromotion của promotion này
            activity_promotions = instance.activity_promotions.select_related(
                'activity_date__activity_package__activity'
            ).prefetch_related(
                'activity_date__activity_package__activity__images'
            ).all()
            
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
                discount_percent = float(ap.discount_percent) if ap.discount_percent else (float(instance.discount_percent) if instance.discount_percent else None)
                discount_amount = float(ap.discount_amount) if ap.discount_amount else (float(instance.discount_amount) if instance.discount_amount else None)
                
                # Thêm vào activity_dates
                activity_dates.append({
                    "id": activity_date.id,
                    "packageId": activity_package.id if activity_package else None,
                    "discount_percent": str(discount_percent) if discount_percent is not None else None,
                    "discount_amount": str(discount_amount) if discount_amount is not None else None,
                })
                
                # Group theo Activity để tạo mảng activitys
                if activity:
                    activity_id = activity.id
                    # Tính discount lớn nhất (ưu tiên discount_percent)
                    current_discount = discount_percent if discount_percent is not None else 0
                    
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
                            "review_count": activity.review_count,
                            "avg_star": activity.avg_star,
                            "avg_price": activity.avg_price,
                            "thumbnails": thumbnail,
                            "discount": current_discount,
                        }
                    else:
                        # Cập nhật discount lớn nhất
                        activity_map[activity_id]["discount"] = max(
                            activity_map[activity_id]["discount"],
                            current_discount
                        )
            
            # Thay thế activity_promotions bằng activity_dates và thêm activitys
            data.pop("activity_promotions", None)
            data["activity_dates"] = activity_dates
            data["activitys"] = list(activity_map.values())
            
        return Response(data)

# Endpoint chung để tạo promotion với cấu trúc mới
class PromotionCreateView(generics.CreateAPIView):
    serializer_class = PromotionCreateSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        promotion_id = data['promotion_id']
        promotion_type = data['type']
        
        try:
            promotion = Promotion.objects.get(id=promotion_id)
        except Promotion.DoesNotExist:
            return Response(
                {"error": "Không tìm thấy promotion"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Kiểm tra promotion_type phù hợp
        if promotion_type == 'hotel' and promotion.promotion_type != PromotionType.HOTEL:
            return Response(
                {"error": "Promotion type không khớp. Promotion phải là loại HOTEL"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif promotion_type == 'flight' and promotion.promotion_type != PromotionType.FLIGHT:
            return Response(
                {"error": "Promotion type không khớp. Promotion phải là loại FLIGHT"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif promotion_type == 'activity' and promotion.promotion_type != PromotionType.ACTIVITY:
            return Response(
                {"error": "Promotion type không khớp. Promotion phải là loại ACTIVITY"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif promotion_type == 'car' and promotion.promotion_type != PromotionType.CAR:
            return Response(
                {"error": "Promotion type không khớp. Promotion phải là loại CAR"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        errors = []
        
        if promotion_type == 'hotel':
            hotel_id = data['hotel_id']
            rooms_data = data['rooms']
            
            try:
                hotel = Hotel.objects.get(id=hotel_id)
            except Hotel.DoesNotExist:
                return Response(
                    {"error": "Không tìm thấy hotel"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Tạo RoomPromotion cho từng room
            rooms_response = []
            for room_data in rooms_data:
                try:
                    room = Room.objects.get(id=room_data['id'], hotel=hotel)
                    room_promotion = RoomPromotion.objects.create(
                        promotion=promotion,
                        room=room,
                        discount_percent=room_data.get('discount_percent'),
                        discount_amount=room_data.get('discount_amount'),
                    )
                    rooms_response.append({
                        'id': room.id,
                        'discount_percent': str(room_promotion.discount_percent) if room_promotion.discount_percent else None,
                        'discount_amount': str(room_promotion.discount_amount) if room_promotion.discount_amount else None,
                    })
                except Room.DoesNotExist:
                    errors.append(f"Room {room_data['id']} không tồn tại hoặc không thuộc hotel {hotel_id}")
                except Exception as e:
                    errors.append(f"Lỗi khi tạo promotion cho room {room_data['id']}: {str(e)}")
            
            response_data = {
                "promotion_id": promotion_id,
                "type": "hotel",
                "hotel_id": hotel_id,
                "rooms": rooms_response
            }
            
        elif promotion_type == 'flight':
            airline_id = data['airline_id']
            flights_data = data['flights']
            
            try:
                airline = Airline.objects.get(id=airline_id)
            except Airline.DoesNotExist:
                return Response(
                    {"error": "Không tìm thấy airline"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Tạo FlightPromotion cho từng flight
            flights_response = []
            for flight_data in flights_data:
                try:
                    flight = Flight.objects.get(id=flight_data['id'], airline=airline)
                    flight_promotion = FlightPromotion.objects.create(
                        promotion=promotion,
                        flight=flight,
                        discount_percent=flight_data.get('discount_percent'),
                        discount_amount=flight_data.get('discount_amount'),
                    )
                    flights_response.append({
                        'id': flight.id,
                        'discount_percent': str(flight_promotion.discount_percent) if flight_promotion.discount_percent else None,
                        'discount_amount': str(flight_promotion.discount_amount) if flight_promotion.discount_amount else None,
                    })
                except Flight.DoesNotExist:
                    errors.append(f"Flight {flight_data['id']} không tồn tại hoặc không thuộc airline {airline_id}")
                except Exception as e:
                    errors.append(f"Lỗi khi tạo promotion cho flight {flight_data['id']}: {str(e)}")
            
            response_data = {
                "promotion_id": promotion_id,
                "type": "flight",
                "airline_id": airline_id,
                "flights": flights_response
            }
            
        elif promotion_type == 'activity':
            # Chỉ hỗ trợ format mới: áp dụng promotion cho ActivityDate
            if 'actDates' not in data or not data['actDates']:
                errors.append("actDates is required for activity promotion")
            else:
                from activities.models import ActivityDate
                act_dates_data = data['actDates']
                act_dates_response = []
                
                for act_date_data in act_dates_data:
                    try:
                        activity_date = ActivityDate.objects.get(id=act_date_data['id'])
                        activity_promotion = ActivityPromotion.objects.create(
                            promotion=promotion,
                            activity_date=activity_date,
                            discount_percent=act_date_data.get('discount_percent'),
                            discount_amount=act_date_data.get('discount_amount'),
                        )
                        act_dates_response.append({
                            'id': activity_date.id,
                            'discount_percent': str(activity_promotion.discount_percent) if activity_promotion.discount_percent else None,
                            'discount_amount': str(activity_promotion.discount_amount) if activity_promotion.discount_amount else None,
                        })
                    except ActivityDate.DoesNotExist:
                        errors.append(f"ActivityDate {act_date_data['id']} không tồn tại")
                    except Exception as e:
                        errors.append(f"Lỗi khi tạo promotion cho ActivityDate {act_date_data['id']}: {str(e)}")
                
                if not errors:
                    response_data = {
                        "promotion_id": promotion_id,
                        "type": "activity",
                        "activity_id": data.get('activity_id'),
                        "activity_package": data.get('activity_package'),
                        "actDates": act_dates_response
                    }
            
        elif promotion_type == 'car':
            cars_data = data['cars']
            
            # Tạo CarPromotion cho từng car
            cars_response = []
            for car_data in cars_data:
                try:
                    car = Car.objects.get(id=car_data['id'])
                    car_promotion = CarPromotion.objects.create(
                        promotion=promotion,
                        car=car,
                        discount_percent=car_data.get('discount_percent'),
                        discount_amount=car_data.get('discount_amount'),
                    )
                    cars_response.append({
                        'id': car.id,
                        'discount_percent': str(car_promotion.discount_percent) if car_promotion.discount_percent else None,
                        'discount_amount': str(car_promotion.discount_amount) if car_promotion.discount_amount else None,
                    })
                except Car.DoesNotExist:
                    errors.append(f"Car {car_data['id']} không tồn tại")
                except Exception as e:
                    errors.append(f"Lỗi khi tạo promotion cho car {car_data['id']}: {str(e)}")
            
            response_data = {
                "promotion_id": promotion_id,
                "type": "car",
                "cars": cars_response
            }
        
        # Kiểm tra nếu có lỗi và không có item nào được tạo
        has_items = False
        if promotion_type == 'hotel':
            has_items = len(response_data.get('rooms', [])) > 0
        elif promotion_type == 'flight':
            has_items = len(response_data.get('flights', [])) > 0
        elif promotion_type == 'activity':
            has_items = len(response_data.get('items', [])) > 0
        elif promotion_type == 'car':
            has_items = len(response_data.get('cars', [])) > 0
        
        if errors and not has_items:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        
        if errors:
            response_data["errors"] = errors
        
        return Response(response_data, status=status.HTTP_201_CREATED)

