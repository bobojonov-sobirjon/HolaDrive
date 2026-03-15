import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import Group

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

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
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

    @database_sync_to_async
    def _check_driver_role(self, user):
        return user.groups.filter(name='Driver').exists()

    @database_sync_to_async
    def _get_current_orders(self):
        from apps.order.services.driver_orders_websocket import get_driver_current_orders
        return get_driver_current_orders(self.user)


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
