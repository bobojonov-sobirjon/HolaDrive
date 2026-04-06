import nested_admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.contenttypes.admin import GenericStackedInline
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from django.utils.html import format_html, format_html_join
from django.db import models
from django.db.models import Q
from django import forms
from .models import (
    CustomUser, RiderUser, DriverUser,
    VerificationCode, PasswordResetToken, UserPreferences,
    DriverPreferences, VehicleDetails, VehicleImages,
    DriverVerification, UserDeviceToken,
    InvitationGenerate, InvitationUsers, PinVerificationForUser,
    DriverIdentification,
    DriverIdentificationUploadType,
    DriverIdentificationUploadTypeItem,
    DriverIdentificationUploadTypeQuestionAnswer,
    DriverIdentificationLegalType,
    DriverIdentificationRegistrationType,
    DriverIdentificationTermsType,
    DriverIdentificationAgreementsItems,
    DriverIdentificationUploadTypeUserAccepted,
    DriverIdentificationLegalAgreementsUserAccepted,
    DriverIdentificationRegistrationAgreementsUserAccepted,
    DriverIdentificationTermsUserAccepted,
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


class RiderRegistrationAgreementAcceptedInline(admin.TabularInline):
    """Rider: registration agreement acceptances (same model as drivers)."""
    model = DriverIdentificationRegistrationAgreementsUserAccepted
    fk_name = 'user'
    extra = 0
    verbose_name_plural = 'Registration agreements accepted'
    fields = (
        'driver_identification_registration_agreements',
        'is_accepted',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('driver_identification_registration_agreements',)


class DriverUploadTypeAcceptedInline(admin.TabularInline):
    model = DriverIdentificationUploadTypeUserAccepted
    fk_name = 'user'
    extra = 0
    verbose_name_plural = 'Upload identifications accepted'
    fields = (
        'driver_identification_upload_type',
        'file',
        'is_accepted',
        'created_at',
    )
    readonly_fields = ('created_at',)
    autocomplete_fields = ('driver_identification_upload_type',)


class DriverLegalAgreementAcceptedInline(admin.TabularInline):
    model = DriverIdentificationLegalAgreementsUserAccepted
    fk_name = 'user'
    extra = 0
    verbose_name_plural = 'Legal agreements accepted'
    fields = (
        'driver_identification_legal_agreements',
        'is_accepted',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('driver_identification_legal_agreements',)


class DriverRegistrationAgreementAcceptedInline(admin.TabularInline):
    model = DriverIdentificationRegistrationAgreementsUserAccepted
    fk_name = 'user'
    extra = 0
    verbose_name_plural = 'Registration agreements accepted'
    fields = (
        'driver_identification_registration_agreements',
        'is_accepted',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('driver_identification_registration_agreements',)


class DriverTermsAcceptedInline(admin.TabularInline):
    model = DriverIdentificationTermsUserAccepted
    fk_name = 'user'
    extra = 0
    verbose_name_plural = 'Terms accepted'
    fields = (
        'driver_identification_terms',
        'is_accepted',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('driver_identification_terms',)


class DriverVerificationStatusListFilter(admin.SimpleListFilter):
    title = 'Driver verification'
    parameter_name = 'driver_verification_status'

    def lookups(self, request, model_admin):
        return DriverVerification.Status.choices

    def queryset(self, request, queryset):
        v = self.value()
        if v is None:
            return queryset
        if v == DriverVerification.Status.NOT_SUBMITTED:
            return queryset.filter(
                Q(driver_verification__status=v) | Q(driver_verification__isnull=True)
            )
        return queryset.filter(driver_verification__status=v)


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
        RiderRegistrationAgreementAcceptedInline,
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
    list_display = (
        'email',
        'username',
        'first_name',
        'last_name',
        'id_identification',
        'is_verified',
        'verification_activation',
        'is_active',
        'created_at',
    )
    list_filter = (
        DriverVerificationStatusListFilter,
        'is_verified',
        'is_active',
        'created_at',
    )
    search_fields = (
        'email',
        'username',
        'first_name',
        'last_name',
        'phone_number',
        'tax_number',
        'id_identification',
        'driver_verification__status',
        'driver_verification__comment',
    )
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
        DriverUploadTypeAcceptedInline,
        DriverLegalAgreementAcceptedInline,
        DriverRegistrationAgreementAcceptedInline,
        DriverTermsAcceptedInline,
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
            qs = qs.filter(groups=driver_group)
        except Group.DoesNotExist:
            return qs.none()
        return qs.select_related('driver_verification')

    @staticmethod
    def _verification_status_style(status):
        return {
            DriverVerification.Status.APPROVED: ('Approved', '#198754'),
            DriverVerification.Status.IN_REVIEW: ('In review', '#fd7e14'),
            DriverVerification.Status.REJECTED: ('Rejected', '#dc3545'),
            DriverVerification.Status.NOT_SUBMITTED: ('Not submitted', '#6c757d'),
        }.get(status, ('—', '#adb5bd'))

    @admin.display(description='Activation')
    def verification_activation(self, obj):
        dv = getattr(obj, 'driver_verification', None)
        if dv is None:
            label, color = ('Not submitted', '#6c757d')
        else:
            label, color = self._verification_status_style(dv.status)
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            color,
            label,
        )

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


_DRIVER_IDENTIFICATION_WIDE_TEXT = {
    models.CharField: {
        'widget': forms.TextInput(
            attrs={
                'style': 'width: 100%; max-width: 56rem; box-sizing: border-box;',
                'class': 'vTextField',
            }
        ),
    },
    models.TextField: {
        'widget': forms.Textarea(
            attrs={
                'rows': 6,
                'cols': 100,
                'style': 'width: 100%; max-width: 56rem; box-sizing: border-box;',
                'class': 'vLargeTextField',
            }
        ),
    },
}


class DriverIdentificationUploadTypeQuestionAnswerInline(nested_admin.NestedTabularInline):
    model = DriverIdentificationUploadTypeQuestionAnswer
    extra = 0
    verbose_name = 'Question / file'
    verbose_name_plural = 'Questions & attachments (this step)'
    classes = ('driver-id-qa-block',)
    fields = ('question', 'file', 'created_at')
    readonly_fields = ('created_at',)
    formfield_overrides = {
        models.CharField: {
            'widget': forms.Textarea(
                attrs={
                    'rows': 2,
                    'cols': 60,
                    'style': 'width: 100%; min-width: 100%; box-sizing: border-box; resize: vertical;',
                    'class': 'vLargeTextField',
                    'placeholder': 'Question shown to the driver',
                }
            ),
        },
    }

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ('question', 'file') and formfield is not None:
            formfield.help_text = ''
        return formfield


class DriverIdentificationUploadTypeItemInline(nested_admin.NestedStackedInline):
    model = DriverIdentificationUploadTypeItem
    extra = 0
    verbose_name = 'Checklist step'
    verbose_name_plural = 'Driver checklist (steps)'
    classes = ('driver-id-step-block',)
    fields = ('item', 'created_at')
    readonly_fields = ('created_at',)
    inlines = (DriverIdentificationUploadTypeQuestionAnswerInline,)
    formfield_overrides = {
        models.CharField: {
            'widget': forms.Textarea(
                attrs={
                    'rows': 3,
                    'cols': 80,
                    'style': 'width: 100%; max-width: 56rem; box-sizing: border-box;',
                    'class': 'vLargeTextField',
                    'placeholder': 'Short label or instruction for this checklist step',
                }
            ),
        },
    }

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'item' and formfield is not None:
            formfield.help_text = ''
        return formfield


@admin.register(DriverIdentificationUploadType)
class DriverIdentificationUploadTypeAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'is_active', 'display_type', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('display_type_label', 'created_at', 'updated_at')
    formfield_overrides = {**_DRIVER_IDENTIFICATION_WIDE_TEXT}
    fieldsets = (
        (None, {
            'classes': ('wide', 'driver-id-general'),
            'fields': ('title', 'description', 'display_type_label', 'is_active', 'icon'),
        }),
        ('Timestamps', {
            'classes': ('collapse', 'wide'),
            'fields': ('created_at', 'updated_at'),
        }),
    )
    inlines = (DriverIdentificationUploadTypeItemInline,)

    @admin.display(description='Display type')
    def display_type_label(self, obj):
        if obj is None or obj.pk is None:
            code = 'upload'
        else:
            code = obj.display_type
        return dict(DriverIdentification.IDENTIFICATION_TYPES).get(code, code)

    def save_model(self, request, obj, form, change):
        obj.display_type = 'upload'
        super().save_model(request, obj, form, change)


def driver_identification_agreements_stacked_inline(item_type: str):
    """
    Inline agreement rows for a single item_type; parent link via GenericForeignKey.
    item_type is forced on save by AgreementIdentificationAdminMixin.
    """

    class Inline(GenericStackedInline):
        model = DriverIdentificationAgreementsItems
        extra = 0
        ct_field = 'content_type'
        ct_fk_field = 'object_id'
        fields = ('title', 'content', 'file', 'created_at')
        readonly_fields = ('created_at',)
        formfield_overrides = {
            models.CharField: {
                'widget': forms.TextInput(
                    attrs={
                        'style': 'width: 100%; max-width: 56rem; box-sizing: border-box;',
                        'class': 'vTextField',
                    }
                ),
            },
        }

        def get_queryset(self, request):
            return super().get_queryset(request).filter(item_type=item_type)

    Inline.__name__ = f'DriverIdentificationAgreements{item_type.title()}Inline'
    return Inline


class AgreementItemTypeAdminMixin:
    agreement_item_type: str

    @admin.display(description='Display type')
    def display_type_label(self, obj):
        if obj is None or obj.pk is None:
            code = self.agreement_item_type
        else:
            code = obj.display_type
        return dict(DriverIdentification.IDENTIFICATION_TYPES).get(code, code)

    def save_formset(self, request, form, formset, change):
        if formset.model is DriverIdentificationAgreementsItems:
            instances = formset.save(commit=False)
            for obj in instances:
                obj.item_type = self.agreement_item_type
            for obj in formset.deleted_objects:
                obj.delete()
            for obj in instances:
                obj.save()
            formset.save_m2m()
            return
        super().save_formset(request, form, formset, change)


@admin.register(DriverIdentificationLegalType)
class DriverIdentificationLegalTypeAdmin(AgreementItemTypeAdminMixin, admin.ModelAdmin):
    agreement_item_type = 'legal'

    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('display_type_label', 'created_at', 'updated_at')
    formfield_overrides = {**_DRIVER_IDENTIFICATION_WIDE_TEXT}
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'display_type_label', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    inlines = (driver_identification_agreements_stacked_inline('legal'),)

    def save_model(self, request, obj, form, change):
        obj.display_type = 'legal'
        super().save_model(request, obj, form, change)


@admin.register(DriverIdentificationRegistrationType)
class DriverIdentificationRegistrationTypeAdmin(AgreementItemTypeAdminMixin, admin.ModelAdmin):
    agreement_item_type = 'registration'

    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('display_type_label', 'created_at', 'updated_at')
    formfield_overrides = {**_DRIVER_IDENTIFICATION_WIDE_TEXT}
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'display_type_label', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    inlines = (driver_identification_agreements_stacked_inline('registration'),)

    def save_model(self, request, obj, form, change):
        obj.display_type = 'registration'
        super().save_model(request, obj, form, change)


@admin.register(DriverIdentificationTermsType)
class DriverIdentificationTermsTypeAdmin(AgreementItemTypeAdminMixin, admin.ModelAdmin):
    agreement_item_type = 'terms'

    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('display_type_label', 'created_at', 'updated_at')
    formfield_overrides = {**_DRIVER_IDENTIFICATION_WIDE_TEXT}
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'display_type_label', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    inlines = (driver_identification_agreements_stacked_inline('terms'),)

    def save_model(self, request, obj, form, change):
        obj.display_type = 'terms'
        super().save_model(request, obj, form, change)


admin.site.unregister(Site)

admin.site.site_header = 'Hola Drive and Hola Driver Admin'
admin.site.site_title = 'Hola Drive and Hola Driver Admin'
admin.site.index_title = 'Hola Drive and Hola Driver Admin'