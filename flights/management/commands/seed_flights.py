from django.core.management.base import BaseCommand
from flights.models import Flight
from airports.models import Airport
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Seed sample flights data'

    def handle(self, *args, **kwargs):
        # Get airports
        try:
            sgn = Airport.objects.get(name__icontains='Tân Sơn Nhất')
            han = Airport.objects.get(name__icontains='Nội Bài')
            dad = Airport.objects.get(name__icontains='Đà Nẵng')
            bkk = Airport.objects.get(name__icontains='Suvarnabhumi')
            dmk = Airport.objects.get(name__icontains='Don Mueang')
            sin = Airport.objects.get(name__icontains='Changi')
        except Airport.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    '❌ Error: Airports not found. Please run: python manage.py seed_airports first'
                )
            )
            return

        # Airlines
        airlines = ['Vietnam Airlines', 'VietJet Air', 'Thai Airways', 'Singapore Airlines']
        
        # Routes with typical flight times (in minutes)
        routes = [
            # Vietnam domestic
            (sgn, han, 120, 'VN'),  # SGN -> HAN
            (han, sgn, 120, 'VN'),  # HAN -> SGN
            (sgn, dad, 75, 'VN'),   # SGN -> DAD
            (dad, sgn, 75, 'VN'),   # DAD -> SGN
            (han, dad, 90, 'VN'),   # HAN -> DAD
            (dad, han, 90, 'VN'),   # DAD -> HAN
            
            # International
            (sgn, bkk, 90, 'VN'),   # SGN -> BKK
            (bkk, sgn, 90, 'VN'),   # BKK -> SGN
            (han, bkk, 135, 'VN'),  # HAN -> BKK
            (bkk, han, 135, 'VN'),  # BKK -> HAN
            (sgn, sin, 120, 'VN'),  # SGN -> SIN
            (sin, sgn, 120, 'VN'),  # SIN -> SGN
            (han, sin, 240, 'VN'),  # HAN -> SIN
            (sin, han, 240, 'VN'),  # SIN -> HAN
        ]

        # Generate flights for next 30 days
        today = datetime.now().date()
        created_count = 0

        for day_offset in range(0, 30):
            flight_date = today + timedelta(days=day_offset)
            
            for origin, destination, duration, flight_prefix in routes:
                # Generate 3-5 flights per day for each route
                num_flights = random.randint(3, 5)
                
                for flight_num in range(num_flights):
                    airline = random.choice(airlines)
                    
                    # Random departure time
                    hour = random.randint(6, 22)
                    minute = random.choice([0, 15, 30, 45])
                    
                    departure_datetime = datetime.combine(
                        flight_date,
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    arrival_datetime = departure_datetime + timedelta(minutes=duration)
                    
                    # Price based on route and time
                    base_price = {
                        'VN': 1500000,  # Domestic Vietnam
                    }.get(flight_prefix, 2500000)  # International
                    
                    # Peak hours (morning & evening) are more expensive
                    if hour in [7, 8, 17, 18, 19]:
                        price_multiplier = random.uniform(1.3, 1.5)
                    else:
                        price_multiplier = random.uniform(0.8, 1.2)
                    
                    price = int(base_price * price_multiplier)
                    
                    # Flight number
                    flight_number = f"{flight_prefix}{random.randint(100, 999)}"
                    
                    # Create flight
                    flight, created = Flight.objects.get_or_create(
                        flight_number=flight_number,
                        departure_datetime=departure_datetime,
                        defaults={
                            'origin': origin,
                            'destination': destination,
                            'airline': airline,
                            'arrival_datetime': arrival_datetime,
                            'duration_minutes': duration,
                            'price': price,
                            'seat_capacity': random.choice([150, 180, 200, 250]),
                            'available_seats': random.randint(10, 100)
                        }
                    )
                    
                    if created:
                        created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Done! Created {created_count} flights for next 30 days.'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Routes: {len(routes)} routes with 3-5 flights per day each.'
            )
        )
