from django.contrib import admin

from .models import Guide


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ('name', 'whatsapp', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'bio')
    filter_horizontal = ('destinations',)
