from django.contrib import admin

from .models import ChatMessage, ChatRoom, SupportMessage, SupportRoom


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


@admin.register(SupportRoom)
class SupportRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'admin', 'created_at', 'updated_at')
    search_fields = ('user__email', 'admin__email', 'user__username', 'admin__username')
    raw_id_fields = ('user', 'admin')
    filter_horizontal = ('orders',)


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'message_type', 'sender', 'order', 'created_at')
    search_fields = ('message', 'sender__email')
    raw_id_fields = ('room', 'sender', 'order')
    list_filter = ('message_type',)
