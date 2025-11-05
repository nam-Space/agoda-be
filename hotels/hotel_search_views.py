# hotels/hotel_search_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from django.db.models import Q
from .models import Hotel
from rooms.models import Room, RoomBookingDetail


class HotelSearchAPI(APIView):
    """
    API: GET /api/hotels/search/
    Tìm kiếm khách sạn có phòng trống
    Query params: destination, check_in, check_out, adults, rooms
    """
    
    def get(self, request):
        destination = request.query_params.get('destination', '')
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        adults = int(request.query_params.get('adults', 1))
        num_rooms = int(request.query_params.get('rooms', 1))
        
        if not destination or not check_in or not check_out:
            return Response(
                {"error": "Missing required parameters: destination, check_in, check_out"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        hotels = Hotel.objects.filter(
            Q(city__name__icontains=destination) | Q(name__icontains=destination)
        ).distinct()
        
        available_hotels = []
        for hotel in hotels:
            has_available_room = self._check_hotel_availability(
                hotel, check_in_date, check_out_date, adults, num_rooms
            )
            if has_available_room:
                available_hotels.append(hotel)
        
        from .serializers import HotelSearchSerializer
        serializer = HotelSearchSerializer(available_hotels, many=True)
        
        return Response({
            "isSuccess": True,
            "total": len(available_hotels),
            "data": serializer.data
        })
    
    def _check_hotel_availability(self, hotel, check_in, check_out, adults, num_rooms):
        """
        Kiểm tra xem hotel có phòng trống trong khoảng ngày không
        """
        rooms = Room.objects.filter(
            hotel=hotel,
            available=True,
            adults_capacity__gte=adults
        )
        
        for room in rooms:
            overlapping_bookings = RoomBookingDetail.objects.filter(
                room=room,
                check_in__lt=check_out,
                check_out__gt=check_in 
            ).count()
            
            if overlapping_bookings < room.total_rooms:
                return True
        
        return False


class RoomAvailabilityAPI(APIView):
    """
    API: GET /api/hotels/<hotel_id>/rooms/availability/
    Tìm phòng trống của 1 khách sạn cụ thể
    Query params: check_in, check_out, adults
    """
    
    def get(self, request, hotel_id):
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        adults = int(request.query_params.get('adults', 1))
        
        if not check_in or not check_out:
            return Response(
                {"error": "Missing required parameters: check_in, check_out"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            hotel = Hotel.objects.get(id=hotel_id)
        except Hotel.DoesNotExist:
            return Response(
                {"error": "Hotel not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        rooms = Room.objects.filter(
            hotel=hotel,
            available=True,
            adults_capacity__gte=adults
        )
        
        available_rooms = []
        for room in rooms:
            overlapping_bookings = RoomBookingDetail.objects.filter(
                room=room,
                check_in__lt=check_out_date,
                check_out__gt=check_in_date
            ).count()
            
            available_count = room.total_rooms - overlapping_bookings
            
            if available_count > 0:
                room.rooms_available = available_count
                available_rooms.append(room)
        
        from rooms.serializers import RoomSerializer
        serializer = RoomSerializer(available_rooms, many=True)
        
        data = serializer.data
        for i, room_data in enumerate(data):
            room_data['rooms_available'] = available_rooms[i].rooms_available
        
        return Response({
            "isSuccess": True,
            "hotel_id": hotel_id,
            "hotel_name": hotel.name,
            "total": len(available_rooms),
            "data": data
        })
