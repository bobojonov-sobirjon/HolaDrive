from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.chat.models import SupportRoom, SupportMessage
from apps.notification.models import Notification
from apps.notification.services import enqueue_push_to_user_id

logger = logging.getLogger(__name__)


def _is_admin(user) -> bool:
    return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


class SupportChatConsumer(AsyncWebsocketConsumer):
    """
    WS for support chat messages.

    URL: ws/support/<room_id>/
    Payload:
      - { "type": "chat_message", "message": "...", "order_id": 123? }
    """

    async def connect(self):
        try:
            room_id_str = self.scope['url_route']['kwargs'].get('room_id')
            self.user = self.scope['user']
            if self.user.is_anonymous:
                await self.close()
                return
            try:
                self.room_id = int(room_id_str)
            except Exception:
                await self.close()
                return

            room = await self.get_room(self.room_id)
            if not room:
                await self.close()
                return
            if not await self.has_access(room):
                await self.close()
                return

            self.room_group_name = f'support_room_{self.room_id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            await self.send(
                text_data=json.dumps(
                    {
                        'type': 'connection_established',
                        'message': 'Connected to support chat',
                        'room_id': self.room_id,
                    }
                )
            )
        except Exception:
            logger.exception('SupportChatConsumer connect failed')
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data or '{}')
        except Exception:
            payload = {}

        msg_type = payload.get('type') or 'chat_message'
        if msg_type != 'chat_message':
            return

        message = (payload.get('message') or '').strip()
        if not message:
            return

        order_id = payload.get('order_id')
        try:
            order_id = int(order_id) if order_id is not None else None
        except Exception:
            order_id = None

        message_data = await self._save_message(message, order_id=order_id)
        if not message_data:
            return

        # Send notification to the other participant (push + ws/notifications/)
        await self._notify_other_party(message=message, order_id=order_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                **message_data,
            },
        )

    async def chat_message(self, event):
        # Send back as-is; mobile can rely on sender_type + order_id
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_room(self, room_id: int):
        try:
            return SupportRoom.objects.select_related('user', 'admin').get(pk=room_id)
        except Exception:
            return None

    @database_sync_to_async
    def has_access(self, room: SupportRoom) -> bool:
        if room.user_id == self.user.id:
            return True
        if _is_admin(self.user) and room.admin_id == self.user.id:
            return True
        return False

    @database_sync_to_async
    def _save_message(self, message: str, *, order_id: int | None):
        try:
            room = SupportRoom.objects.get(pk=self.room_id)
            is_admin = _is_admin(self.user)

            order_obj = None
            if order_id:
                from apps.order.models import Order

                order_obj = Order.objects.filter(pk=order_id).first()
                if order_obj and not room.orders.filter(pk=order_obj.pk).exists():
                    room.orders.add(order_obj)
                    SupportMessage.objects.create(
                        room=room,
                        sender=self.user,
                        message_type=SupportMessage.MessageType.SYSTEM,
                        message=f'Chat context switched to order #{order_obj.id}.',
                        order=order_obj,
                    )

            mtype = SupportMessage.MessageType.ADMIN if is_admin else SupportMessage.MessageType.USER
            msg = SupportMessage.objects.create(
                room=room,
                sender=self.user,
                message_type=mtype,
                message=message,
                order=order_obj,
            )

            return {
                'type': 'chat_message',
                'message_id': msg.id,
                'message_type': msg.message_type,
                'message': msg.message,
                'order_id': msg.order_id,
                'sender_id': self.user.id,
                'sender_name': self.user.get_full_name() or getattr(self.user, 'username', None) or self.user.email,
                'sender_type': 'admin' if is_admin else 'user',
                'created_at': msg.created_at.isoformat(),
            }
        except Exception:
            logger.exception('SupportChatConsumer save failed')
            return None

    async def _notify_other_party(self, *, message: str, order_id: int | None):
        await database_sync_to_async(self.__notify_other_party)(message=message, order_id=order_id)

    def __notify_other_party(self, *, message: str, order_id: int | None):
        try:
            room = SupportRoom.objects.select_related('user', 'admin').get(pk=self.room_id)
            is_admin = _is_admin(self.user)
            recipient = room.user if is_admin else room.admin
            if not recipient:
                return

            title = 'New support message'
            body = (message[:120] + '…') if len(message) > 120 else message
            n = Notification.objects.create(
                user=recipient,
                notification_type=Notification.NotificationType.CHAT_MESSAGE,
                title=title,
                message=body,
                related_object_type='support_room',
                related_object_id=room.id,
                data={
                    'support_room_id': room.id,
                    'order_id': order_id,
                    'sender_id': self.user.id,
                },
            )

            enqueue_push_to_user_id(recipient.id, title=title, body=body, data=n.data or {})

            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            payload = {
                'id': n.id,
                'user_id': n.user_id,
                'title': n.title,
                'message': n.message,
                'notification_type': n.notification_type,
                'related_object_type': n.related_object_type,
                'related_object_id': n.related_object_id,
                'data': n.data,
                'created_at': n.created_at.isoformat() if n.created_at else None,
                'status': n.status,
            }
            async_to_sync(channel_layer.group_send)(
                f'notifications_{n.user_id}',
                {'type': 'notification', 'notification': payload},
            )
        except Exception:
            logger.exception('SupportChatConsumer notify failed')
            return

