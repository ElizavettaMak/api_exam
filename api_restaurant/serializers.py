from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Restaurant, Table, Booking, TimeSlot


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = '__all__'


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = '__all__'


class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = '__all__'

    def validate(self, data):  # Переопределение валидации для проверки доступности слота времени
        id = data['id']
        check_in = data['check_in_time']
        check_out = data['check_out_time']

        overlaps = Booking.objects.filter(
            id=id,
            check_in_time__lt=check_out,
            check_out_date__gt=check_in,
        ).exists()

        if overlaps:
            raise serializers.ValidationError("Это время недоступно для бронирования")

        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('user', 'created_at')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user