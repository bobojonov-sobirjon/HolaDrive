import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class DriverOrdersConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            logger.info(
                "[WS driver/orders] Reject: anonymous (no valid token)",
            )
            await self.close(code=4401)
            return

        is_driver = await self._check_driver_role(self.user)
        if not is_driver:
            logger.info(
                "[WS driver/orders] Reject: user id=%s not in Driver group",
                getattr(self.user, "id", None),
            )
            await self.close(code=4403)
            return

        logger.info(
            "[WS driver/orders] Accept: user_id=%s",
            self.user.id,
        )

        self.driver_id = self.user.id
        self.room_group_name = f'driver_orders_{self.driver_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to driver orders',
            'driver_id': self.driver_id
        }))

        orders_data = await self._get_current_orders()
        await self.send(text_data=json.dumps({
            'type': 'initial_orders',
            'orders': orders_data,
            'message': 'Current pending orders'
        }))
        await self._schedule_active_ride_snapshot_once('driver')

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Driver orders socket hozircha faqat health check uchun ishlatiladi.
        Surge/heatmap alohida DriverSurgeZonesConsumer orqali ishlaydi.
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            if msg_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def new_order(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order': event.get('order', {}),
            'message': event.get('message', 'New ride request available')
        }))

    async def order_timeout(self, event):
        await self.send(text_data=json.dumps({
            'type': 'order_timeout',
            'order_id': event.get('order_id'),
            'message': event.get('message', 'Order expired or reassigned to another driver')
        }))

    async def order_cancelled_by_rider(self, event):
        await self.send(text_data=json.dumps({
            'type': 'order_cancelled_by_rider',
            'change': event.get('change', 'cancelled_rider'),
            'message': event.get('message', 'The rider cancelled this ride.'),
            'order': event.get('order', {}),
            'cancel': event.get('cancel'),
        }))

    async def active_ride_snapshot(self, event):
        await self.send(text_data=json.dumps({
            'type': 'active_ride_snapshot',
            'scope': event.get('scope', 'driver'),
            'has_active_ride': event.get('has_active_ride', False),
            'order': event.get('order'),
            'checked_at': event.get('checked_at'),
            'message': event.get('message', 'Active ride status refreshed'),
        }))

    @database_sync_to_async
    def _check_driver_role(self, user):
        return user.groups.filter(name='Driver').exists()

    @database_sync_to_async
    def _get_current_orders(self):
        from apps.order.services.driver_orders_websocket import get_driver_current_orders
        return get_driver_current_orders(self.user)

    @database_sync_to_async
    def _schedule_active_ride_snapshot_once(self, scope: str):
        from apps.order.tasks import send_active_ride_snapshot_once
        send_active_ride_snapshot_once.apply_async(
            kwargs={'user_id': self.user.id, 'scope': scope},
            countdown=3,
        )


class RiderOrdersConsumer(AsyncWebsocketConsumer):
    """
    WebSocket for riders: active trips + real-time driver accept/reject updates.
    Group: rider_orders_<user_id>
    """

    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            logger.info('[WS rider/orders] Reject: anonymous')
            await self.close(code=4401)
            return

        is_rider = await self._check_rider_role(self.user)
        if not is_rider:
            logger.info(
                '[WS rider/orders] Reject: user id=%s not in Rider group',
                getattr(self.user, 'id', None),
            )
            await self.close(code=4403)
            return

        self.rider_id = self.user.id
        self.room_group_name = f'rider_orders_{self.rider_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to rider orders',
            'rider_id': self.rider_id,
        }))

        orders_data = await self._get_active_orders()
        await self.send(text_data=json.dumps({
            'type': 'initial_orders',
            'orders': orders_data,
            'message': 'Your active orders',
        }))
        await self._schedule_active_ride_snapshot_once('rider')

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def rider_order_accepted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'rider_order_accepted',
            'order': event.get('order', {}),
            'message': event.get('message', ''),
        }))

    async def rider_driver_rejected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'rider_driver_rejected',
            'order': event.get('order', {}),
            'rejected_driver_id': event.get('rejected_driver_id'),
            'reassigned': event.get('reassigned', False),
            'message': event.get('message', ''),
        }))

    async def rider_order_updated(self, event):
        """Full order snapshot on any lifecycle change (listen for this in Flutter)."""
        payload = {
            'type': 'rider_order_updated',
            'change': event.get('change'),
            'order': event.get('order', {}),
            'message': event.get('message', ''),
        }
        if 'rejected_driver_id' in event:
            payload['rejected_driver_id'] = event['rejected_driver_id']
        if 'reassigned' in event:
            payload['reassigned'] = event['reassigned']
        await self.send(text_data=json.dumps(payload))

    async def active_ride_snapshot(self, event):
        await self.send(text_data=json.dumps({
            'type': 'active_ride_snapshot',
            'scope': event.get('scope', 'rider'),
            'has_active_ride': event.get('has_active_ride', False),
            'order': event.get('order'),
            'checked_at': event.get('checked_at'),
            'message': event.get('message', 'Active ride status refreshed'),
        }))

    @database_sync_to_async
    def _check_rider_role(self, user):
        return user.groups.filter(name='Rider').exists()

    @database_sync_to_async
    def _get_active_orders(self):
        from apps.order.services.rider_orders_websocket import get_rider_active_orders
        return get_rider_active_orders(self.user)

    @database_sync_to_async
    def _schedule_active_ride_snapshot_once(self, scope: str):
        from apps.order.tasks import send_active_ride_snapshot_once
        send_active_ride_snapshot_once.apply_async(
            kwargs={'user_id': self.user.id, 'scope': scope},
            countdown=3,
        )


