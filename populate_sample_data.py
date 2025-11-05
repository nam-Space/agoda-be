"""
Script to populate sample data for hotel search suggestions
Run: python manage.py shell < populate_sample_data.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoda_be.settings')
django.setup()

from hotels.models import Hotel
from cities.models import City, Country

print("🚀 Starting to populate sample data...")

# 1. Check and create Vietnam country
vietnam, created = Country.objects.get_or_create(
    name='Vietnam',
    defaults={'code': 'VN'}
)
if created:
    print(f"✅ Created country: Vietnam")
else:
    print(f"ℹ️  Country Vietnam already exists")

# 2. Create Vietnam cities with hotels
vietnam_cities_data = [
    {'name': 'Hồ Chí Minh', 'hotel_count': 0},
    {'name': 'Hà Nội', 'hotel_count': 0},
    {'name': 'Đà Nẵng', 'hotel_count': 0},
    {'name': 'Nha Trang', 'hotel_count': 0},
    {'name': 'Vũng Tàu', 'hotel_count': 0},
    {'name': 'Đà Lạt', 'hotel_count': 0},
]

created_cities = []
for city_data in vietnam_cities_data:
    city, created = City.objects.get_or_create(
        name=city_data['name'],
        country=vietnam
    )
    if created:
        print(f"✅ Created city: {city.name}")
    else:
        print(f"ℹ️  City {city.name} already exists")
    created_cities.append(city)

# 3. Create sample hotels if they don't exist
hotel_count = Hotel.objects.count()
print(f"ℹ️  Current hotels in database: {hotel_count}")

if hotel_count < 10:
    print("📝 Creating sample hotels...")
    
    # Sample hotels for Hồ Chí Minh
    hcm = created_cities[0]
    hotels_hcm = [
        {
            'name': 'The Ascott Limited Ho Chi Minh',
            'description': 'Tầm hướng kỳ nghỉ theo cách của quý khách. Khách sạn 5 sao cao cấp',
            'avg_star': 4.5,
            'review_count': 120,
            'min_price': 2000000,
            'original_price': 2500000,
            'discount_percentage': 20,
            'city': hcm
        },
        {
            'name': 'InterContinental Saigon',
            'description': 'Khách sạn sang trọng tại trung tâm thành phố',
            'avg_star': 4.8,
            'review_count': 250,
            'min_price': 3000000,
            'original_price': 3600000,
            'discount_percentage': 17,
            'city': hcm
        },
        {
            'name': 'Hilton Saigon',
            'description': 'Khách sạn quốc tế với dịch vụ đẳng cấp',
            'avg_star': 4.6,
            'review_count': 180,
            'min_price': 2500000,
            'original_price': 3000000,
            'discount_percentage': 17,
            'city': hcm
        },
    ]
    
    # Sample hotels for Hà Nội
    hanoi = created_cities[1]
    hotels_hanoi = [
        {
            'name': 'Sofitel Legend Metropole Hanoi',
            'description': 'Khách sạn lịch sử sang trọng',
            'avg_star': 4.7,
            'review_count': 200,
            'min_price': 4000000,
            'original_price': 5000000,
            'discount_percentage': 20,
            'city': hanoi
        },
        {
            'name': 'Hanoi Luxury Hotel',
            'description': 'Khách sạn cao cấp giữa lòng phố cổ',
            'avg_star': 4.3,
            'review_count': 95,
            'min_price': 1500000,
            'original_price': 1800000,
            'discount_percentage': 17,
            'city': hanoi
        },
    ]
    
    # Sample hotels for Đà Nẵng
    danang = created_cities[2]
    hotels_danang = [
        {
            'name': 'Da Nang Seaside Resort',
            'description': 'Resort bên bãi biển tuyệt đẹp',
            'avg_star': 4.5,
            'review_count': 150,
            'min_price': 2200000,
            'original_price': 2750000,
            'discount_percentage': 20,
            'city': danang
        },
    ]
    
    all_hotels = hotels_hcm + hotels_hanoi + hotels_danang
    
    for hotel_data in all_hotels:
        hotel, created = Hotel.objects.get_or_create(
            name=hotel_data['name'],
            defaults=hotel_data
        )
        if created:
            print(f"✅ Created hotel: {hotel.name}")
        else:
            print(f"ℹ️  Hotel {hotel.name} already exists")

# 4. Create international cities (optional)
print("\n📍 Creating international cities...")
singapore, _ = Country.objects.get_or_create(name='Singapore', defaults={'code': 'SG'})
thailand, _ = Country.objects.get_or_create(name='Thailand', defaults={'code': 'TH'})
korea, _ = Country.objects.get_or_create(name='South Korea', defaults={'code': 'KR'})

international_cities = [
    {'name': 'Singapore', 'country': singapore},
    {'name': 'Bangkok', 'country': thailand},
    {'name': 'Seoul', 'country': korea},
]

for city_data in international_cities:
    city, created = City.objects.get_or_create(
        name=city_data['name'],
        country=city_data['country']
    )
    if created:
        print(f"✅ Created international city: {city.name}")

# 5. Summary
print("\n" + "="*50)
print("📊 SUMMARY:")
print("="*50)
print(f"✅ Total countries: {Country.objects.count()}")
print(f"✅ Total cities: {City.objects.count()}")
print(f"   - Vietnam cities: {City.objects.filter(country=vietnam).count()}")
print(f"   - International cities: {City.objects.exclude(country=vietnam).count()}")
print(f"✅ Total hotels: {Hotel.objects.count()}")
print(f"   - Hotels with discount: {Hotel.objects.filter(discount_percentage__gt=0).count()}")
print("\n✨ Sample data population complete!")
print("\n🧪 Test the API:")
print("   curl http://localhost:8000/api/hotels/search-suggestions/")
