from __future__ import annotations

import json
import logging

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

from apps.notification.models import Notification
from apps.notification.services import enqueue_push_to_user_id
from apps.safety.models import SafetyMessage, SafetyRoom
from apps.safety.serializers import SafetyMessageSerializer
from apps.safety.services import get_valid_share_link

logger = logging.getLogger(__name__)


def _is_staff(user) -> bool:
    return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


class SafetyChatConsumer(AsyncWebsocketConsumer):
    """
    WS: ws/safety/<room_id>/?token=<JWT>
    Client → server: { "type": "chat_message", "message": "...", "order_id": ? }
    Server → client: { "type": "chat_message", "message": {...} }
    """

    async def connect(self):
        try:
            room_id_str = self.scope['url_route']['kwargs'].get('room_id')
            self.user = self.scope['user']
            if self.user.is_anonymous:
                await self.close(code=4401)
                return
            try:
                self.room_id = int(room_id_str)
            except Exception:
                await self.close(code=4400)
                return

            room = await self.get_room(self.room_id)
            if not room or not await self.has_access(room):
                await self.close(code=4403)
                return

            self.room_group_name = f'safety_room_{self.room_id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            await self.send(
                text_data=json.dumps(
                    {
                        'type': 'connection_established',
                        'message': 'Connected to safety chat',
                        'room_id': self.room_id,
                    }
                )
            )
        except Exception:
            logger.exception('SafetyChatConsumer connect failed')
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data or '{}')
        except Exception:
            payload = {}

        if (payload.get('type') or 'chat_message') != 'chat_message':
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

        await self._notify_other_party(message=message, order_id=order_id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'safety_chat_message', 'message': message_data},
        )

    async def safety_chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'chat_message',
                    'message': event.get('message'),
                }
            )
        )

    @database_sync_to_async
    def get_room(self, room_id: int):
        try:
            return SafetyRoom.objects.select_related('user', 'agent').get(pk=room_id)
        except SafetyRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def has_access(self, room: SafetyRoom) -> bool:
        u = self.user
        return bool(
            room.user_id == u.id or room.agent_id == u.id or _is_staff(u)
        )

    @database_sync_to_async
    def _save_message(self, message: str, order_id: int | None = None):
        try:
            room = SafetyRoom.objects.get(pk=self.room_id)
        except SafetyRoom.DoesNotExist:
            return None
        if not (
            room.user_id == self.user.id or room.agent_id == self.user.id or _is_staff(self.user)
        ):
            return None

        msg_type = (
            SafetyMessage.MessageType.AGENT
            if _is_staff(self.user)
            else SafetyMessage.MessageType.USER
        )
        order = None
        if order_id:
            from apps.order.models import Order

            order = Order.objects.filter(pk=order_id).first()
            if order and not room.orders.filter(pk=order.pk).exists():
                room.orders.add(order)

        msg = SafetyMessage.objects.create(
            room=room,
            sender=self.user,
            message_type=msg_type,
            message=message,
            order=order,
        )
        room.save(update_fields=['updated_at'])
        return SafetyMessageSerializer(msg).data

    @database_sync_to_async
    def _notify_other_party(self, message: str, order_id: int | None = None):
        try:
            room = SafetyRoom.objects.select_related('user', 'agent').get(pk=self.room_id)
        except SafetyRoom.DoesNotExist:
            return
        other_id = room.agent_id if self.user.id == room.user_id else room.user_id
        if not other_id:
            return
        title = 'Safety agent message' if _is_staff(self.user) else 'Safety chat'
        notif = Notification.objects.create(
            user_id=other_id,
            notification_type=Notification.NotificationType.SYSTEM,
            title=title,
            message=message[:200],
            related_object_type='safety_room',
            related_object_id=room.id,
            data={'room_id': room.id, 'order_id': order_id},
        )
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_{other_id}',
                    {
                        'type': 'notification',
                        'notification': {
                            'id': notif.id,
                            'title': notif.title,
                            'message': notif.message,
                            'related_object_type': notif.related_object_type,
                            'related_object_id': notif.related_object_id,
                            'data': notif.data,
                        },
                    },
                )
        except Exception:
            pass
        enqueue_push_to_user_id(other_id, title=title, body=message[:120], data={'room_id': str(room.id)})


class TripShareTrackingConsumer(AsyncWebsocketConsumer):
    """
    Public live tracking for share link viewers (no JWT).
    WS: ws/safety/share/<token>/
    Joins the same order_tracking_<order_id> group as rider/driver tracking.
    """

    async def connect(self):
        token = self.scope['url_route']['kwargs'].get('token')
        link = await self._get_link(token)
        if not link:
            await self.close(code=4403)
            return

        self.order_id = link['order_id']
        self.token = token
        self.group_name = f'order_tracking_{self.order_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'connection_established',
                    'message': 'Connected to shared trip tracking',
                    'order_id': self.order_id,
                    'token': self.token,
                }
            )
        )
        initial = await self._initial(self.order_id)
        if initial:
            await self.send(text_data=json.dumps({'type': 'driver_location_update', **initial}))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data or '{}')
            if payload.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except Exception:
            pass

    async def driver_location_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'driver_location_update',
                    'order_id': event.get('order_id'),
                    'driver_id': event.get('driver_id'),
                    'latitude': event.get('latitude'),
                    'longitude': event.get('longitude'),
                    'updated_at': event.get('updated_at'),
                    'eta_minutes': event.get('eta_minutes'),
                    'eta_to_pickup_minutes': event.get('eta_to_pickup_minutes'),
                    'eta_to_destination_minutes': event.get('eta_to_destination_minutes'),
                    'tracking_phase': event.get('tracking_phase'),
                }
            )
        )

    @database_sync_to_async
    def _get_link(self, token: str):
        try:
            link = get_valid_share_link(token)
            return {'order_id': link.order_id, 'token': link.token}
        except Exception:
            return None

    @database_sync_to_async
    def _initial(self, order_id: int):
        from apps.order.services.order_tracking_websocket import get_initial_tracking_payload

        return get_initial_tracking_payload(order_id)
