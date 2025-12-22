# locations/views.py
from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q
from hotels.models import Hotel
from cities.models import City
from airports.models import Airport


class LocationSuggestionsView(generics.ListAPIView):
    def get(self, request):
        q = request.query_params.get('q', '')
        type_param = request.query_params.get('type', '')

        if not q:
            return Response({"results": []})

        results = []

        if type_param == 'hotel' or type_param == 'homestay':
            # Search hotels/homestays and cities
            hotels = Hotel.objects.filter(
                Q(name__icontains=q) | Q(city__name__icontains=q)
            ).select_related('city').prefetch_related('city__airports')[:10]
            for hotel in hotels:
                city_airport = hotel.city.airports.first() if hotel.city else None
                results.append({
                    "id": hotel.id,
                    "name": hotel.name,
                    "type": "hotel",
                    "subtitle": hotel.city.name if hotel.city else "",
                    "city_id": city_airport.id if city_airport else (hotel.city.id if hotel.city else None),
                })

            cities = City.objects.filter(name__icontains=q).prefetch_related('airports')[:5]
            for city in cities:
                city_airport = city.airports.first()
                results.append({
                    "id": city.id,
                    "name": city.name,
                    "type": "city",
                    "subtitle": "",
                    "city_id": city_airport.id if city_airport else city.id,
                })

        elif type_param == 'flight':
            # Search airports and cities (cities must have airports)
            airports = Airport.objects.filter(
                Q(name__icontains=q) | Q(city__name__icontains=q) | Q(code__icontains=q)
            ).select_related('city')[:10]
            for airport in airports:
                results.append({
                    "id": airport.id,
                    "name": airport.name,
                    "type": "airport",
                    "subtitle": airport.city.name if airport.city else airport.code,
                })

            cities = City.objects.filter(
                name__icontains=q,
                airports__isnull=False
            ).distinct()[:5]
            for city in cities:
                airport = city.airports.first()
                if airport:
                    results.append({
                        "id": airport.id,
                        "name": city.name,
                        "type": "city",
                        "subtitle": "",
                    })

        return Response({"results": results})
