# payments/constants/payment_method.py
from django.db import models

class PaymentMethod(models.IntegerChoices):
    ONLINE = 1, 'Online Payment'
    CASH = 2, 'Pay at Hotel / On Delivery'
