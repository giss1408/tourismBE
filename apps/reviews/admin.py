from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('destination', 'user', 'rating', 'is_visible', 'created_at')
    list_filter = ('is_visible', 'rating')
    list_editable = ('is_visible',)
    search_fields = ('destination__name', 'user__email', 'comment')
