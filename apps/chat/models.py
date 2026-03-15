from django.db import models
from apps.accounts.models import CustomUser


class ChatRoom(models.Model):
    class RoomStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESS = 'process', 'Process'
        CANCEL = 'cancel', 'Cancel'
        COMPLETED = 'completed', 'Completed'

    order = models.ForeignKey(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='chat_rooms',
        verbose_name='Order',
    )
    initiator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_initiator',
        verbose_name='Initiator (Rider)',
    )
    receiver = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_receiver',
        verbose_name='Receiver (Driver)',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=RoomStatus.choices,
        default=RoomStatus.PENDING,
        verbose_name='Status',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        return f"ChatRoom order={self.order_id} initiator={self.initiator_id} status={self.status}"

    class Meta:
        verbose_name = 'Chat Room'
        verbose_name_plural = '01 Chat Rooms'
        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['order'], name='chatroom_order_idx'),
            models.Index(fields=['initiator'], name='chatroom_initiator_idx'),
            models.Index(fields=['receiver'], name='chatroom_receiver_idx'),
            models.Index(fields=['status'], name='chatroom_status_idx'),
        ]


class ChatMessage(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Chat Room',
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_messages_sent',
        verbose_name='Sender',
    )
    message = models.TextField(verbose_name='Message')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.sender_id}: {self.message[:30]}..."

    class Meta:
        verbose_name = 'Chat Message'
        verbose_name_plural = '02 Chat Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room'], name='chatmsg_room_idx'),
            models.Index(fields=['sender'], name='chatmsg_sender_idx'),
            models.Index(fields=['created_at'], name='chatmsg_created_idx'),
        ]
