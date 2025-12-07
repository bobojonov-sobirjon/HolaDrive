from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal
import random
from datetime import timedelta
from django.utils import timezone


class CustomUser(AbstractUser):
    """
    Custom User model that extends Django's AbstractUser
    """
    
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'
    
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Required. Enter a valid email address."
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Phone Number",
        help_text="Optional. Enter your phone number."
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date of Birth",
        help_text="Optional. Enter your date of birth."
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
        null=True,
        verbose_name="Gender",
        help_text="Optional. Select your gender."
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="Avatar",
        help_text="Optional. Upload your profile photo."
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Address",
        help_text="Optional. Enter your address."
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name="Longitude",
        help_text="Optional. Longitude of your location."
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name="Latitude",
        help_text="Optional. Latitude of your location."
    )
    tax_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Tax Number (GST/HST)",
        help_text="Optional. Enter your tax number (GST/HST)."
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email Verified",
        help_text="Indicates whether this user's email is verified."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email'], name='user_email_idx'),
            models.Index(fields=['phone_number'], name='user_phone_idx'),
            models.Index(fields=['is_verified'], name='user_verified_idx'),
            models.Index(fields=['is_active'], name='user_active_idx'),
            models.Index(fields=['created_at'], name='user_created_idx'),
            models.Index(fields=['email', 'is_active'], name='user_email_act_idx'),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    def get_short_name(self):
        """
        Return the short name for the user.
        """
        return self.first_name if self.first_name else self.email


class VerificationCode(models.Model):
    """
    Model for storing verification codes (OTP)
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='verification_codes',
        verbose_name="User"
    )
    code = models.CharField(
        max_length=4,
        verbose_name="Verification Code"
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Phone Number"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Is Used"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    expires_at = models.DateTimeField(
        verbose_name="Expires At"
    )

    class Meta:
        verbose_name = "Verification Code"
        verbose_name_plural = "Verification Codes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='verif_user_idx'),
            models.Index(fields=['code'], name='verif_code_idx'),
            models.Index(fields=['is_used'], name='verif_used_idx'),
            models.Index(fields=['expires_at'], name='verif_expires_idx'),
            models.Index(fields=['user', 'code', 'is_used'], name='verif_user_code_used_idx'),
            models.Index(fields=['created_at'], name='verif_created_idx'),
        ]

    def __str__(self):
        return f"{self.code} for {self.user.email or self.phone_number}"

    def is_valid(self):
        """
        Check if the code is still valid (not used and not expired)
        """
        return not self.is_used and timezone.now() < self.expires_at

    @staticmethod
    def generate_code():
        """
        Generate a 4-digit verification code
        """
        return str(random.randint(1000, 9999))

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)


class PasswordResetToken(models.Model):
    """
    Model for storing password reset tokens
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name="User"
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Reset Token"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Is Used"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    expires_at = models.DateTimeField(
        verbose_name="Expires At"
    )

    class Meta:
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='reset_user_idx'),
            models.Index(fields=['token'], name='reset_token_idx'),
            models.Index(fields=['is_used'], name='reset_used_idx'),
            models.Index(fields=['expires_at'], name='reset_expires_idx'),
            models.Index(fields=['token', 'is_used'], name='reset_token_used_idx'),
            models.Index(fields=['created_at'], name='reset_created_idx'),
        ]

    def __str__(self):
        return f"Reset token for {self.user.email}"

    def is_valid(self):
        """
        Check if the token is still valid (not used and not expired)
        """
        return not self.is_used and timezone.now() < self.expires_at

    @staticmethod
    def generate_token():
        """
        Generate a random token
        """
        import secrets
        return secrets.token_urlsafe(32)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)


