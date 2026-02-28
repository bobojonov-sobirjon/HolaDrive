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
    id_identification = models.CharField(
        max_length=9,
        unique=True,
        blank=True,
        null=True,
        verbose_name="ID Identification",
        help_text="Unique 9-digit identification number (auto-generated)"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email Verified",
        help_text="Indicates whether this user's email is verified."
    )
    is_online = models.BooleanField(
        default=False,
        verbose_name="Driver Online Status",
        help_text="Indicates whether driver is online and available for orders."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "01. Users"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email'], name='user_email_idx'),
            models.Index(fields=['phone_number'], name='user_phone_idx'),
            models.Index(fields=['id_identification'], name='user_id_identification_idx'),
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
    
    @staticmethod
    def generate_id_identification():
        """
        Generate a unique 9-digit identification number
        """
        while True:
            # Generate 9-digit number (100000000 to 999999999)
            id_number = str(random.randint(100000000, 999999999))
            # Check if it already exists
            if not CustomUser.objects.filter(id_identification=id_number).exists():
                return id_number
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-generate id_identification if not set
        """
        if not self.id_identification:
            self.id_identification = self.generate_id_identification()
        super().save(*args, **kwargs)


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
        verbose_name_plural = "02. Rider Preferences"
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
        verbose_name_plural = "04. PIN Verifications For Riders"
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
        verbose_name_plural = "03. Driver Preferences"
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
    Supports multiple ride types (like Uber/Yandex Go)
    """
    
    class VehicleCondition(models.TextChoices):
        EXCELLENT = 'excellent', 'Excellent'
        GOOD = 'good', 'Good'
        FAIR = 'fair', 'Fair'
    
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
    plate_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Plate Number",
        help_text="Vehicle license plate number (e.g., NYC 560)"
    )
    color = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Color",
        help_text="Vehicle color (e.g., White, Black, Red)"
    )
    vehicle_condition = models.CharField(
        max_length=20,
        choices=VehicleCondition.choices,
        default=VehicleCondition.GOOD,
        verbose_name="Vehicle Condition",
        help_text="Condition of the vehicle (affects ride type suggestions)"
    )
    default_ride_type = models.ForeignKey(
        'order.RideType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_vehicles',
        verbose_name="Default Ride Type",
        help_text="Primary/default ride type for this vehicle (shown first)"
    )
    supported_ride_types = models.ManyToManyField(
        'order.RideType',
        related_name='supported_vehicles',
        blank=True,
        verbose_name="Supported Ride Types",
        help_text="Ride types this vehicle can support (e.g., Standard, Premium, Eco). One vehicle can support multiple types."
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
            models.Index(fields=['vehicle_condition'], name='vehicle_condition_idx'),
            models.Index(fields=['updated_at'], name='vehicle_updated_idx'),
            models.Index(fields=['user', 'updated_at'], name='vehicle_user_updated_idx'),
        ]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year_of_manufacture}) - {self.user.email}"
    
    def is_electric_vehicle(self):
        """
        Determine if vehicle is electric based on brand and model.
        Returns True if vehicle is electric/hybrid, False otherwise.
        """
        electric_keywords = [
            'tesla', 'nissan leaf', 'bmw i', 'audi e', 'hyundai ioniq',
            'kia ev', 'volkswagen id', 'electric', 'ev', 'hybrid',
            'prius', 'bolt', 'volt', 'model 3', 'model s', 'model x', 'model y'
        ]
        
        brand_model = f"{self.brand} {self.model}".lower()
        return any(keyword in brand_model for keyword in electric_keywords)
    
    def suggest_ride_types(self):
        """
        Automatically suggest ride types based on vehicle characteristics.
        Similar to how Uber/Yandex Go work.
        
        Returns:
            list: List of RideType objects that are suggested for this vehicle
        """
        from apps.order.models import RideType
        
        suggestions = []
        
        # 1. Standard (Hola) - always available
        standard = RideType.objects.filter(
            is_premium=False,
            is_ev=False,
            is_active=True
        ).first()
        if standard:
            suggestions.append(standard)
        
        # 2. Premium - if vehicle meets premium criteria
        is_premium_brand = self.brand.lower() in [
            'mercedes', 'mercedes-benz', 'bmw', 'audi', 'lexus', 'porsche',
            'tesla', 'jaguar', 'land rover', 'range rover', 'bentley',
            'rolls-royce', 'maserati', 'ferrari', 'lamborghini', 'mclaren'
        ]
        
        is_recent_and_excellent = (
            self.year_of_manufacture >= 2020 and
            self.vehicle_condition == self.VehicleCondition.EXCELLENT
        )
        
        if is_premium_brand or is_recent_and_excellent:
            premium = RideType.objects.filter(
                is_premium=True,
                is_active=True
            ).first()
            if premium and premium not in suggestions:
                suggestions.append(premium)
        
        # 3. Eco - if vehicle is electric
        if self.is_electric_vehicle():
            eco = RideType.objects.filter(
                is_ev=True,
                is_active=True
            ).first()
            if eco and eco not in suggestions:
                suggestions.append(eco)
        
        # Ensure we have at least one suggestion (Standard)
        if not suggestions and standard:
            suggestions.append(standard)
        
        return suggestions
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically set ride types if not set.
        Only applies suggestions if supported_ride_types is empty (new vehicle or manually cleared).
        """
        is_new = self.pk is None
        
        super().save(*args, **kwargs)
        
        # Only auto-suggest if supported_ride_types is empty
        # This allows admin/driver to manually set ride types without auto-override
        if not self.supported_ride_types.exists():
            suggestions = self.suggest_ride_types()
            if suggestions:
                # Set suggested ride types
                self.supported_ride_types.set(suggestions)
                
                # Set default_ride_type to first suggestion if not set
                if not self.default_ride_type and suggestions:
                    self.default_ride_type = suggestions[0]
                    # Save again to update default_ride_type
                    super().save(update_fields=['default_ride_type'])


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
    
    IDENTIFICATION_TYPES = (
        ('upload', 'Photo Upload'),
        ('terms', 'Terms and Conditions'),
    )
    """
    Model for storing driver identification types (dynamic identification items)
    Admin can create different identification types like Driver's License, Profile Photo, etc.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Name",
        help_text="Unique name for the identification type (e.g., 'Driver License', 'Profile Photo')"
    )
    display_type = models.CharField(
        max_length=20, 
        choices=IDENTIFICATION_TYPES, 
        default='upload',
        verbose_name="Display Type",
        help_text="Whether to display a photo upload or only terms and conditions"
    )
    image = models.ImageField(
        upload_to='driver_identification_icons/',
        blank=True,
        null=True,
        verbose_name="Icon Image",
        help_text="Icon image for the identification type"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Title to display (e.g., 'Take a photo of your Driver's License')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
        help_text="Detailed description/instructions for the user"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this identification type is active and visible to users"
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
        verbose_name_plural = "03. Driver Identifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name'], name='driver_id_name_idx'),
            models.Index(fields=['is_active'], name='driver_id_active_idx'),
            models.Index(fields=['created_at'], name='driver_id_created_idx'),
            models.Index(fields=['is_active', 'created_at'], name='driver_id_active_created_idx'),
        ]

    def __str__(self):
        return self.name


class TermsAndConditionsAcceptance(models.Model):
    """
    Model for storing terms and conditions acceptance by drivers
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='terms_and_conditions_acceptance',
    )
    driver_identification = models.ForeignKey(
        DriverIdentification,
        on_delete=models.CASCADE,
        related_name='terms_and_conditions_acceptance',
    )
    is_accepted = models.BooleanField(
        default=True,
        verbose_name="Is Accepted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Terms and Conditions Acceptance"
        verbose_name_plural = "Terms and Conditions Acceptances"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='terms_accept_user_idx'),
            models.Index(fields=['driver_identification'], name='terms_accept_id_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'driver_identification'],
                name='terms_accept_user_di_uniq',
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.driver_identification.name}"

    @classmethod
    def accept_driver_identification(cls, user, driver_identification):
        """Create or update acceptance for user + driver_identification."""
        if not user or not driver_identification:
            return None
        obj, _ = cls.objects.update_or_create(
            user=user,
            driver_identification=driver_identification,
            defaults={'is_accepted': True},
        )
        return obj

class DriverIdentificationFAQ(models.Model):
    """
    FAQ entries for a driver identification (question, link, file).
    """
    driver_identification = models.ForeignKey(
        DriverIdentification,
        on_delete=models.CASCADE,
        related_name='identification_faq',
        verbose_name="Driver Identification",
    )
    question = models.CharField(
        max_length=500,
        verbose_name="Question",
        help_text="FAQ question text",
    )
    link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Link",
    )
    file = models.FileField(
        upload_to='driver_identification_faq_files/',
        blank=True,
        null=True,
        verbose_name="File",
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Order",
        help_text="Display order (lower first)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Driver Identification FAQ"
        verbose_name_plural = "Driver Identification FAQs"
        ordering = ['order', 'id']

    def __str__(self):
        return self.question[:50] + ('...' if len(self.question) > 50 else '')


class DriverIdentificationItems(models.Model):
    """
    Model for storing items related to driver identifications (many-to-many relationship)
    This allows linking multiple items to a single identification type
    """
    driver_identification = models.ForeignKey(
        DriverIdentification,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Driver Identification",
        help_text="The identification type this item belongs to"
    )
    item = models.CharField(
        max_length=255,
        verbose_name="Item",
        help_text="Item name or description"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    class Meta:
        verbose_name = "Driver Identification Item"
        verbose_name_plural = "Driver Identification Items (Type: Upload)"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['driver_identification'], name='driver_id_item_id_idx'),
            models.Index(fields=['created_at'], name='driver_id_item_created_idx'),
        ]

    def __str__(self):
        return f"{self.driver_identification.name} - {self.item}"


class DriverIdentificationUploadDocument(models.Model):
    """
    Model for storing user-uploaded documents for driver identifications
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='driver_identification_uploads',
        verbose_name="User",
        help_text="User who uploaded the document"
    )
    driver_identification = models.ForeignKey(
        DriverIdentification,
        on_delete=models.CASCADE,
        related_name='uploaded_documents',
        verbose_name="Driver Identification",
        help_text="The identification type this document is for"
    )
    document_file = models.FileField(
        upload_to='driver_documents/',
        verbose_name="Document File",
        help_text="Uploaded document file (any file type)"
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
        verbose_name = "Driver Identification Upload Document"
        verbose_name_plural = "Driver Identification Upload Documents"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='driver_upload_user_idx'),
            models.Index(fields=['driver_identification'], name='driver_upload_id_idx'),
            models.Index(fields=['user', 'driver_identification'], name='driver_upload_user_id_idx'),
            models.Index(fields=['updated_at'], name='driver_upload_updated_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'driver_identification'],
                name='unique_user_driver_identification'
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.driver_identification.name}"


