from django.contrib import admin

from .models import ChatMessage, ChatRoom


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'initiator', 'receiver', 'status', 'created_at')
    list_filter = ('status',)
    raw_id_fields = ('order', 'initiator', 'receiver')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'created_at')
    search_fields = ('message', 'sender__email')
    raw_id_fields = ('room', 'sender')
