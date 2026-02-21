from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from django.utils.html import format_html, format_html_join
import mimetypes
from django.db import models
from django import forms
from .models import (
    CustomUser, RiderUser, DriverUser,
    VerificationCode, PasswordResetToken, UserPreferences,
    DriverPreferences, VehicleDetails, VehicleImages,
    DriverIdentification, DriverIdentificationItems, DriverIdentificationFAQ,
    DriverIdentificationUploadDocument,
    DriverVerification, UserDeviceToken,
    InvitationGenerate, InvitationUsers, PinVerificationForUser,
    LegalPage, DriverAgreement
)
try:
    from apps.order.models import RideType
except ImportError:
    RideType = None


class UserPreferencesInline(admin.TabularInline):
    """
    Inline admin for UserPreferences
    """
    model = UserPreferences
    extra = 1
    fields = ('chatting_preference', 'temperature_preference', 'music_preference', 'volume_level')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 200px;'}),
        },
    }


class InvitationUsersInline(admin.TabularInline):
    """
    Inline admin for InvitationUsers (sent invitations)
    """
    model = InvitationUsers
    fk_name = 'sender'
    extra = 0
    fields = ('receiver', 'is_active', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    can_delete = True


class PinVerificationForDriverInline(admin.TabularInline):
    """
    Inline admin for PinVerificationForUser
    """
    model = PinVerificationForUser
    extra = 0
    max_num = 1
    fields = ('pin', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False
    verbose_name = 'PIN Verification For Driver'
    

class PinVerificationForRiderInline(admin.TabularInline):
    """
    Inline admin for PinVerificationForUser
    """
    model = PinVerificationForUser
    extra = 0
    max_num = 1
    fields = ('pin', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False
    verbose_name = 'PIN Verification For Rider'


class DriverPreferencesInline(admin.TabularInline):
    """
    Inline admin for DriverPreferences
    """
    model = DriverPreferences
    extra = 0
    max_num = 1
    fields = ('trip_type_preference', 'maximum_pickup_distance', 'preferred_working_hours', 'notification_intensity')
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False
    
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 200px;'}),
        },
    }


class UserDeviceTokenInline(admin.TabularInline):
    """
    Inline admin for UserDeviceToken (push notification tokens)
    """
    model = UserDeviceToken
    extra = 0
    fields = ('mobile', 'token', 'updated_at')
    readonly_fields = ('updated_at',)
    ordering = ('-updated_at',)


class VehicleImagesInline(admin.TabularInline):
    """
    Inline admin for VehicleImages
    """
    model = VehicleImages
    extra = 1
    fields = ('image', 'created_at')
    readonly_fields = ('created_at',)


class VehicleDetailsInline(admin.StackedInline):
    """
    Inline admin for VehicleDetails with VehicleImages display and Ride Type support
    """
    model = VehicleDetails
    extra = 0
    max_num = 1
    fields = (
        'brand', 'model', 'year_of_manufacture', 'vin',
        'vehicle_condition',
        'default_ride_type',
        'supported_ride_types',
        'vehicle_images_display',
        'plate_number',
        'color',
        'created_at', 'updated_at'
    )
    readonly_fields = ('created_at', 'updated_at', 'vehicle_images_display')
    can_delete = False
    classes = ('collapse',)
    filter_horizontal = ('supported_ride_types',)
    
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
        models.IntegerField: {
            'widget': forms.NumberInput(attrs={'style': 'width: 100%; min-width: 200px;'}),
        },
    }
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit default_ride_type choices to active ride types only"""
        if db_field.name == 'default_ride_type' and RideType:
            kwargs['queryset'] = RideType.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Limit supported_ride_types choices to active ride types only"""
        if db_field.name == 'supported_ride_types' and RideType:
            kwargs['queryset'] = RideType.objects.filter(is_active=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def vehicle_images_display(self, obj):
        """
        VehicleImages ni ko'rsatish (read-only, rasmlar sifatida)
        """
        if obj and obj.pk:
            images = list(obj.images.all())
            if images:
                # Har bir rasm uchun alohida blok
                img_blocks = format_html_join(
                    '\n',
                    '''
                    <div style="text-align: center; border: 1px solid #ddd; padding: 5px; border-radius: 5px; display: inline-block; margin: 5px;">
                        <img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 3px;" />
                        <br/>
                        <small style="color: #666;">{}</small>
                    </div>
                    ''',
                    (
                        (img.image.url, img.created_at.strftime("%Y-%m-%d %H:%M"))
                        for img in images
                    )
                )
                return format_html(
                    '<div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">{}</div>',
                    img_blocks
                )
        return format_html('<p style="color: #999; font-style: italic;">No images uploaded yet</p>')
    vehicle_images_display.short_description = "Vehicle Images"


class DriverIdentificationUploadDocumentInline(admin.TabularInline):
    """
    Inline admin for DriverIdentificationUploadDocument
    Shows all uploaded documents for this DriverIdentification
    """
    model = DriverIdentificationUploadDocument
    fk_name = 'driver_identification'
    extra = 0
    fields = ('user', 'document_file', 'document_preview', 'created_at', 'updated_at')
    readonly_fields = ('document_preview', 'created_at', 'updated_at')
    ordering = ('-updated_at',)
    can_delete = True
    show_change_link = True

    def document_preview(self, obj):
        """
        Fayl preview:
        - Agar rasm bo'lsa, Vehicle Images dagidek kartochka ko'rinishida <img>
        - Aks holda oddiy "Open file" link
        """
        if not obj or not obj.document_file:
            return format_html('<span style="color:#999;">No file</span>')

        url = obj.document_file.url
        mime_type, _ = mimetypes.guess_type(url)

        # Rasm bo'lsa: VehicleImages bilan bir xil karta
        if mime_type and mime_type.startswith('image/'):
            return format_html(
                '''
                <div style="text-align: center; border: 1px solid #ddd; padding: 5px; border-radius: 5px; display: inline-block; margin: 5px;">
                    <img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 3px;" />
                    <br/>
                    <small style="color: #666;">{}</small>
                </div>
                ''',
                url,
                obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else '',
            )

        # Boshqa fayllar uchun oddiy link
        return format_html('<a href="{}" target="_blank">Open file</a>', url)

    document_preview.short_description = "Preview"


@admin.register(DriverIdentificationUploadDocument)
class DriverIdentificationUploadDocumentAdmin(admin.ModelAdmin):
    """
    Admin for DriverIdentificationUploadDocument - alohida sahifada ko'rsatiladi
    """
    list_display = ('user', 'driver_identification', 'document_preview', 'created_at', 'updated_at')
    list_filter = ('driver_identification', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username', 'driver_identification__name')
    readonly_fields = ('document_preview', 'created_at', 'updated_at')
    ordering = ('-updated_at',)
    
    fieldsets = (
        ('Document Information', {
            'fields': ('user', 'driver_identification', 'document_file', 'document_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def document_preview(self, obj):
        """
        Fayl preview:
        - Agar rasm bo'lsa, Vehicle Images dagidek kartochka ko'rinishida <img>
        - Aks holda oddiy "Open file" link
        """
        if not obj or not obj.document_file:
            return format_html('<span style="color:#999;">No file</span>')

        url = obj.document_file.url
        mime_type, _ = mimetypes.guess_type(url)

        # Rasm bo'lsa: VehicleImages bilan bir xil karta
        if mime_type and mime_type.startswith('image/'):
            return format_html(
                '''
                <div style="text-align: center; border: 1px solid #ddd; padding: 5px; border-radius: 5px; display: inline-block; margin: 5px;">
                    <img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 3px;" />
                    <br/>
                    <small style="color: #666;">{}</small>
                </div>
                ''',
                url,
                obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else '',
            )

        # Boshqa fayllar uchun oddiy link
        return format_html('<a href="{}" target="_blank">Open file</a>', url)

    document_preview.short_description = "Preview"


@admin.register(DriverVerification)
class DriverVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'reviewer', 'estimated_review_hours', 'reviewed_at', 'updated_at')
    list_filter = ('status', 'estimated_review_hours', 'updated_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    ordering = ('-updated_at',)

    fieldsets = (
        ('Driver', {
            'fields': ('user',)
        }),
        ('Status', {
            'fields': ('status', 'estimated_review_hours')
        }),
        ('Review', {
            'fields': ('reviewer', 'comment', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Limit reviewer choices to superusers only.
        """
        if db_field.name == 'reviewer':
            kwargs['queryset'] = CustomUser.objects.filter(is_superuser=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """
        Set reviewer when status is changed from admin.
        Notification itself is created in model.save().
        """
        if change and 'status' in form.changed_data:
            obj.reviewer = request.user
        super().save_model(request, obj, form, change)


@admin.register(RiderUser)
class RiderUserAdmin(UserAdmin):
    """
    Admin panel for Riders only
    Faqat Rider guruhiga tegishli userlarni ko'rsatadi
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'id_identification', 'is_verified', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'tax_number', 'id_identification')
    ordering = ('-created_at',)
    
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 4, 'cols': 80, 'style': 'width: 100%; min-width: 500px;'}),
        },
        models.EmailField: {
            'widget': forms.EmailInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
    }
    
    inlines = [
        UserPreferencesInline,
        InvitationUsersInline,
        PinVerificationForRiderInline,
        UserDeviceTokenInline,
    ]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar')}),
        ('Additional Information', {'fields': ('address', 'longitude', 'latitude', 'tax_number', 'id_identification')}),
        ('Permissions', {'fields': ('is_active', 'groups')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
        ('Verification', {'fields': ('is_verified',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login', 'id_identification')
    
    def get_queryset(self, request):
        """
        Faqat Rider guruhiga tegishli userlarni qaytaradi
        """
        qs = super().get_queryset(request)
        try:
            rider_group = Group.objects.get(name='Rider')
            return qs.filter(groups=rider_group)
        except Group.DoesNotExist:
            return qs.none()
    
    def save_model(self, request, obj, form, change):
        """
        Auto-assign Rider group for new users
        """
        super().save_model(request, obj, form, change)
        if not change:
            try:
                rider_group = Group.objects.get(name='Rider')
                if rider_group not in obj.groups.all():
                    obj.groups.add(rider_group)
            except Group.DoesNotExist:
                pass


@admin.register(DriverUser)
class DriverUserAdmin(UserAdmin):
    """
    Admin panel for Drivers only
    Faqat Driver guruhiga tegishli userlarni ko'rsatadi
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'id_identification', 'is_verified', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'tax_number', 'id_identification')
    ordering = ('-created_at',)

    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 4, 'cols': 80, 'style': 'width: 100%; min-width: 500px;'}),
        },
        models.EmailField: {
            'widget': forms.EmailInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
    }
    
    inlines = [
        PinVerificationForDriverInline,
        DriverPreferencesInline,
        VehicleDetailsInline,
        UserDeviceTokenInline,
    ]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar')}),
        ('Additional Information', {'fields': ('address', 'longitude', 'latitude', 'tax_number', 'id_identification')}),
        ('Permissions', {'fields': ('is_active', 'groups')}),
        ('Online Status', {'fields': ('is_online',)}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
        ('Verification', {'fields': ('is_verified',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login', 'id_identification')
    
    def get_queryset(self, request):
        """
        Limit queryset to users in Driver group
        """
        qs = super().get_queryset(request)
        try:
            driver_group = Group.objects.get(name='Driver')
            return qs.filter(groups=driver_group)
        except Group.DoesNotExist:
            return qs.none()
    
    def save_model(self, request, obj, form, change):
        """
        Auto-assign Driver group for new users
        """
        super().save_model(request, obj, form, change)
        if not change:
            try:
                driver_group = Group.objects.get(name='Driver')
                if driver_group not in obj.groups.all():
                    obj.groups.add(driver_group)
            except Group.DoesNotExist:
                pass


class DriverIdentificationItemsInline(admin.TabularInline):
    """
    Inline admin for DriverIdentificationItems
    """
    model = DriverIdentificationItems
    extra = 1
    fields = ('item',)
    
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 250px;'}),
        },
    }


class DriverIdentificationFAQInline(admin.TabularInline):
    model = DriverIdentificationFAQ
    extra = 0
    fields = ('question', 'link', 'file', 'order')
    ordering = ('order',)


@admin.register(DriverIdentification)
class DriverIdentificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [DriverIdentificationItemsInline, DriverIdentificationFAQInline]
    
    # CharField va TextField uchun kengaytirilgan ko'rinish
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 4, 'cols': 80, 'style': 'width: 100%; min-width: 500px;'}),
        },
    }
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('display_type', 'name', 'title', 'description', 'is_active')
        }),
        ('Image', {
            'fields': ('image',)
        }),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(DriverIdentificationFAQ)
class DriverIdentificationFAQAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'driver_identification', 'order', 'created_at')
    list_filter = ('driver_identification',)
    search_fields = ('question',)
    ordering = ('driver_identification', 'order', 'id')

    def question_short(self, obj):
        return (obj.question[:50] + '...') if len(obj.question) > 50 else obj.question
    question_short.short_description = 'Question'


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ('name', 'link', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
    

@admin.register(DriverAgreement)
class DriverAgreementAdmin(admin.ModelAdmin):
    list_display = ('name', 'file', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Agreement Information', {
            'fields': ('name', 'file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


admin.site.unregister(Site)

admin.site.site_header = 'Hola Drive and Hola Driver Admin'
admin.site.site_title = 'Hola Drive and Hola Driver Admin'
admin.site.index_title = 'Hola Drive and Hola Driver Admin'