from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'status', 'created_at', 'read_at', 'chat_button')
    list_filter = ('notification_type', 'status', 'created_at')
    search_fields = ('user__email', 'user__username', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    ordering = ('-created_at',)
    change_list_template = 'admin/notification/change_list.html'
    
    def changelist_view(self, request, extra_context=None):
        """
        Override changelist_view to add websocket_url to context
        """
        extra_context = extra_context or {}
        extra_context['websocket_url'] = getattr(settings, 'WEBSOCKET_URL', f"{request.get_host()}")
        return super().changelist_view(request, extra_context=extra_context)
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Notification Content', {
            'fields': ('notification_type', 'title', 'message')
        }),
        ('Status', {
            'fields': ('status', 'read_at')
        }),
        ('Related Object', {
            'fields': ('related_object_type', 'related_object_id', 'data'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read']
    
    def chat_button(self, obj):
        """
        Add chat button for chat_message notifications
        """
        if obj and obj.notification_type == 'chat_message' and obj.related_object_type == 'conversation' and obj.related_object_id:
            return format_html(
                '<button class="button" onclick="event.stopPropagation(); event.preventDefault(); openChatModalFromNotification({}); return false;" style="cursor: pointer; border: none; background: #417690; color: white; padding: 8px 16px; border-radius: 4px;">💬 Open Chat</button>',
                obj.related_object_id
            )
        return "-"
    chat_button.short_description = 'Chat'
    chat_button.allow_tags = True
    
    def mark_as_read(self, request, queryset):
        """
        Mark selected notifications as read
        """
        from django.utils import timezone
        updated = queryset.filter(status='unread').update(
            status='read',
            read_at=timezone.now()
        )
        self.message_user(request, f'{updated} notification(s) marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
