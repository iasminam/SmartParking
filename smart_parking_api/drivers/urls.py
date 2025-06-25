from django.urls import path
from . import views
from .views import create_payment_intent

urlpatterns = [
    path('driver_page/<str:username>/', views.DriverPageView.as_view(), name='driver_page'),  
    path('register/', views.DriverRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('simulate_parking/', views.simulate_parking, name='simulate_parking'),
    path('simulate_departure/', views.simulate_departure, name='simulate_departure'),
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('simulate_car_detection/', views.simulate_car_detection, name='simulate_car_detection'),
    path('check_barrier_open_status/', views.check_barrier_open_status, name='check_barrier_open_status'),
    path('trigger_car_detection/', views.trigger_car_detection, name='trigger_car_detection'),
    path('verify_departure/', views.verify_departure, name='verify_departure'),
    path('confirm-payment/', views.confirm_payment, name='confirm_payment'),
]