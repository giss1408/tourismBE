from django.contrib import admin

from .models import DeviceToken


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'last_seen_at')
    search_fields = ('user__email',)
    readonly_fields = ('token',)