class UserPreferences(models.Model):
    """
    Model for storing user ride preferences
    """
    
    class ChattingPreference(models.TextChoices):
        NO_COMMUNICATION = 'no_communication', 'No Communication'
        CASUAL = 'casual', 'Casual'
        FRIENDLY = 'friendly', 'Friendly'
    
    class TemperaturePreference(models.TextChoices):
        WARM = 'warm', 'Warm (25°C and above)'
        COMFORTABLE = 'comfortable', 'Comfortable (22-24°C)'
        COOL = 'cool', 'Cool (18-21°C)'
        COLD = 'cold', 'Cold (below 18°C)'
    
    class MusicPreference(models.TextChoices):
        POP = 'pop', 'Pop'
        ROCK = 'rock', 'Rock'
        JAZZ = 'jazz', 'Jazz'
        CLASSICAL = 'classical', 'Classical'
        HIP_HOP = 'hip_hop', 'Hip Hop'
        ELECTRONIC = 'electronic', 'Electronic'
        COUNTRY = 'country', 'Country'
        NO_MUSIC = 'no_music', 'No Music'
    
    class VolumeLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        MUTE = 'mute', 'Mute'
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='user_preferences',
        verbose_name="User",
        help_text="User who owns these preferences"
    )
    chatting_preference = models.CharField(
        max_length=20,
        choices=ChattingPreference.choices,
        default=ChattingPreference.NO_COMMUNICATION,
        verbose_name="Chatting Preference",
        help_text="Preferred communication style during rides"
    )
    temperature_preference = models.CharField(
        max_length=20,
        choices=TemperaturePreference.choices,
        default=TemperaturePreference.COMFORTABLE,
        verbose_name="Temperature Preference",
        help_text="Preferred temperature range in the vehicle"
    )
    music_preference = models.CharField(
        max_length=20,
        choices=MusicPreference.choices,
        default=MusicPreference.POP,
        verbose_name="Music Preference",
        help_text="Preferred music genre"
    )
    volume_level = models.CharField(
        max_length=10,
        choices=VolumeLevel.choices,
        default=VolumeLevel.MEDIUM,
        verbose_name="Volume Level",
        help_text="Preferred music volume level"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='pref_user_idx'),
            models.Index(fields=['updated_at'], name='pref_updated_idx'),
            models.Index(fields=['user', 'updated_at'], name='pref_user_updated_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='unique_user_preferences'
            )
        ]

    def __str__(self):
        return f"Preferences for {self.user.email}"


class InvitationGenerate(models.Model):
    """
    Model for storing invitation codes generated by users
    Each user can have only one invitation code
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='invitation_generate',
        verbose_name="User",
        help_text="User who generated the invitation code"
    )
    invite_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Invite Code",
        help_text="Unique invitation code for the user"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    class Meta:
        verbose_name = "Invitation Generate"
        verbose_name_plural = "Invitation Generates"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='inv_gen_user_idx'),
            models.Index(fields=['invite_code'], name='inv_gen_code_idx'),
            models.Index(fields=['created_at'], name='inv_gen_created_idx'),
        ]

    def __str__(self):
        return f"Invitation code {self.invite_code} for {self.user.email}"

    @staticmethod
    def generate_invite_code():
        """
        Generate a unique invitation code
        """
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(10))
        while InvitationGenerate.objects.filter(invite_code=code).exists():
            code = ''.join(secrets.choice(alphabet) for _ in range(10))
        return code

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self.generate_invite_code()
        super().save(*args, **kwargs)


class InvitationUsers(models.Model):
    """
    Model for storing invitation relationships between users
    When a user enters an invitation code during login, they become the receiver
    """
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name="Sender",
        help_text="User who sent the invitation (owner of the invitation code)"
    )
    receiver = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_invitations',
        verbose_name="Receiver",
        help_text="User who used the invitation code",
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this invitation is still active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    class Meta:
        verbose_name = "Invitation User"
        verbose_name_plural = "Invitation Users"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender'], name='inv_user_sender_idx'),
            models.Index(fields=['receiver'], name='inv_user_receiver_idx'),
            models.Index(fields=['is_active'], name='inv_user_active_idx'),
            models.Index(fields=['created_at'], name='inv_user_created_idx'),
            models.Index(fields=['sender', 'is_active'], name='inv_user_sender_active_idx'),
        ]

    def __str__(self):
        if self.receiver:
            return f"{self.sender.email} invited {self.receiver.email}"
        return f"Invitation from {self.sender.email} (pending)"


class PinVerificationForUser(models.Model):
    """
    Model for storing PIN verification codes for users
    Each user can have only one PIN, which can be changed but not deleted
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='pin_verification',
        verbose_name="User",
        help_text="User who owns the PIN"
    )
    pin = models.CharField(
        max_length=4,
        verbose_name="PIN",
        help_text="4-digit PIN code"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        verbose_name = "PIN Verification For User"
        verbose_name_plural = "PIN Verifications For Users"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='pin_user_idx'),
            models.Index(fields=['pin'], name='pin_code_idx'),
            models.Index(fields=['created_at'], name='pin_created_idx'),
            models.Index(fields=['updated_at'], name='pin_updated_idx'),
        ]

    def __str__(self):
        return f"PIN for {self.user.email}"


