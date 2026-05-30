from django.contrib import admin

from .models import (
    DriverCashout,
    DriverWalletBalance,
    DriverWalletTransaction,
    Order,
    OrderDriver,
    RideType,
)


class OrderDriverInline(admin.TabularInline):
    model = OrderDriver
    extra = 0
    raw_id_fields = ('driver',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_code', 'user', 'status', 'order_type', 'payment_type', 'created_at')
    list_filter = ('status', 'order_type', 'payment_type')
    search_fields = ('order_code', 'user__email', 'id')
    raw_id_fields = ('user', 'saved_card')
    inlines = (OrderDriverInline,)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RideType)
class RideTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'name_large', 'is_active', 'base_price', 'price_per_km')
    list_filter = ('is_active', 'is_premium', 'is_ev')


@admin.register(DriverCashout)
class DriverCashoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver', 'amount', 'status', 'payment_type', 'created_at')
    list_filter = ('status', 'payment_type')
    search_fields = ('driver__email',)
    raw_id_fields = ('driver',)


@admin.register(DriverWalletBalance)
class DriverWalletBalanceAdmin(admin.ModelAdmin):
    list_display = ('driver', 'available_card', 'available_hola_wallet_cash', 'lifetime_card')
    search_fields = ('driver__email',)
    raw_id_fields = ('driver',)


@admin.register(DriverWalletTransaction)
class DriverWalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver', 'kind', 'amount', 'payment_type', 'order', 'created_at')
    list_filter = ('kind', 'payment_type')
    search_fields = ('driver__email',)
    raw_id_fields = ('driver', 'order', 'cashout')
