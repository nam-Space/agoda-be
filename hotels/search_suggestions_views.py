# hotels/search_suggestions_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Hotel, UserSearchHistory
from cities.models import City
from datetime import datetime


class SearchSuggestionsAPI(APIView):
    """
    API: GET /api/hotels/search-suggestions/
    Trả về gợi ý cho autocomplete search:
    - Recent/Popular searches
    - Featured properties
    - Popular destinations
    """
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        
        # 1. Recent searches from database
        recent_searches = []
        
        # Get search history for logged-in user or by session
        if request.user.is_authenticated:
            history_qs = UserSearchHistory.objects.filter(
                user=request.user
            )[:3]
        else:
            # For anonymous users, get from session
            session_key = request.session.session_key
            if session_key:
                history_qs = UserSearchHistory.objects.filter(
                    session_key=session_key
                )[:3]
            else:
                history_qs = UserSearchHistory.objects.none()
        
        for history in history_qs:
            # Format dates
            if history.check_in and history.check_out:
                check_in_str = history.check_in.strftime('%d tháng %m %Y')
                check_out_str = history.check_out.strftime('%d tháng %m %Y')
                dates = f"{check_in_str} - {check_out_str}"
            else:
                dates = ""
            
            recent_searches.append({
                "city": history.destination,
                "dates": dates,
                "guests": history.adults + history.children
            })
        
        # 2. Featured properties (khách sạn đặc biệt)
        featured_properties = Hotel.objects.filter(
            Q(name__icontains="Ascott") | 
            Q(name__icontains="InterContinental") |
            Q(name__icontains="Hilton")
        ).values('id', 'name', 'description')[:2]
        
        featured_list = []
        for hotel in featured_properties:
            # Tạo tag description
            tag = hotel.get('description', '')[:50] if hotel.get('description') else "Khách sạn cao cấp"
            featured_list.append({
                "id": hotel['id'],
                "name": hotel['name'],
                "tag": tag
            })
        
        # Nếu không có featured hotels, lấy top rated hotels
        if len(featured_list) == 0:
            top_hotels = Hotel.objects.filter(
                avg_star__gte=4.0
            ).order_by('-avg_star', '-review_count')[:2]
            
            for hotel in top_hotels:
                tag = hotel.description[:50] if hotel.description else "Khách sạn chất lượng cao"
                featured_list.append({
                    "id": hotel.id,
                    "name": hotel.name,
                    "tag": tag
                })
        
        # 3. Popular destinations - Vietnam
        vietnam_cities = City.objects.filter(
            country__name__icontains='Vietnam'
        ).annotate(
            hotel_count=Count('hotels')
        ).filter(
            hotel_count__gt=0
        ).order_by('-hotel_count').values('id', 'name', 'hotel_count')[:6]
        
        vietnam_destinations = []
        # Mapping tags cho các thành phố phổ biến
        city_tags = {
            'Hồ Chí Minh': 'nhà hàng, mua sắm',
            'Hà Nội': 'nhà hàng, tham quan',
            'Vũng Tàu': 'bãi biển, nhà hàng',
            'Nha Trang': 'bãi biển, nhà hàng',
            'Đà Nẵng': 'bãi biển, tham quan',
            'Đà Lạt': 'thiên nhiên, tham quan',
        }
        
        for city in vietnam_cities:
            city_name = city['name']
            tags = city_tags.get(city_name, 'du lịch, nghỉ dưỡng')
            vietnam_destinations.append({
                "id": city['id'],
                "name": city_name,
                "count": f"({city['hotel_count']})",
                "tags": tags
            })
        
        # 4. International destinations (mock hoặc từ DB nếu có)
        # Có thể query từ cities với country khác Vietnam
        international_cities = City.objects.exclude(
            country__name__icontains='Vietnam'
        ).annotate(
            hotel_count=Count('hotels')
        ).filter(
            hotel_count__gt=0
        ).order_by('-hotel_count').values('id', 'name', 'hotel_count')[:3]
        
        international_destinations = []
        intl_tags = {
            'Singapore': 'mua sắm, nhà hàng',
            'Seoul': 'mua sắm, nhà hàng',
            'Bangkok': 'mua sắm, nhà hàng',
        }
        
        for city in international_cities:
            city_name = city['name']
            tags = intl_tags.get(city_name, 'du lịch, mua sắm')
            international_destinations.append({
                "id": city['id'],
                "name": city_name,
                "count": f"({city['hotel_count']})",
                "tags": tags
            })
        
        # Không dùng default data - chỉ show data thật từ DB
        
        # 5. Filtered suggestions based on query
        filtered_suggestions = []
        if query:
            # Search in cities and hotels
            matching_cities = City.objects.filter(
                Q(name__icontains=query)
            ).annotate(
                hotel_count=Count('hotels')
            ).filter(hotel_count__gt=0).values('id', 'name', 'hotel_count')[:5]
            
            for city in matching_cities:
                filtered_suggestions.append({
                    "type": "city",
                    "id": city['id'],
                    "name": city['name'],
                    "count": f"({city['hotel_count']})"
                })
            
            matching_hotels = Hotel.objects.filter(
                Q(name__icontains=query)
            ).values('id', 'name', 'city__name')[:5]
            
            for hotel in matching_hotels:
                filtered_suggestions.append({
                    "type": "hotel",
                    "id": hotel['id'],
                    "name": hotel['name'],
                    "city": hotel.get('city__name', 'N/A')
                })
        
        return Response({
            "isSuccess": True,
            "data": {
                "recent_searches": recent_searches,
                "featured_properties": featured_list,
                "vietnam_destinations": vietnam_destinations,
                "international_destinations": international_destinations,
                "filtered_suggestions": filtered_suggestions if query else []
            }
        })
