from django.db import models

from apps.accounts.models import CustomUser


class VoiceCallSession(models.Model):
    """Agora voice call session (trip rider↔driver or user↔support)."""

    class CallType(models.TextChoices):
        TRIP = 'trip', 'Trip'
        RIDER_SUPPORT = 'rider_support', 'Rider Support'
        DRIVER_SUPPORT = 'driver_support', 'Driver Support'

    class Status(models.TextChoices):
        RINGING = 'ringing', 'Ringing'
        ANSWERED = 'answered', 'Answered'
        ENDED = 'ended', 'Ended'
        MISSED = 'missed', 'Missed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        FAILED = 'failed', 'Failed'

    class InitiatorRole(models.TextChoices):
        RIDER = 'rider', 'Rider'
        DRIVER = 'driver', 'Driver'
        ADMIN = 'admin', 'Admin'

    call_type = models.CharField(max_length=20, choices=CallType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RINGING,
    )
    order = models.ForeignKey(
        'order.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voice_calls',
    )
    support_room = models.ForeignKey(
        'chat.SupportRoom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voice_calls',
    )
    caller = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='voice_calls_made',
    )
    callee = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voice_calls_received',
    )
    agora_channel_name = models.CharField(max_length=128, unique=True)
    agora_app_id = models.CharField(max_length=64, blank=True)
    initiator_role = models.CharField(max_length=20, choices=InitiatorRole.choices)
    ring_started_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    end_reason = models.CharField(max_length=255, blank=True)
    operator_note = models.TextField(blank=True, help_text='Admin summary after support call')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Voice Call Session'
        verbose_name_plural = 'Voice Call Sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['call_type'], name='voicecall_type_idx'),
            models.Index(fields=['status'], name='voicecall_status_idx'),
            models.Index(fields=['caller'], name='voicecall_caller_idx'),
            models.Index(fields=['callee'], name='voicecall_callee_idx'),
            models.Index(fields=['order'], name='voicecall_order_idx'),
            models.Index(fields=['created_at'], name='voicecall_created_idx'),
        ]

    def __str__(self):
        return f'{self.call_type} #{self.id} {self.status}'


class CallRecording(models.Model):
    class RecordingStatus(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not started'
        RECORDING = 'recording', 'Recording'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class TranscriptStatus(models.TextChoices):
        NOT_REQUESTED = 'not_requested', 'Not requested'
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    call = models.OneToOneField(
        VoiceCallSession,
        on_delete=models.CASCADE,
        related_name='recording',
    )
    recording_url = models.URLField(blank=True)
    recording_status = models.CharField(
        max_length=20,
        choices=RecordingStatus.choices,
        default=RecordingStatus.NOT_STARTED,
    )
    transcript_text = models.TextField(blank=True)
    transcript_status = models.CharField(
        max_length=20,
        choices=TranscriptStatus.choices,
        default=TranscriptStatus.NOT_REQUESTED,
    )
    agora_resource_id = models.CharField(max_length=128, blank=True)
    agora_sid = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Call Recording'
        verbose_name_plural = 'Call Recordings'


class SupportAgentDuty(models.Model):
    """Admin on-duty flag for accepting support voice calls."""

    admin = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='support_agent_duty',
    )
    is_on_duty = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Support Agent Duty'
        verbose_name_plural = 'Support Agent Duties'

    def __str__(self):
        return f'{self.admin_id} on_duty={self.is_on_duty}'
