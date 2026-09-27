from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('booking__reference', 'stripe_payment_intent_id')
    readonly_fields = ('booking', 'stripe_payment_intent_id', 'amount', 'currency',
                       'status', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False  # Payments come from Stripe only.
