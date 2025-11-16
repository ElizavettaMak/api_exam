from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Restaurant, Table, Booking, TimeSlot

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = '__all__'


class TableSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)

    class Meta:
        model = Table
        fields = '__all__'


class TimeSlotSerializer(serializers.ModelSerializer):
    table_info = serializers.CharField(source='table.table_number', read_only=True)
    restaurant_name = serializers.CharField(source='table.restaurant.name', read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = TimeSlot
        fields = '__all__'
        read_only_fields = ('status',)

    def validate(self, data):
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        table = data.get('table')
        instance = getattr(self, 'instance', None)

        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError({
                    "end_time": "End_time должно быть после start_time"
                })

            duration = end_time - start_time
            if duration.total_seconds() < 3600:
                raise serializers.ValidationError({
                    "end_time": "Время должно быть минимум 1 час"
                })

        # Проверка на пересечение с существующими ЗАБРОНИРОВАННЫМИ слотами
        if table and start_time and end_time:
            # Создаем queryset для поиска пересечений
            overlapping_query = TimeSlot.objects.filter(
                table=table,
                start_time__lt=end_time,
                end_time__gt=start_time,
                status='reserved'  # Проверяем только занятые слоты
            )

            # Исключаем текущий instance при обновлении
            if instance and instance.pk:
                overlapping_query = overlapping_query.exclude(pk=instance.pk)

            if overlapping_query.exists():
                raise serializers.ValidationError({
                    "table": "This time slot overlaps with an existing reservation"
                })

        return data

class BookingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    table_info = serializers.CharField(source='table.table_number', read_only=True)
    restaurant_name = serializers.CharField(source='table.restaurant.name', read_only=True)
    time_slot_display = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

    def get_time_slot_display(self, obj):
        return f"{obj.time_slot.start_time.strftime('%Y-%m-%d %H:%M')} - {obj.time_slot.end_time.strftime('%H:%M')}"

    def validate(self, data):
        request = self.context.get('request')
        time_slot = data.get('time_slot')

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Пользователь должен быть авторизован")

        if time_slot and time_slot.status != 'free':
            raise serializers.ValidationError({
                "time_slot": "Данное время недоступно"
            })

        # Проверка, что пользователь не имеет брони в это же время
        user_overlapping = Booking.objects.filter(
            user=request.user,
            time_slot__start_time__lt=time_slot.end_time,
            time_slot__end_time__gt=time_slot.start_time
        ).exists()

        if user_overlapping:
            raise serializers.ValidationError({
                "time_slot": "У вас уже есть бронирование на это время"
            })

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)

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