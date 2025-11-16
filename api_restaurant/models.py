from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model


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

    def __str__(self):
        return f"Table №{self.table_number}"

# Слот времени
class TimeSlot(models.Model):
    STATUS_CHOICES = [
        ('reserved', 'Reserved'),
        ('free', 'Free'),
    ]
    check_in_time = models.DateTimeField()
    check_out_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='free')

    def __str__(self):
        return f"Status: {self.status}"


# Бронирование
class Booking(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='bookings')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='bookings')
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='bookings')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.user.username} - Table {self.table.table_number}"