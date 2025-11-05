from django.core.management.base import BaseCommand
from airports.models import Airport
from cities.models import City
from countries.models import Country


class Command(BaseCommand):
    help = 'Seed sample airports data'

    def handle(self, *args, **kwargs):
        # Create or get countries
        vietnam, _ = Country.objects.get_or_create(
            name='Việt Nam',
            defaults={'code': 'VN'}
        )
        thailand, _ = Country.objects.get_or_create(
            name='Thái Lan', 
            defaults={'code': 'TH'}
        )
        singapore, _ = Country.objects.get_or_create(
            name='Singapore',
            defaults={'code': 'SG'}
        )

        # Create or get cities
        hcm, _ = City.objects.get_or_create(
            name='Hồ Chí Minh',
            defaults={'country': vietnam}
        )
        hanoi, _ = City.objects.get_or_create(
            name='Hà Nội',
            defaults={'country': vietnam}
        )
        danang, _ = City.objects.get_or_create(
            name='Đà Nẵng',
            defaults={'country': vietnam}
        )
        bangkok, _ = City.objects.get_or_create(
            name='Bangkok',
            defaults={'country': thailand}
        )
        singapore_city, _ = City.objects.get_or_create(
            name='Singapore',
            defaults={'country': singapore}
        )

        # Sample airports
        airports_data = [
            # Vietnam - Ho Chi Minh
            {
                'name': 'Sân bay Quốc tế Tân Sơn Nhất (SGN)',
                'city': hcm,
                'description': 'Sân bay quốc tế lớn nhất Việt Nam',
                'location': 'Tân Bình, Hồ Chí Minh',
                'lat': 10.8188,
                'lng': 106.6519
            },
            # Vietnam - Hanoi
            {
                'name': 'Sân bay Quốc tế Nội Bài (HAN)',
                'city': hanoi,
                'description': 'Sân bay quốc tế của thủ đô Hà Nội',
                'location': 'Sóc Sơn, Hà Nội',
                'lat': 21.2212,
                'lng': 105.8072
            },
            # Vietnam - Da Nang
            {
                'name': 'Sân bay Quốc tế Đà Nẵng (DAD)',
                'city': danang,
                'description': 'Sân bay quốc tế miền Trung',
                'location': 'Hải Châu, Đà Nẵng',
                'lat': 16.0544,
                'lng': 108.2022
            },
            # Thailand - Bangkok
            {
                'name': 'Sân bay Suvarnabhumi (BKK)',
                'city': bangkok,
                'description': 'Sân bay quốc tế chính của Bangkok',
                'location': 'Bangkok, Thailand',
                'lat': 13.6900,
                'lng': 100.7501
            },
            {
                'name': 'Sân bay Don Mueang (DMK)',
                'city': bangkok,
                'description': 'Sân bay quốc tế thứ hai của Bangkok',
                'location': 'Bangkok, Thailand',
                'lat': 13.9126,
                'lng': 100.6067
            },
            # Singapore
            {
                'name': 'Sân bay Changi (SIN)',
                'city': singapore_city,
                'description': 'Sân bay quốc tế Changi Singapore',
                'location': 'Changi, Singapore',
                'lat': 1.3644,
                'lng': 103.9915
            },
        ]

        # Create airports
        created_count = 0
        for airport_data in airports_data:
            airport, created = Airport.objects.get_or_create(
                name=airport_data['name'],
                defaults={
                    'city': airport_data['city'],
                    'description': airport_data['description'],
                    'location': airport_data['location'],
                    'lat': airport_data['lat'],
                    'lng': airport_data['lng']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {airport.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'- Already exists: {airport.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Done! Created {created_count} new airports.'
            )
        )
