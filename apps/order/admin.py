from django.contrib import admin
from .models import (
    Order, OrderItem, OrderPreferences, AdditionalPassenger, OrderDriver, 
    CancelOrder, RideType, SurgePricing, OrderPaymentSplit, PromoCode, OrderPromoCode
)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_code', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_code', 'user__email', 'user__username')
    readonly_fields = ('order_code', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'ride_type', 'address_from', 'address_to', 'original_price', 'adjusted_price', 'calculated_price', 'created_at')
    list_filter = ('is_price_adjusted', 'ride_type', 'created_at')
    search_fields = ('order__order_code', 'address_from', 'address_to')
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'original_price', 
        'calculated_price', 
        'min_price', 
        'max_price', 
        'price_adjustment_percentage', 
        'is_price_adjusted',
        'distance_km'  # Also readonly since it's auto-calculated
    )
    ordering = ('-created_at',)
    fieldsets = (
        ('Order Information', {
            'fields': ('order', 'ride_type')
        }),
        ('Location Information', {
            'fields': ('address_from', 'address_to', 'latitude_from', 'longitude_from', 'latitude_to', 'longitude_to'),
            'description': 'Enter addresses and coordinates. Distance will be calculated automatically if coordinates are provided.'
        }),
        ('Distance and Time', {
            'fields': ('distance_km', 'estimated_time'),
            'description': 'Distance is calculated automatically from coordinates. You can also enter it manually if needed.'
        }),
        ('Pricing Information', {
            'fields': (
                'original_price',  # Auto-calculated (readonly)
                'min_price',  # Auto-calculated (readonly)
                'max_price',  # Auto-calculated (readonly)
                'adjusted_price',  # User can edit (for manage price)
                'calculated_price',  # Auto-updated (readonly)
                'price_adjustment_percentage',  # Auto-calculated (readonly)
                'is_price_adjusted'  # Auto-updated (readonly)
            ),
            'description': 'Original price, min/max prices are calculated automatically. You can adjust the price manually using "Adjusted Price" field. Other fields are read-only and calculated automatically.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderPreferences)
class OrderPreferencesAdmin(admin.ModelAdmin):
    list_display = ('order', 'chatting_preference', 'temperature_preference', 'music_preference', 'gender_preference', 'created_at')
    list_filter = ('chatting_preference', 'temperature_preference', 'music_preference', 'gender_preference', 'created_at')
    search_fields = ('order__order_code',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Order Information', {
            'fields': ('order',)
        }),
        ('Rider Preferences', {
            'fields': ('chatting_preference', 'temperature_preference', 'music_preference', 'volume_level', 'pet_preference', 'kids_chair_preference', 'wheelchair_preference')
        }),
        ('Driver Preferences', {
            'fields': ('gender_preference', 'favorite_driver_preference')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AdditionalPassenger)
class AdditionalPassengerAdmin(admin.ModelAdmin):
    list_display = ('order', 'full_name', 'phone_number', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__order_code', 'full_name', 'phone_number', 'email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(OrderDriver)
class OrderDriverAdmin(admin.ModelAdmin):
    list_display = ('order', 'driver', 'pin_code', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__order_code', 'driver__email', 'driver__username', 'pin_code')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(CancelOrder)
class CancelOrderAdmin(admin.ModelAdmin):
    list_display = ('order', 'driver', 'reason', 'created_at')
    list_filter = ('reason', 'created_at')
    search_fields = ('order__order_code', 'other_reason')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(RideType)
class RideTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_large', 'base_price', 'price_per_km', 'capacity', 'is_premium', 'is_ev', 'is_active', 'created_at')
    list_filter = ('is_premium', 'is_ev', 'is_active', 'created_at')
    search_fields = ('name', 'name_large')
    readonly_fields = ('created_at',)
    ordering = ('name',)


@admin.register(SurgePricing)
class SurgePricingAdmin(admin.ModelAdmin):
    list_display = ('name', 'multiplier', 'zone_name', 'is_active', 'priority', 'created_at', 'updated_at')
    list_filter = ('is_active', 'priority', 'created_at')
    search_fields = ('name', 'zone_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-priority', 'name')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'multiplier', 'is_active', 'priority')
        }),
        ('Time Factors', {
            'fields': ('start_time', 'end_time', 'days_of_week'),
            'classes': ('collapse',)
        }),
        ('Zone Factors', {
            'fields': ('zone_name', 'latitude', 'longitude', 'radius_km'),
            'classes': ('collapse',)
        }),
        ('Driver Count Factors', {
            'fields': ('min_available_drivers', 'max_available_drivers'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderPaymentSplit)
class OrderPaymentSplitAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'amount', 'split_type', 'payment_status', 'invitation_accepted', 'created_at')
    list_filter = ('payment_status', 'split_type', 'invitation_accepted', 'created_at')
    search_fields = ('order__order_code', 'user__email', 'user__username', 'invitation_token')
    readonly_fields = ('created_at', 'updated_at', 'invitation_token', 'payment_confirmed_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Order and User Information', {
            'fields': ('order', 'user')
        }),
        ('Split Information', {
            'fields': ('split_type', 'amount', 'percentage')
        }),
        ('Payment Status', {
            'fields': ('payment_status', 'payment_confirmed_at', 'payment_failed_reason')
        }),
        ('Invitation Information', {
            'fields': ('invitation_token', 'invited_at', 'invitation_accepted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'user', 'is_active', 'current_uses', 'max_uses', 'valid_from', 'valid_until', 'created_at')
    list_filter = ('discount_type', 'is_active', 'created_at', 'valid_from', 'valid_until')
    search_fields = ('code', 'description', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'current_uses')
    ordering = ('-created_at',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount Information', {
            'fields': ('discount_type', 'discount_value', 'max_discount_amount')
        }),
        ('User Assignment', {
            'fields': ('user',),
            'description': 'If user is set, this promo code is only for this user. If empty, it\'s general.'
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'current_uses', 'min_order_amount')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderPromoCode)
class OrderPromoCodeAdmin(admin.ModelAdmin):
    list_display = ('order', 'promo_code', 'discount_amount', 'order_amount_before_discount', 'order_amount_after_discount', 'applied_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__order_code', 'promo_code__code', 'applied_by__email', 'applied_by__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    fieldsets = (
        ('Order and Promo Code', {
            'fields': ('order', 'promo_code', 'applied_by')
        }),
        ('Discount Information', {
            'fields': (
                'order_amount_before_discount',
                'discount_amount',
                'order_amount_after_discount'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
