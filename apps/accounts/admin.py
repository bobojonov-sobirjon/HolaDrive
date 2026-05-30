from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, DriverUser, RiderUser, UserDeviceToken


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    
    def get_groups_name(self, obj):
        return [group.name for group in obj.groups.all()]
    
    list_display = (
        'email', 'username', 'first_name', 'last_name', 'phone_number', 'is_verified', 'is_staff', 'is_active', 'created_at', 'get_groups_name'
    )
    list_filter = ('is_staff', 'is_active', 'is_verified', 'is_superuser', 'groups')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'firebase_uid')
    ordering = ('-created_at',)
    readonly_fields = ('id_identification', 'created_at', 'updated_at', 'last_login')

    fieldsets = UserAdmin.fieldsets + (
        (
            'Hola Drive profile',
            {
                'fields': (
                    'phone_number',
                    'date_of_birth',
                    'gender',
                    'avatar',
                    'address',
                    'tax_number',
                    'firebase_uid',
                    'id_identification',
                    'is_verified',
                    'is_online',
                    'stripe_customer_id',
                    'stripe_connect_account_id',
                ),
            },
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets


@admin.register(RiderUser)
class RiderUserAdmin(CustomUserAdmin):
    pass


@admin.register(DriverUser)
class DriverUserAdmin(CustomUserAdmin):
    pass


@admin.register(UserDeviceToken)
class UserDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'mobile', 'created_at')
    search_fields = ('user__email', 'token')
    raw_id_fields = ('user',)