class DriverPreferences(models.Model):
    """
    Model for storing driver ride preferences
    """
    
    class TripTypePreference(models.TextChoices):
        SHORT_TRIPS = 'short_trips', 'Short trips (under 5 km)'
        MEDIUM_TRIPS = 'medium_trips', 'Medium trips (5-15 km)'
        LONG_TRIPS = 'long_trips', 'Long trips (over 15 km)'
        ANY = 'any', 'Any trip length'
    
    class MaximumPickupDistance(models.TextChoices):
        ONE_KM = '1', '1 km'
        THREE_KM = '3', '3 km'
        FIVE_KM = '5', '5 km'
        TEN_KM = '10', '10 km'
        FIFTEEN_KM = '15', '15 km'
        TWENTY_KM = '20', '20 km'
    
    class PreferredWorkingHours(models.TextChoices):
        MORNING = 'morning', 'Morning (6 AM - 12 PM)'
        AFTERNOON = 'afternoon', 'Afternoon (12 PM - 6 PM)'
        EVENING = 'evening', 'Evening (6 PM - 12 AM)'
        NIGHT = 'night', 'Night (12 AM - 6 AM)'
        ANY = 'any', 'Any time'
    
    class NotificationIntensity(models.TextChoices):
        MINIMAL = 'minimal', 'Minimal (only ride requests)'
        MODERATE = 'moderate', 'Moderate (ride requests + updates)'
        HIGH = 'high', 'High (all notifications)'
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='driver_preferences',
        verbose_name="User",
        help_text="Driver who owns these preferences"
    )
    trip_type_preference = models.CharField(
        max_length=20,
        choices=TripTypePreference.choices,
        default=TripTypePreference.ANY,
        verbose_name="Trip Type Preference",
        help_text="Preferred trip length"
    )
    maximum_pickup_distance = models.CharField(
        max_length=10,
        choices=MaximumPickupDistance.choices,
        default=MaximumPickupDistance.FIVE_KM,
        verbose_name="Maximum Pickup Distance",
        help_text="Maximum distance driver is willing to travel for pickup"
    )
    preferred_working_hours = models.CharField(
        max_length=20,
        choices=PreferredWorkingHours.choices,
        default=PreferredWorkingHours.ANY,
        verbose_name="Preferred Working Hours",
        help_text="Preferred time of day to work"
    )
    notification_intensity = models.CharField(
        max_length=20,
        choices=NotificationIntensity.choices,
        default=NotificationIntensity.MINIMAL,
        verbose_name="Notification Intensity",
        help_text="How many notifications to receive"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        verbose_name = "Driver Preference"
        verbose_name_plural = "Driver Preferences"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='driver_pref_user_idx'),
            models.Index(fields=['updated_at'], name='driver_pref_updated_idx'),
            models.Index(fields=['user', 'updated_at'], name='driver_pref_user_updated_idx'),
            models.Index(fields=['trip_type_preference'], name='driver_pref_trip_type_idx'),
            models.Index(fields=['preferred_working_hours'], name='driver_pref_working_hours_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='unique_driver_preferences'
            )
        ]

    def __str__(self):
        return f"Driver preferences for {self.user.email}"


