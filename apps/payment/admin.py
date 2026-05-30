from django.contrib import admin

from .models import SavedCard


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'holder_role', 'brand', 'last4', 'is_default', 'is_active')
    list_filter = ('holder_role', 'is_default', 'is_active')
    search_fields = ('user__email', 'stripe_payment_method_id')
    raw_id_fields = ('user',)
