# hotels/search_history_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import UserSearchHistory
from datetime import datetime


class SaveSearchHistoryAPI(APIView):
    """
    API: POST /api/hotels/save-search-history/
    Lưu lịch sử tìm kiếm của user
    """
    
    def post(self, request):
        data = request.data
        
        # Validate required fields
        destination = data.get('destination')
        if not destination:
            return Response({
                "isSuccess": False,
                "message": "Destination is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse dates
        check_in = None
        check_out = None
        if data.get('check_in'):
            try:
                check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if data.get('check_out'):
            try:
                check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Create search history
        history_data = {
            'destination': destination,
            'check_in': check_in,
            'check_out': check_out,
            'adults': data.get('adults', 1),
            'children': data.get('children', 0),
            'rooms': data.get('rooms', 1),
        }
        
        # Associate with user or session
        if request.user.is_authenticated:
            history_data['user'] = request.user
        else:
            # For anonymous users, use session key
            if not request.session.session_key:
                request.session.create()
            history_data['session_key'] = request.session.session_key
        
        # Save to database
        try:
            search_history = UserSearchHistory.objects.create(**history_data)
            
            return Response({
                "isSuccess": True,
                "message": "Search history saved successfully",
                "data": {
                    "id": search_history.id,
                    "destination": search_history.destination,
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                "isSuccess": False,
                "message": f"Error saving search history: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
