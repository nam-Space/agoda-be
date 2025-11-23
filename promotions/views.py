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


# Promotion
class PromotionListCreateView(generics.ListCreateAPIView):
    serializer_class = PromotionSerializer

    def get_queryset(self):
        now = timezone.now()
        queryset = Promotion.objects.prefetch_related(
            "flight_promotions__flight",
            "activity_promotions__activity",
            "room_promotions__room__hotel",
            "car_promotions__car",
        ).filter(end_date__gte=now) 
        queryset = queryset.order_by("-created_at")
        
        promotion_type = self.request.query_params.get("promotion_type")
        if promotion_type:
            queryset = queryset.filter(promotion_type=promotion_type)
        return queryset


class PromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Promotion.objects.prefetch_related(
            "flight_promotions__flight",
            "activity_promotions__activity",
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
            items_data = data['items']
            
            # Tạo ActivityPromotion cho từng activity
            items_response = []
            for item_data in items_data:
                try:
                    activity = Activity.objects.get(id=item_data['id'])
                    activity_promotion = ActivityPromotion.objects.create(
                        promotion=promotion,
                        activity=activity,
                        discount_percent=item_data.get('discount_percent'),
                        discount_amount=item_data.get('discount_amount'),
                    )
                    items_response.append({
                        'id': activity.id,
                        'discount_percent': str(activity_promotion.discount_percent) if activity_promotion.discount_percent else None,
                        'discount_amount': str(activity_promotion.discount_amount) if activity_promotion.discount_amount else None,
                    })
                except Activity.DoesNotExist:
                    errors.append(f"Activity {item_data['id']} không tồn tại")
                except Exception as e:
                    errors.append(f"Lỗi khi tạo promotion cho activity {item_data['id']}: {str(e)}")
            
            response_data = {
                "promotion_id": promotion_id,
                "type": "activity",
                "items": items_response
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

