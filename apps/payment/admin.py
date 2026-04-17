from django.contrib import admin

from .models import SavedCard


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'holder_role',
        'brand',
        'last4',
        'exp_month',
        'exp_year',
        'is_default',
        'is_active',
        'created_at',
    )
    list_filter = ('holder_role', 'is_default', 'is_active', 'brand', 'funding')
    search_fields = (
        'user__email',
        'user__username',
        'user__first_name',
        'user__last_name',
        'stripe_payment_method_id',
        'stripe_customer_id',
        'last4',
        'nickname',
    )
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)
    fieldsets = (
        (None, {'fields': ('user', 'holder_role', 'nickname', 'is_default', 'is_active')}),
        (
            'Stripe',
            {
                'fields': (
                    'stripe_customer_id',
                    'stripe_payment_method_id',
                ),
            },
        ),
        (
            'Display (from Stripe)',
            {
                'fields': (
                    'brand',
                    'last4',
                    'exp_month',
                    'exp_year',
                    'funding',
                ),
            },
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
