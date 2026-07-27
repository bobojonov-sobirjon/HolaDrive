from django.contrib import admin

from .models import SafetyMessage, SafetyRoom, TripShareLink, TripVoiceRecording


@admin.register(TripShareLink)
class TripShareLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'created_by', 'token', 'is_active', 'expires_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('token', 'order__order_code', 'created_by__email')
    readonly_fields = ('token', 'created_at', 'updated_at')


class SafetyMessageInline(admin.TabularInline):
    model = SafetyMessage
    extra = 0
    readonly_fields = ('sender', 'message_type', 'message', 'order', 'created_at')


@admin.register(SafetyRoom)
class SafetyRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'agent', 'created_at', 'updated_at')
    search_fields = ('user__email', 'agent__email')
    filter_horizontal = ('orders',)
    inlines = [SafetyMessageInline]


@admin.register(TripVoiceRecording)
class TripVoiceRecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'status', 'duration_seconds', 'started_at', 'ended_at')
    list_filter = ('status',)
    search_fields = ('order__order_code', 'user__email')