class DriverSurgeZonesConsumer(AsyncWebsocketConsumer):
    """
    WebSocket: driverlar uchun gavjum zonalar (surge zones).
    Ulangan zahoti aktiv zonalar yuboriladi, keyin signal orqali yangilanishlar push qilinadi.
    """

    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            logger.info("[WS driver/surge-zones] Reject: anonymous")
            await self.close(code=4401)
            return

        is_driver = await self._check_driver_role(self.user)
        if not is_driver:
            logger.info(
                "[WS driver/surge-zones] Reject: user id=%s not in Driver group",
                getattr(self.user, "id", None),
            )
            await self.close(code=4403)
            return

        self.group_name = "driver_surge_zones"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        # Ulangan zahoti joriy zonalarni yuborish
        zones = await self._get_surge_zones()
        await self.send(text_data=json.dumps({
            "type": "surge_zones",
            "zones": zones,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def receive(self, text_data):
        """
        Hozircha faqat ping/pong va qo'lda refresh qo'llab-quvvatlanadi.
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            if msg_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
            elif msg_type == "refresh":
                zones = await self._get_surge_zones()
                await self.send(text_data=json.dumps({
                    "type": "surge_zones",
                    "zones": zones,
                }))
        except json.JSONDecodeError:
            pass

    async def surge_zones_update(self, event):
        """
        Signals orqali keladigan yangilanishlar.
        """
        zones = event.get("zones", [])
        await self.send(text_data=json.dumps({
            "type": "surge_zones",
            "zones": zones,
        }))

    @database_sync_to_async
    def _check_driver_role(self, user):
        return user.groups.filter(name="Driver").exists()

    @database_sync_to_async
    def _get_surge_zones(self):
        """
        Barcha active SurgePricing zonalarni oddiy dict sifatida qaytaradi.
        """
        from apps.order.models import SurgePricing

        zones = SurgePricing.objects.filter(is_active=True).order_by("-priority", "name")
        result = []
        for z in zones:
            result.append({
                "id": z.id,
                "name": z.name,
                "zone_name": z.zone_name,
                "latitude": float(z.latitude) if z.latitude is not None else None,
                "longitude": float(z.longitude) if z.longitude is not None else None,
                "radius_km": float(z.radius_km) if z.radius_km is not None else None,
                "multiplier": float(z.multiplier) if z.multiplier is not None else 1.0,
                "start_time": str(z.start_time) if z.start_time else None,
                "end_time": str(z.end_time) if z.end_time else None,
                "days_of_week": z.days_of_week or [],
            })
        return result


class OrderTrackingConsumer(AsyncWebsocketConsumer):
    """
    Real-time location stream for one order.
    Group: order_tracking_<order_id>
    """

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close(code=4401)
            return

        try:
            self.order_id = int(self.scope["url_route"]["kwargs"]["order_id"])
        except (ValueError, TypeError, KeyError):
            await self.close(code=4400)
            return

        allowed = await self._has_access(self.user.id, self.order_id)
        if not allowed:
            await self.close(code=4403)
            return

        self.group_name = f"order_tracking_{self.order_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "Connected to order tracking",
            "order_id": self.order_id,
        }))

        initial_payload = await self._initial_driver_location(self.order_id)
        if initial_payload:
            await self.send(text_data=json.dumps({
                "type": "driver_location_update",
                **initial_payload,
            }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
            if payload.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def driver_location_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "driver_location_update",
            "order_id": event.get("order_id"),
            "driver_id": event.get("driver_id"),
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "updated_at": event.get("updated_at"),
            "eta_minutes": event.get("eta_minutes"),
            "eta_to_pickup_minutes": event.get("eta_to_pickup_minutes"),
            "eta_to_destination_minutes": event.get("eta_to_destination_minutes"),
            "tracking_phase": event.get("tracking_phase"),
        }))

    @database_sync_to_async
    def _has_access(self, user_id: int, order_id: int):
        from .models import Order, OrderDriver

        order = Order.objects.filter(id=order_id).only("id", "user_id").first()
        if not order:
            return False
        if order.user_id == user_id:
            return True
        return OrderDriver.objects.filter(
            order_id=order_id,
            driver_id=user_id,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        ).exists()

    @database_sync_to_async
    def _initial_driver_location(self, order_id: int):
        from .services.order_tracking_websocket import get_initial_tracking_payload

        return get_initial_tracking_payload(order_id)


class OrderChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        try:
            order_id_str = self.scope['url_route']['kwargs']['order_id']
            
            try:
                self.order_id = int(order_id_str)
            except (ValueError, TypeError):
                await self.close()
                return
            
            self.room_group_name = f'order_chat_{self.order_id}'
            self.user = self.scope['user']
            
            if self.user.is_anonymous:
                await self.close()
                return
            
            chat = await self.get_chat()
            if not chat:
                await self.close()
                return
            
            self.chat = chat
            
            if not await self.has_access(chat):
                await self.close()
                return
            
            self.user_type = await self.get_user_type(chat)
            
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to order chat',
                'order_id': self.order_id,
                'user_type': self.user_type
            }))
        except Exception:
            await self.close()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                message = text_data_json.get('message', '')
                if message and message.strip():
                    await self.save_and_send_message(message.strip())
            elif message_type == 'typing':
                await self.handle_typing(text_data_json)
            elif message_type == 'read_messages':
                await self.mark_messages_as_read()
        except json.JSONDecodeError:
            if text_data and text_data.strip():
                await self.save_and_send_message(text_data.strip())
        except Exception:
            pass
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event.get('message_id'),
            'message': event.get('message'),
            'sender_id': event.get('sender_id'),
            'sender_name': event.get('sender_name'),
            'sender_type': event.get('sender_type'),
            'created_at': event.get('created_at'),
            'attachment_url': event.get('attachment_url'),
            'file_type': event.get('file_type'),
            'file_name': event.get('file_name'),
        }))
    
    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_type': event['user_type'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing']
        }))
    
    @database_sync_to_async
    def get_chat(self):
        from apps.chat.models import ChatRoom
        try:
            return ChatRoom.objects.select_related('initiator', 'receiver', 'order').get(order_id=self.order_id)
        except Exception:
            return None

    @database_sync_to_async
    def has_access(self, chat):
        return self.user == chat.initiator or (chat.receiver and self.user == chat.receiver)

    @database_sync_to_async
    def get_user_type(self, chat):
        if self.user == chat.initiator:
            return 'rider'
        if chat.receiver and self.user == chat.receiver:
            return 'driver'
        return None
    
    async def save_and_send_message(self, message_text):
        try:
            message_data = await self._save_message_to_db(message_text)
            
            if message_data:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message_id': message_data['message_id'],
                        'message': message_data['message'],
                        'sender_id': message_data['sender_id'],
                        'sender_name': message_data['sender_name'],
                        'sender_type': message_data['sender_type'],
                        'created_at': message_data['created_at'],
                        'attachment_url': message_data.get('attachment_url'),
                        'file_type': message_data.get('file_type'),
                        'file_name': message_data.get('file_name'),
                    }
                )
                
                await self._send_push_notification(message_data)
        except Exception:
            pass
    
    @database_sync_to_async
    def _save_message_to_db(self, message_text):
        from apps.chat.models import ChatRoom, ChatMessage
        try:
            room = ChatRoom.objects.get(order_id=self.order_id)
            sender_type = 'rider' if self.user == room.initiator else 'driver'
            message = ChatMessage.objects.create(
                room=room,
                sender=self.user,
                message=message_text,
            )
            room.save(update_fields=['updated_at'])
            sender_name = self.user.get_full_name() or getattr(self.user, 'username', None) or self.user.email
            receiver_id = room.receiver_id if sender_type == 'rider' else room.initiator_id
            return {
                'message_id': message.id,
                'message': message_text,
                'sender_id': self.user.id,
                'sender_name': sender_name or 'Unknown',
                'sender_type': sender_type,
                'created_at': message.created_at.isoformat(),
                'attachment_url': None,
                'file_type': None,
                'file_name': None,
                'receiver_id': receiver_id,
            }
        except Exception:
            return None
    
    async def _send_push_notification(self, message_data):
        try:
            from apps.notification.tasks import send_push_notification_async
            
            receiver_id = message_data.get('receiver_id')
            sender_name = message_data.get('sender_name')
            message_preview = message_data['message'][:50] + '...' if len(message_data['message']) > 50 else message_data['message']
            
            send_push_notification_async.delay(
                user_id=receiver_id,
                title=f"New message from {sender_name}",
                body=message_preview,
                data={
                    "type": "order_chat_message",
                    "order_id": self.order_id,
                    "message_id": message_data['message_id']
                }
            )
        except Exception:
            pass
    
    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        user_name = self.user.get_full_name() or self.user.username
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_type': self.user_type,
                'user_name': user_name,
                'is_typing': is_typing
            }
        )
    
    @database_sync_to_async
    def mark_messages_as_read(self):
        pass
