from django.db import models
from bookings.models import Booking
from airports.models import Airport

class SeatClass(models.TextChoices):
    ECONOMY = 'Economy', 'Economy'
    BUSINESS = 'Business', 'Business'
    FIRST = 'First', 'First'

class Flight(models.Model):
    flight_number = models.CharField(max_length=20, unique=True)
    airline = models.CharField(max_length=100)
    origin = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='departing_flights')
    destination = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='arriving_flights')
    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seat_capacity = models.IntegerField()

class FlightBookingDetail(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='flight_detail')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)
    seat_class = models.CharField(max_length=20, choices=SeatClass.choices)
    num_passengers = models.IntegerField()
    def __str__(self):
        return f"FlightBooking for {self.booking.booking_code}"