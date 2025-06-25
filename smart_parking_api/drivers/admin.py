from django.contrib import admin
from .models import Driver

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'driver_name', 'car_number_plate', 'date_of_arrival', 'date_of_departure', 'paid_amount')
    readonly_fields = ('api_key',) 