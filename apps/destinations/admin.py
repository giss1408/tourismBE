from django.contrib import admin
from .models import Destination

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'category', 'rating', 'price', 'is_featured')
    list_filter = ('category', 'is_featured')
    search_fields = ('name', 'location')