class VehicleDetails(models.Model):
    """
    Model for storing vehicle details for drivers
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='vehicle_details',
        verbose_name="Driver",
        help_text="Driver who owns this vehicle"
    )
    brand = models.CharField(
        max_length=100,
        verbose_name="Brand of car",
        help_text="Vehicle brand (e.g., Toyota, Honda, etc.)"
    )
    model = models.CharField(
        max_length=100,
        verbose_name="Model of car",
        help_text="Vehicle model (e.g., Camry, Accord, etc.)"
    )
    year_of_manufacture = models.IntegerField(
        verbose_name="Year of Manufacture",
        help_text="Year the vehicle was manufactured (2015 or newer)"
    )
    vin = models.CharField(
        max_length=17,
        unique=True,
        verbose_name="Vehicle Identification Number (VIN)",
        help_text="Unique vehicle identification number"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        verbose_name = "Vehicle Detail"
        verbose_name_plural = "Vehicle Details"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='vehicle_user_idx'),
            models.Index(fields=['vin'], name='vehicle_vin_idx'),
            models.Index(fields=['brand'], name='vehicle_brand_idx'),
            models.Index(fields=['model'], name='vehicle_model_idx'),
            models.Index(fields=['year_of_manufacture'], name='vehicle_year_idx'),
            models.Index(fields=['updated_at'], name='vehicle_updated_idx'),
            models.Index(fields=['user', 'updated_at'], name='vehicle_user_updated_idx'),
        ]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year_of_manufacture}) - {self.user.email}"


class VehicleImages(models.Model):
    """
    Model for storing vehicle images
    """
    vehicle = models.ForeignKey(
        VehicleDetails,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Vehicle",
        help_text="Vehicle these images belong to"
    )
    image = models.ImageField(
        upload_to='vehicles/',
        verbose_name="Vehicle Image",
        help_text="Image of the vehicle"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    class Meta:
        verbose_name = "Vehicle Image"
        verbose_name_plural = "Vehicle Images"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vehicle'], name='veh_img_vehicle_idx'),
            models.Index(fields=['created_at'], name='veh_img_created_idx'),
            models.Index(fields=['vehicle', 'created_at'], name='veh_img_veh_created_idx'),
        ]

    def __str__(self):
        return f"Image for {self.vehicle.brand} {self.vehicle.model}"


class DriverIdentification(models.Model):
    """
    Model for storing driver identification documents and verification status
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='driver_identification',
        verbose_name="Driver",
        help_text="Driver who owns these identification documents"
    )
    
    # Image fields (documents)
    proof_of_work_eligibility = models.ImageField(
        upload_to='driver_documents/proof_of_work/',
        blank=True,
        null=True,
        verbose_name="Proof of Work Eligibility",
        help_text="Photo of proof of work eligibility document"
    )
    profile_photo = models.ImageField(
        upload_to='driver_documents/profile_photos/',
        blank=True,
        null=True,
        verbose_name="Profile Photo",
        help_text="Driver profile photo (verified by Veriff)"
    )
    drivers_license = models.ImageField(
        upload_to='driver_documents/drivers_license/',
        blank=True,
        null=True,
        verbose_name="Driver's License",
        help_text="Photo of driver's license (Class 1, 2, or 4 required)"
    )
    background_check = models.ImageField(
        upload_to='driver_documents/background_check/',
        blank=True,
        null=True,
        verbose_name="Background Check",
        help_text="Photo of background check results"
    )
    driver_abstract = models.ImageField(
        upload_to='driver_documents/driver_abstract/',
        blank=True,
        null=True,
        verbose_name="Driver Abstract",
        help_text="Photo of province driver abstract (3-year Personal Driver Abstract)"
    )
    livery_vehicle_registration = models.ImageField(
        upload_to='driver_documents/livery_registration/',
        blank=True,
        null=True,
        verbose_name="Livery Vehicle Registration",
        help_text="Photo of livery vehicle registration (Class 1-55 or Class 1-66)"
    )
    vehicle_insurance = models.ImageField(
        upload_to='driver_documents/vehicle_insurance/',
        blank=True,
        null=True,
        verbose_name="Vehicle Insurance",
        help_text="Photo of vehicle insurance document"
    )
    city_tndl = models.ImageField(
        upload_to='driver_documents/city_tndl/',
        blank=True,
        null=True,
        verbose_name="City TNDL",
        help_text="Photo of City TNDL (Taxi Network Driver License)"
    )
    elvis_vehicle_inspection = models.ImageField(
        upload_to='driver_documents/elvis_inspection/',
        blank=True,
        null=True,
        verbose_name="ELVIS Vehicle Inspection Form",
        help_text="Photo of ELVIS (Enhanced Livery Vehicle Inspection Standards) certificate"
    )
    
    # Boolean fields (agreements)
    terms_and_conditions = models.BooleanField(
        default=False,
        verbose_name="Terms and Conditions",
        help_text="Whether driver has agreed to terms and conditions"
    )
    legal_agreements = models.BooleanField(
        default=False,
        verbose_name="Legal Agreements",
        help_text="Whether driver has agreed to legal agreements"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        verbose_name = "Driver Identification"
        verbose_name_plural = "Driver Identifications"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='driver_id_user_idx'),
            models.Index(fields=['updated_at'], name='driver_id_updated_idx'),
            models.Index(fields=['user', 'updated_at'], name='driver_id_user_updated_idx'),
            models.Index(fields=['terms_and_conditions'], name='driver_id_terms_idx'),
            models.Index(fields=['legal_agreements'], name='driver_id_legal_idx'),
        ]

    def __str__(self):
        return f"Identification for {self.user.email}"
    
    def get_completion_status(self):
        """
        Get completion status for each identification step
        Returns a dictionary with True/False for each step
        """
        return {
            'proof_of_work_eligibility': bool(self.proof_of_work_eligibility),
            'profile_photo': bool(self.profile_photo),
            'drivers_license': bool(self.drivers_license),
            'background_check': bool(self.background_check),
            'driver_abstract': bool(self.driver_abstract),
            'livery_vehicle_registration': bool(self.livery_vehicle_registration),
            'vehicle_insurance': bool(self.vehicle_insurance),
            'city_tndl': bool(self.city_tndl),
            'elvis_vehicle_inspection': bool(self.elvis_vehicle_inspection),
            'terms_and_conditions': self.terms_and_conditions,
            'legal_agreements': self.legal_agreements,
        }
    
    def get_completion_count(self):
        """
        Get count of completed steps
        """
        status = self.get_completion_status()
        return sum(1 for value in status.values() if value)
    
    def get_total_steps(self):
        """
        Get total number of steps
        """
        return 11