class DriverAgreement(models.Model):
    """
    Model for storing driver agreements
    """
    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text="Name of the agreement"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this agreement is visible to drivers"
    )
    file = models.FileField(
        upload_to='driver_agreements/',
        verbose_name="File",
        help_text="File of the agreement"
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
        verbose_name = "Driver Agreement"
        verbose_name_plural = "05. Driver Agreements"
        ordering = ['-updated_at']


class DriverVerification(models.Model):
    """
    Model for tracking overall driver verification status.
    Used to show 'In review / Approved / Rejected' screen and
    to trigger notifications when status changes.
    """

    class Status(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', 'Not submitted'
        IN_REVIEW = 'in_review', 'In review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='driver_verification',
        verbose_name="Driver",
        help_text="Driver this verification belongs to"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_SUBMITTED,
        verbose_name="Status",
        help_text="Current verification status"
    )
    reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_drivers',
        verbose_name="Reviewer",
        help_text="Admin/staff user who last reviewed this driver"
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name="Comment",
        help_text="Optional reviewer comment"
    )
    estimated_review_hours = models.IntegerField(
        default=48,
        verbose_name="Estimated Review Hours",
        help_text="Estimated review time in hours"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Reviewed At",
        help_text="Timestamp when status was last set to Approved/Rejected"
    )

    class Meta:
        verbose_name = "Driver Verification"
        verbose_name_plural = "04. Driver Verifications"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='driver_ver_user_idx'),
            models.Index(fields=['status'], name='driver_ver_status_idx'),
            models.Index(fields=['updated_at'], name='driver_ver_updated_idx'),
            models.Index(fields=['user', 'status'], name='driver_ver_user_status_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """
        Override save to detect status changes and create Notification.
        """
        import logging
        from apps.notification.models import Notification
        from apps.notification.services import send_push_to_user

        logger = logging.getLogger(__name__)

        old_status = None
        if self.pk:
            old_status = (
                DriverVerification.objects.filter(pk=self.pk)
                .values_list('status', flat=True)
                .first()
            )

        # Set reviewed_at when moving to terminal states
        if self.status in {self.Status.APPROVED, self.Status.REJECTED} and self.reviewed_at is None:
            self.reviewed_at = timezone.now()

        logger.info(
            "DriverVerification.save() called for user=%s old_status=%s new_status=%s",
            self.user_id,
            old_status,
            self.status,
        )

        super().save(*args, **kwargs)

        # Create notification on create or status change
        if old_status != self.status:
            logger.info(
                "DriverVerification status changed – creating Notification for user=%s status=%s",
                self.user_id,
                self.status,
            )
            notification = Notification.objects.create(
                user=self.user,
                notification_type=Notification.NotificationType.SYSTEM,
                title="Driver verification status updated",
                message=f"Your driver verification status is now: {self.get_status_display()}",
                related_object_type="driver_verification",
                related_object_id=self.pk,
                data={"status": self.status},
            )
            # Try to send push notification (best-effort, non-blocking for main flow)
            success, error = send_push_to_user(
                user=self.user,
                title=notification.title,
                body=notification.message,
                data=notification.data or {},
            )
            logger.info(
                "DriverVerification push result user=%s success=%s error=%s",
                self.user_id,
                success,
                error,
            )
        else:
            logger.info(
                "DriverVerification status not changed – no Notification created (user=%s, status=%s)",
                self.user_id,
                self.status,
            )


class UserDeviceToken(models.Model):
    """
    Stores push notification device tokens for users.
    """

    class DeviceType(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        verbose_name="User",
    )
    token = models.CharField(
        max_length=512,
        verbose_name="Device Token",
        help_text="Push notification token (FCM/APNs/etc.)",
    )
    mobile = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        verbose_name="Device Type",
        help_text="Device type / platform",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
    )

    class Meta:
        verbose_name = "User Device Token"
        verbose_name_plural = "User Device Tokens"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='device_token_user_idx'),
            models.Index(fields=['mobile'], name='device_token_mobile_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'mobile'],
                name='unique_user_mobile_device_token',
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.mobile}"
    
    @classmethod
    def upsert_token(cls, user, token: str, mobile: str):
        """
        Create or update device token for given user & mobile platform.
        """
        if not user or not token or not mobile:
            return None
        token = token.strip()
        if not token:
            return None
        obj, _ = cls.objects.update_or_create(
            user=user,
            mobile=mobile,
            defaults={'token': token},
        )
        return obj


class LegalPage(models.Model):
    """
    Single model for Privacy Policy, Terms of Service, etc.
    name: e.g. "Privacy Policy", "Terms of Service"
    link: URL to the page
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Name",
        help_text="e.g. Privacy Policy, Terms of Service"
    )
    link = models.URLField(
        max_length=500,
        verbose_name="Link",
        help_text="URL to the page"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Legal Agreement"
        verbose_name_plural = "Legal Agreements"
        ordering = ['name']

    def __str__(self):
        return self.name
    

class AcceptanceOfAgreement(models.Model):
    """
    Model for storing user acceptance of agreements
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='acceptance_of_agreements',
    )
    agreement = models.ForeignKey(
        LegalPage,
        on_delete=models.CASCADE,
        related_name='acceptance_of_agreements',
    )
    is_accepted = models.BooleanField(
        default=True,
        verbose_name="Is Accepted",
        help_text="Whether this agreement is accepted by the user",
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Acceptance of Agreement"
        verbose_name_plural = "Acceptance of Agreements"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='acc_agree_user_idx'),
            models.Index(fields=['agreement'], name='acc_agree_agmt_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'agreement'],
                name='unique_user_agreement_acceptance',
            ),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.agreement.name}"
    
    @classmethod
    def accept_agreement(cls, user, agreement):
        """
        Accept an agreement for a user
        """
        if not user or not agreement:
            return None

        obj, _ = cls.objects.update_or_create(
            user=user,
            agreement=agreement,
            defaults={'accepted_at': timezone.now()},
        )
        return obj

    @classmethod
    def is_agreement_accepted(cls, user, agreement):
        """
        Check if a user has accepted an agreement
        """
        if not user or not agreement:
            return False
        return cls.objects.filter(user=user, agreement=agreement).exists()


class RiderUser(CustomUser):
    """
    Proxy model for Riders in admin panel
    """
    class Meta:
        proxy = True
        verbose_name = "Rider"
        verbose_name_plural = "01. Riders"


class DriverUser(CustomUser):
    """
    Proxy model for Drivers in admin panel
    """
    class Meta:
        proxy = True
        verbose_name = "Driver"
        verbose_name_plural = "02. Drivers"