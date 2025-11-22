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