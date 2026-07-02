from django.contrib import admin

from .models import CallRecording, SupportAgentDuty, VoiceCallSession


@admin.register(VoiceCallSession)
class VoiceCallSessionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'call_type',
        'status',
        'caller',
        'callee',
        'order',
        'duration_seconds',
        'created_at',
    )
    list_filter = ('call_type', 'status')
    search_fields = ('agora_channel_name', 'caller__email', 'callee__email')
    readonly_fields = ('created_at', 'updated_at', 'ring_started_at')


@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ('call', 'recording_status', 'transcript_status', 'updated_at')


@admin.register(SupportAgentDuty)
class SupportAgentDutyAdmin(admin.ModelAdmin):
    list_display = ('admin', 'is_on_duty', 'updated_at')
