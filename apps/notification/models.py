from django.db import models
from apps.accounts.models import CustomUser


class Notification(models.Model):
    """
    Notification model for real-time notifications
    """
    class NotificationType(models.TextChoices):
        CHAT_MESSAGE = 'chat_message', 'Chat Message'
        ORDER_UPDATE = 'order_update', 'Order Update'
        SYSTEM = 'system', 'System'
        PROMOTION = 'promotion', 'Promotion'
        OTHER = 'other', 'Other'
    
    class NotificationStatus(models.TextChoices):
        UNREAD = 'unread', 'Unread'
        READ = 'read', 'Read'
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='User',
        help_text='User who will receive this notification'
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.OTHER,
        verbose_name='Notification Type'
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name='Title',
        help_text='Notification title'
    )
    
    message = models.TextField(
        verbose_name='Message',
        help_text='Notification message content'
    )
    
    status = models.CharField(
        max_length=10,
        choices=NotificationStatus.choices,
        default=NotificationStatus.UNREAD,
        verbose_name='Status'
    )
    
    related_object_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Related Object Type',
        help_text='Type of related object (e.g., "order", "conversation")'
    )
    
    related_object_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Related Object ID',
        help_text='ID of related object'
    )
    
    data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Data',
        help_text='Additional data in JSON format'
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Read At',
        help_text='Timestamp when notification was read'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    objects = models.Manager()
    
    def __str__(self):
        if self.user:
            user_name = self.user.get_full_name() or self.user.username
        else:
            user_name = "Unknown"
        status = self.status or "Unknown"
        return f"{user_name} - {self.title} - {status}"
    
    def mark_as_read(self):
        """
        Mark notification as read
        """
        from django.utils import timezone
        self.status = self.NotificationStatus.READ
        self.read_at = timezone.now()
        self.save()
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = '01 Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='notification_user_idx'),
            models.Index(fields=['status'], name='notification_status_idx'),
            models.Index(fields=['notification_type'], name='notification_type_idx'),
            models.Index(fields=['user', 'status'], name='notification_user_status_idx'),
            models.Index(fields=['created_at'], name='notification_created_idx'),
        ]
