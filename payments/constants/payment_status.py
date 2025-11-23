from django.db import models

class PaymentStatus(models.IntegerChoices):
    PENDING = 1, 'Pending'
    SUCCESS = 2, 'Success'
    FAILED = 3, 'Failed'
    CANCELLED = 4, 'Cancelled'
    UNPAID = 5, 'Unpaid'         
    PAID = 6, 'Paid'
    REFUNDED = 7, 'Refunded' 