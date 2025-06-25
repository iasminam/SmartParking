from rest_framework import serializers, permissions 
from .models import Driver
from django.contrib.auth.models import User

class DriverSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True) 
    password = serializers.CharField(write_only=True)
    class Meta:
        model = Driver
        fields = (
            'username', 'password', 'driver_name', 'car_number_plate',
            'date_of_arrival', 'date_of_departure', 'paid_amount', 'api_key'
        )
        read_only_fields = ('api_key', 'date_of_arrival', 'date_of_departure', 'paid_amount') # Câmpuri care nu sunt setate de client la creare/update

    def create(self, validated_data):
        # Extragem username și password direct din validated_data, deoarece vin la nivelul rădăcină.
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        user = User.objects.create_user(username=username, password=password)

        # Acum creează obiectul Driver, asociindu-l cu userul creat.
        driver = Driver.objects.create(user=user, **validated_data)
        return driver

    def update(self, instance, validated_data):
        # Extrage username și password 
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)

        if username:
            instance.user.username = username
        if password:
            instance.user.set_password(password)
        instance.user.save()

        # Actualizează câmpurile Driver
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
class UserSerializer(serializers.ModelSerializer):
     class Meta:
         model = User
         fields = ('username', 'password')