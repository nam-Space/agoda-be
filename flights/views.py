from rest_framework import viewsets
from rest_framework.response import Response
from datetime import datetime
from .models import Flight, FlightLeg, FlightBookingDetail, SeatClassPricing
from .serializers import FlightBookingDetailSerializer, FlightLegSerializer, FlightSerializer, SeatClassPricingSerializer

class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.select_related(
        'airline',
        'aircraft',
        'aircraft__airline'
    ).prefetch_related(
        'legs__departure_airport',
        'legs__arrival_airport',
        'seat_classes'
    ).all()
    serializer_class = FlightSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params
        
        # Filter theo baggage included
        baggage_included = q.get('baggageIncluded')
        if baggage_included and baggage_included.lower() == 'true':
            queryset = queryset.filter(baggage_included=True)
        
        # Filter theo airline (có thể multiple airlines)
        airlines = q.getlist('airlines[]') or [q.get('airline')]
        airlines = [a for a in airlines if a]  # Remove None/empty
        if airlines:
            queryset = queryset.filter(airline_id__in=airlines)
        
        # Filter theo số điểm dừng (có thể multiple)
        stops_list = q.getlist('stops[]')
        if stops_list:
            # Convert labels to numbers: "Bay Thẳng"=0, "1 Điểm Dừng"=1, ">2 Điểm Dừng"=2+
            stops_values = []
            for stop in stops_list:
                if stop == '0' or stop == 'Bay Thẳng':
                    stops_values.append(0)
                elif stop == '1' or stop == '1 Điểm Dừng':
                    stops_values.append(1)
                elif stop == '>2' or stop == '>2 Điểm Dừng':
                    # Lọc flights có >= 2 stops
                    pass
            
            if stops_values:
                queryset = queryset.filter(stops__in=stops_values)
            # Handle >2 stops
            if any(s in ['>2', '>2 Điểm Dừng'] for s in stops_list):
                queryset = queryset.filter(stops__gte=2)
        
        # Filter theo hạng ghế (có thể multiple)
        seat_classes = q.getlist('seatClasses[]') or [q.get('seatClass')]
        seat_classes = [sc for sc in seat_classes if sc]
        if seat_classes:
            queryset = queryset.filter(
                seat_classes__seat_class__in=seat_classes,
                seat_classes__available_seats__gt=0
            ).distinct()
        
        # Filter theo max duration (minutes)
        max_duration = q.get('maxDuration')
        if max_duration:
            queryset = queryset.filter(total_duration__lte=int(max_duration))
        
        # Filter theo max price
        max_price = q.get('maxPrice')
        if max_price:
            queryset = queryset.filter(base_price__lte=float(max_price))
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        q = request.query_params
        
        # Lấy params để filter thêm
        origin = q.get('origin')
        destination = q.get('destination')
        departure_date = q.get('departureDate')
        departure_hour = q.get('departureHour')  # 0-24
        arrival_hour = q.get('arrivalHour')  # 0-24
        
        # Filter theo origin, destination, departure_date, hours
        filtered_flights = []
        for flight in queryset:
            legs = list(flight.legs.order_by('departure_time'))
            if not legs:
                continue
            
            first_leg = legs[0]
            last_leg = legs[-1]
            
            # Check origin
            if origin and str(first_leg.departure_airport_id) != origin:
                continue
            
            # Check destination
            if destination and str(last_leg.arrival_airport_id) != destination:
                continue
            
            # Check departure date
            if departure_date:
                try:
                    date_obj = datetime.strptime(departure_date, '%Y-%m-%d').date()
                    if first_leg.departure_time.date() != date_obj:
                        continue
                except ValueError:
                    pass
            
            # Check departure hour
            if departure_hour:
                dep_hour = first_leg.departure_time.hour
                target_hour = int(departure_hour)
                if dep_hour < target_hour:
                    continue
            
            # Check arrival hour
            if arrival_hour:
                arr_hour = last_leg.arrival_time.hour
                target_hour = int(arrival_hour)
                if arr_hour < target_hour:
                    continue
            
            filtered_flights.append(flight)
        
        # Sort if needed
        sort_by = q.get('sortBy')
        if sort_by == 'price_asc':
            filtered_flights.sort(key=lambda f: f.base_price)
        elif sort_by == 'price_desc':
            filtered_flights.sort(key=lambda f: f.base_price, reverse=True)
        elif sort_by == 'duration_asc':
            filtered_flights.sort(key=lambda f: f.total_duration)
        elif sort_by == 'duration_desc':
            filtered_flights.sort(key=lambda f: f.total_duration, reverse=True)
        
        # Paginate
        page = self.paginate_queryset(filtered_flights)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(filtered_flights, many=True)
        return Response(serializer.data)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        q = self.request.query_params
        
        context["origin"] = q.get("origin")
        context["destination"] = q.get("destination")
        context["departureDate"] = q.get("departureDate")
        context["seatClass"] = q.get("seatClass")
        context["airline"] = q.get("airline")
        context["stops"] = q.get("stops")
        
        return context

class FlightLegViewSet(viewsets.ModelViewSet):
    queryset = FlightLeg.objects.select_related(
        'departure_airport',
        'arrival_airport',
        'flight',
        'flight__airline'
    ).all()
    serializer_class = FlightLegSerializer

class SeatClassPricingViewSet(viewsets.ModelViewSet):
    queryset = SeatClassPricing.objects.select_related('flight').all()
    serializer_class = SeatClassPricingSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        flight_id = self.request.query_params.get('flight_id')
        if flight_id:
            queryset = queryset.filter(flight_id=flight_id)
        return queryset

class FlightBookingDetailViewSet(viewsets.ModelViewSet):
    queryset = FlightBookingDetail.objects.select_related(
        'booking',
        'flight'
    ).all()
    serializer_class = FlightBookingDetailSerializer
