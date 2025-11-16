from django.contrib import admin
from .models import User, Restaurant, Table, Booking, TimeSlot

admin.site.register(User)
admin.site.register(Restaurant)
admin.site.register(Table)
admin.site.register(Booking)
admin.site.register(TimeSlot)
