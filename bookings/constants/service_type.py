from django.db import models


class ServiceType(models.IntegerChoices):
    HOTEL = 1, "Hotel"
    CAR = 2, "Car"
    FLIGHT = (
        3,
        "Flight",
    )
    ACTIVITY = (4, "Activity")
    HANDBOOK = (5, "Handbook")
