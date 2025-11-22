from django.db import models
from apps.accounts.models import CustomUser


class Conversation(models.Model):
    """
    Conversation between Rider/Driver and Support
    Support is always the same (single support agent)
    """
    class ConversationStatus(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'
        PENDING = 'pending', 'Pending'
    
    class UserType(models.TextChoices):
        RIDER = 'rider', 'Rider'
        DRIVER = 'driver', 'Driver'
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name='User',
        help_text='Rider or Driver who started the conversation'
    )
    
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        verbose_name='User Type',
        help_text='Whether the user is a Rider or Driver'
    )
    
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.OPEN,
        verbose_name='Status'
    )
    
    subject = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Subject',
        help_text='Subject or title of the conversation'
    )
    
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Message At',
        help_text='Timestamp of the last message in this conversation'
    )
    
    unread_count_support = models.IntegerField(
        default=0,
        verbose_name='Unread Count (Support)',
        help_text='Number of unread messages for support'
    )
    
    unread_count_user = models.IntegerField(
        default=0,
        verbose_name='Unread Count (User)',
        help_text='Number of unread messages for user'
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
        return f"{user_name} - {status}"
    
    class Meta:
        verbose_name = 'Conversation'
        verbose_name_plural = '01 Conversations'
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['user'], name='conversation_user_idx'),
            models.Index(fields=['status'], name='conversation_status_idx'),
            models.Index(fields=['last_message_at'], name='conversation_last_msg_idx'),
            models.Index(fields=['user', 'status'], name='conversation_user_status_idx'),
        ]


class Message(models.Model):
    """
    Message in a conversation
    Can be sent by Rider, Driver, or Support
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Conversation'
    )
    
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
        verbose_name='Sender',
        help_text='User who sent the message'
    )
    
    message = models.TextField(
        verbose_name='Message',
        help_text='Message content'
    )
    
    is_read_by_support = models.BooleanField(
        default=False,
        verbose_name='Is Read By Support',
        help_text='Whether support has read this message'
    )
    
    is_read_by_user = models.BooleanField(
        default=False,
        verbose_name='Is Read By User',
        help_text='Whether user has read this message'
    )
    
    is_from_support = models.BooleanField(
        default=False,
        verbose_name='Is From Support',
        help_text='Whether this message is from support team'
    )
    
    attachment = models.FileField(
        upload_to='chat/attachments/',
        null=True,
        blank=True,
        verbose_name='Attachment',
        help_text='File attachment (image, document, audio, etc.)'
    )
    
    file_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ('image', 'Image'),
            ('file', 'File'),
            ('audio', 'Audio'),
        ],
        verbose_name='File Type',
        help_text='Type of file attachment'
    )
    
    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='File Name',
        help_text='Original name of the uploaded file'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    objects = models.Manager()
    
    def __str__(self):
        if self.sender:
            sender_name = self.sender.get_full_name() or self.sender.username
        else:
            sender_name = "Unknown"
        message_preview = self.message[:50] if self.message else ""
        return f"{sender_name}: {message_preview}"
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = '02 Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation'], name='message_conversation_idx'),
            models.Index(fields=['sender'], name='message_sender_idx'),
            models.Index(fields=['created_at'], name='message_created_idx'),
            models.Index(fields=['conversation', 'created_at'], name='message_conv_created_idx'),
            models.Index(fields=['is_read_by_support', 'is_read_by_user'], name='message_read_idx'),
        ]
