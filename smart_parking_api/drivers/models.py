from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid
class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    driver_name = models.CharField(max_length=255)
    car_number_plate = models.CharField(max_length=20)
    date_of_arrival = models.DateTimeField(null=True, blank=True)
    date_of_departure = models.DateTimeField(null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    api_key = models.CharField(max_length=255, default="IASMINA", editable=False)

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'In asteptare'),
        ('paid', 'Platit'),
        ('failed', 'Esuat'),
    ]
    payment_status = models.CharField(
        max_length=10, 
        choices=PAYMENT_STATUS_CHOICES,
        default='pending', 
        null=True, blank=True 
    )

    def _str_(self):
        return self.driver_name