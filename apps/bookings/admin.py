from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'destination_name', 'status', 'total_price', 'booking_date')
    list_filter = ('status',)
    search_fields = ('reference', 'destination_name', 'user__email')
