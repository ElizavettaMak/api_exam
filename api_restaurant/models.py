from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

# Пользователь
class User(AbstractUser):
    pass

# Ресторан
class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()

    def __str__(self):
        return self.name

# Столик
class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=40)
    capacity = models.PositiveIntegerField()

    class Meta:
        unique_together = ['restaurant', 'table_number']

    def __str__(self):
        return f"Table {self.table_number} at {self.restaurant.name}"

# Слот времени
class TimeSlot(models.Model):
    STATUS_CHOICES = [
        ('reserved', 'Reserved'),
        ('free', 'Free'),
    ]
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='time_slots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='free')

    def __str__(self):
        return f"{self.table} - {self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%H:%M')} ({self.status})"

    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("End_time должно быть после start_time")

            # Проверка на пересечение с существующими забронированными слотами
            if self.status == 'free':
                overlapping = TimeSlot.objects.filter(
                    table=self.table,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time,
                    status='reserved'
                ).exclude(pk=self.pk).exists()

                if overlapping:
                    raise ValidationError("Время недоступно для бронирования")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# Бронирование
class Booking(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='bookings')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='bookings')
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='bookings')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Бронирование для {self.user.username} - {self.table}"

    class Meta:
        unique_together = ['timeslot']  # Один слот - одно бронирование

    def clean(self):
        if self.timeslot.status != 'free':
            raise ValidationError("Это время уже забронировано")

    def save(self, *args, **kwargs):
        if not self.pk:  # Только при создании
            self.timeslot.status = 'reserved'
            self.timeslot.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Освобождаем слот при удалении брони
        self.timeslot.status = 'free'
        self.timeslot.save()
        super().delete(*args, **kwargs)