from __future__ import annotations

import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import CustomUser


def _share_token() -> str:
    return secrets.token_urlsafe(24)


class TripShareLink(models.Model):
    """Public, time-limited link so friends can follow an active trip."""

    order = models.ForeignKey(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='share_links',
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='trip_share_links',
    )
    token = models.CharField(max_length=64, unique=True, default=_share_token, db_index=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trip Share Link'
        verbose_name_plural = '01 Trip Share Links'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'is_active'], name='tripshare_order_active_idx'),
            models.Index(fields=['expires_at'], name='tripshare_expires_idx'),
        ]

    def __str__(self):
        return f'Share order={self.order_id} token={self.token[:8]}…'

    @property
    def is_valid(self) -> bool:
        if not self.is_active or self.revoked_at:
            return False
        return timezone.now() < self.expires_at

    @property
    def deep_link(self) -> str:
        """Native app scheme — opens HolaDrive app if installed."""
        scheme = getattr(settings, 'APP_DEEP_LINK_SCHEME', 'holadrive') or 'holadrive'
        return f'{scheme}://trip/share/{self.token}'

    @property
    def share_url(self) -> str:
        """
        HTTPS link for SMS / WhatsApp / system share sheet.
        Opens lightweight viewer on API host (or App Links into the mobile app).
        """
        base = (getattr(settings, 'APP_SHARE_HTTPS_BASE', '') or '').rstrip('/')
        if not base:
            base = (getattr(settings, 'PUBLIC_BASE_URL', '') or '').rstrip('/')
        if base:
            return f'{base}/trip/share/{self.token}'
        return f'/trip/share/{self.token}'

    @property
    def public_api_url(self) -> str:
        """JSON API for the shared trip (no auth)."""
        base = (getattr(settings, 'PUBLIC_BASE_URL', '') or '').rstrip('/')
        if base:
            return f'{base}/api/v1/safety/share/{self.token}/'
        return f'/api/v1/safety/share/{self.token}/'


class SafetyRoom(models.Model):
    """Safety-agent chat (separate from general SupportRoom)."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='safety_rooms',
    )
    agent = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='safety_rooms_as_agent',
        help_text='Staff/admin handling safety chats',
    )
    orders = models.ManyToManyField(
        'order.Order',
        blank=True,
        related_name='safety_rooms',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Safety Room'
        verbose_name_plural = '02 Safety Rooms'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'agent'], name='safety_room_user_agent_uniq'),
        ]
        indexes = [
            models.Index(fields=['user'], name='safetyroom_user_idx'),
            models.Index(fields=['agent'], name='safetyroom_agent_idx'),
        ]

    def __str__(self):
        return f'SafetyRoom user={self.user_id} agent={self.agent_id}'


class SafetyMessage(models.Model):
    class MessageType(models.TextChoices):
        USER = 'user', 'User'
        AGENT = 'agent', 'Agent'
        SYSTEM = 'system', 'System'

    room = models.ForeignKey(
        SafetyRoom,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='safety_messages_sent',
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.USER,
    )
    message = models.TextField()
    order = models.ForeignKey(
        'order.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='safety_messages',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Safety Message'
        verbose_name_plural = '03 Safety Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at'], name='safetymsg_room_created_idx'),
        ]

    def __str__(self):
        return f'{self.message_type}: {self.message[:40]}'


def trip_recording_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'm4a'
    return f'safety/recordings/{instance.order_id}/{uuid.uuid4().hex}.{ext}'


class TripVoiceRecording(models.Model):
    """In-trip safety voice recording (not Agora call recording)."""

    class Status(models.TextChoices):
        RECORDING = 'recording', 'Recording'
        UPLOADED = 'uploaded', 'Uploaded'
        FAILED = 'failed', 'Failed'
        DELETED = 'deleted', 'Deleted'

    order = models.ForeignKey(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='safety_voice_recordings',
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='safety_voice_recordings',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECORDING,
    )
    audio_file = models.FileField(
        upload_to=trip_recording_upload_to,
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trip Voice Recording'
        verbose_name_plural = '04 Trip Voice Recordings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status'], name='triprec_order_status_idx'),
            models.Index(fields=['user'], name='triprec_user_idx'),
        ]

    def __str__(self):
        return f'Recording order={self.order_id} status={self.status}'
