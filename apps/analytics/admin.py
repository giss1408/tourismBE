from django.contrib import admin
from .models import AnalyticsEvent, UserProperties

@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'timestamp', 'received_at')
    list_filter = ('name',)
    search_fields = ('name', 'user__email')

admin.site.register(UserProperties)
