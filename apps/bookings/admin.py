from django.contrib import admin

from .models import Booking
from .services import cancel_booking, confirm_booking


@admin.action(description='Confirm selected bookings (emails the travellers)')
def confirm_selected(modeladmin, request, queryset):
    confirmed = sum(confirm_booking(booking) for booking in queryset)
    modeladmin.message_user(request, f'{confirmed} booking(s) confirmed.')


@admin.action(description='Cancel selected bookings (refunds within the free window)')
def cancel_selected(modeladmin, request, queryset):
    for booking in queryset:
        cancel_booking(booking)
    modeladmin.message_user(request, f'{queryset.count()} booking(s) cancelled.')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    actions = [confirm_selected, cancel_selected]
    readonly_fields = ('status', 'total_price', 'confirmed_at', 'cancelled_at')
    list_display = ('reference', 'user', 'destination_name', 'status', 'total_price', 'booking_date')
    list_filter = ('status',)
    search_fields = ('reference', 'destination_name', 'user__email')
