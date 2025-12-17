from django.contrib import admin
from django.urls import path
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django import forms
from .models import Conversation, Message
from .admin_views import chat_interface, send_message_api, get_messages_api


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'status', 'subject', 'chat_button')
    list_filter = ('status', 'user_type', 'created_at')
    search_fields = ('user__email', 'user__username', 'subject')
    readonly_fields = ('created_at', 'updated_at', 'last_message_at')
    ordering = ('-last_message_at', '-created_at')
    change_list_template = 'admin/chat/conversation/change_list.html'
    
    # CharField va TextField uchun kengaytirilgan ko'rinish
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 4, 'cols': 80, 'style': 'width: 100%; min-width: 500px;'}),
        },
    }
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_type')
        }),
        ('Conversation Information', {
            'fields': ('status', 'subject')
        }),
        ('Unread Counts', {
            'fields': ('unread_count_support', 'unread_count_user')
        }),
        ('Timestamps', {
            'fields': ('last_message_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def chat_button(self, obj):
        """
        Add chat button to list display - opens modal
        """
        if obj:
            return format_html(
                '<button class="button" onclick="event.stopPropagation(); event.preventDefault(); openChatModal({}); return false;" style="cursor: pointer; border: none; background: #417690; color: white; padding: 8px 16px; border-radius: 4px;">💬 Chat</button>',
                obj.id
            )
        return "-"
    chat_button.short_description = 'Chat'
    chat_button.allow_tags = True
    
    def get_urls(self):
        """
        Add custom URLs for chat interface
        """
        urls = super().get_urls()
        custom_urls = [
            path('<int:conversation_id>/chat/', self.admin_site.admin_view(chat_interface), name='chat_conversation_chat'),
            path('<int:conversation_id>/chat/send/', self.admin_site.admin_view(send_message_api), name='chat_conversation_send'),
            path('<int:conversation_id>/chat/messages/', self.admin_site.admin_view(get_messages_api), name='chat_conversation_messages'),
        ]
        return custom_urls + urls
    


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'message_preview', 'is_from_support', 'is_read_by_support', 'is_read_by_user', 'created_at')
    list_filter = ('is_from_support', 'is_read_by_support', 'is_read_by_user', 'created_at')
    search_fields = ('conversation__user__email', 'conversation__user__username', 'message', 'sender__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    # CharField va TextField uchun kengaytirilgan ko'rinish
    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'style': 'width: 100%; min-width: 300px;'}),
        },
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 4, 'cols': 80, 'style': 'width: 100%; min-width: 500px;'}),
        },
    }
    
    fieldsets = (
        ('Conversation and Sender', {
            'fields': ('conversation', 'sender', 'is_from_support')
        }),
        ('Message Content', {
            'fields': ('message', 'attachment')
        }),
        ('Read Status', {
            'fields': ('is_read_by_support', 'is_read_by_user')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def message_preview(self, obj):
        if obj.message:
            return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
        return "-"
    message_preview.short_description = 'Message Preview'
