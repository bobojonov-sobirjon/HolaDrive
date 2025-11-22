from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from .models import CustomUser, VerificationCode, PasswordResetToken, UserPreferences, InvitationGenerate, InvitationUsers, PinVerificationForUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
        ('Verification', {'fields': ('is_verified',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login')


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'email', 'phone_number', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('code', 'user__email', 'user__phone_number', 'email', 'phone_number')
    readonly_fields = ('code', 'created_at', 'expires_at')
    ordering = ('-created_at',)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('token', 'user__email')
    readonly_fields = ('token', 'created_at', 'expires_at')
    ordering = ('-created_at',)


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'chatting_preference', 'temperature_preference', 'music_preference', 'volume_level', 'created_at', 'updated_at')
    list_filter = ('chatting_preference', 'temperature_preference', 'music_preference', 'volume_level', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)


@admin.register(InvitationGenerate)
class InvitationGenerateAdmin(admin.ModelAdmin):
    list_display = ('user', 'invite_code', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('invite_code', 'user__email', 'user__username')
    readonly_fields = ('invite_code', 'created_at')
    ordering = ('-created_at',)


@admin.register(InvitationUsers)
class InvitationUsersAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('sender__email', 'sender__username', 'receiver__email', 'receiver__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(PinVerificationForUser)
class PinVerificationForUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'pin', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__username', 'pin')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)


admin.site.unregister(Site)

admin.site.site_header = 'Holo Drive Admin'
admin.site.site_title = 'Holo Drive Admin'
admin.site.index_title = 'Holo Drive Admin'