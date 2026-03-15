from django.contrib import admin
from .models import ChatRoom, ChatMessage


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'initiator', 'receiver', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__id', 'initiator__email', 'receiver__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at', '-created_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'message_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('room__order__id', 'sender__email', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def message_preview(self, obj):
        if obj.message:
            return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
        return "-"
    message_preview.short_description = 'Message'
