from django.db import models


class CarBookingStatus(models.IntegerChoices):
    STARTING = 0, "Starting"
    PICKED = 1, "Picked"
    MOVING = 2, "Moving"
    ARRIVED = 3, "Arrived"
