import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatMessage

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat
    """
    
    async def connect(self):
        """
        Connect to WebSocket and join conversation room
        """
        try:
            room_id_str = self.scope['url_route']['kwargs'].get('conversation_id') or self.scope['url_route']['kwargs'].get('room_id')
            try:
                self.room_id = int(room_id_str)
            except (ValueError, TypeError):
                await self.close()
                return
            self.room_group_name = f'chat_room_{self.room_id}'
            self.user = self.scope['user']
            if self.user.is_anonymous:
                await self.close()
                return
            room = await self.get_room(self.room_id)
            if not room:
                await self.close()
                return
            if not await self.has_access(room):
                await self.close()
                return
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to chat',
                'room_id': self.room_id
            }))
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """
        Leave room group
        """
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        print(f"📨 WebSocket receive called with data: {text_data}")
        print(f"📨 Room ID: {getattr(self, 'room_id', 'NOT SET')}")
        print(f"📨 Room group: {getattr(self, 'room_group_name', 'NOT SET')}")
        print(f"📨 User: {getattr(self, 'user', 'NOT SET')}")
        
        try:
            try:
                text_data_json = json.loads(text_data)
                print(f"📨 Parsed JSON: {text_data_json}")
                message_type = text_data_json.get('type', 'chat_message')
                print(f"📨 Message type: {message_type}")
                
                if message_type == 'chat_message':
                    message = text_data_json.get('message', '')
                    file_base64 = text_data_json.get('file_base64', None)
                    file_name = text_data_json.get('file_name', None)
                    file_type = text_data_json.get('file_type', None)
                    
                    print(f"📨 Chat message received: message='{message}', has_file={bool(file_base64)}")
                    
                    if message:
                        print(f"📨 Saving text message...")
                        await self.save_message(message)
                    else:
                        print(f"⚠️ Empty message, not saving")
                elif message_type == 'typing':
                    print(f"📨 Typing indicator received")
                    await self.handle_typing(text_data_json)
                elif message_type == 'read_message':
                    message_id = text_data_json.get('message_id')
                    print(f"📨 Read message request for ID: {message_id}")
                    await self.mark_message_as_read(message_id)
                else:
                    print(f"⚠️ Unknown message type: {message_type}")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON decode error: {e}, treating as plain text")
                if text_data and text_data.strip():
                    print(f"📨 Saving as plain text message...")
                    await self.save_message(text_data.strip())
        except Exception as e:
            print(f"❌ Error in receive: {e}")
            import traceback
            traceback.print_exc()
    
    async def chat_message(self, event):
        """
        Send message to WebSocket. Response format: initiator fields (message, created_at, sender_type)
        and sender as a separate object. No message_id, attachment, file_* in response.
        """
        try:
            is_from_support = event.get('is_from_support', False)
            sender_id = event.get('sender_id', event.get('sender'))
            message_payload = {
                'type': 'chat_message',
                'message': event.get('message', ''),
                'created_at': event.get('created_at', ''),
                'sender_type': 'support' if is_from_support else 'initiator',
                'sender': {
                    'id': sender_id,
                    'name': event.get('sender_name', 'Unknown'),
                    'is_from_support': is_from_support,
                },
            }
            await self.send(text_data=json.dumps(message_payload))
        except Exception as e:
            print(f"❌ Error sending message to WebSocket: {e}")
            import traceback
            traceback.print_exc()
    
    async def typing_indicator(self, event):
        """
        Send typing indicator
        """
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user': event['user'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing']
        }))
    
    async def message_read(self, event):
        """
        Send message read confirmation
        """
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'read_by': event['read_by']
        }))
    
    @database_sync_to_async
    def get_room(self, room_id):
        try:
            return ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def has_access(self, room):
        if room.initiator_id == self.user.id:
            return True
        if room.receiver_id and room.receiver_id == self.user.id:
            return True
        return False
    
    async def save_message(self, message_text):
        """
        Save message to database and send to room group
        """
        try:
            message_data = await self._save_message_to_db(message_text)
            if message_data and self.channel_layer:
                event_data = {
                    'type': 'chat_message',
                    'message': message_data['message_text'],
                    'sender': message_data['sender_id'],
                    'sender_id': message_data['sender_id'],
                    'sender_name': message_data['sender_name'],
                    'is_from_support': message_data.get('is_from_support', False),
                    'created_at': message_data['created_at'],
                    'message_id': message_data['message_id'],
                    'attachment': message_data.get('attachment_url'),
                    'attachment_url': message_data.get('attachment_url'),
                    'file_type': message_data.get('file_type'),
                    'file_name': message_data.get('file_name')
                }
                await self.channel_layer.group_send(self.room_group_name, event_data)
        except Exception as e:
            print(f"❌ Error saving message: {e}")
            import traceback
            traceback.print_exc()
    
    async def save_message_with_file(self, message_text, file_base64, file_name, file_type):
        """
        Save message with file attachment to database and send to room group
        """
        try:
            message_data = await self._save_message_with_file_to_db(message_text, file_base64, file_name, file_type)
            
            if message_data:
                print(f"Sending message with file to room group: {self.room_group_name}")
                print(f"Message data: {message_data}")
                try:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_data['message_text'],
                            'sender': message_data['sender_id'],
                            'sender_id': message_data['sender_id'],
                            'sender_name': message_data['sender_name'],
                            'is_from_support': message_data['is_from_support'],
                            'created_at': message_data['created_at'],
                            'message_id': message_data['message_id'],
                            'attachment': message_data.get('attachment_url'),
                            'attachment_url': message_data.get('attachment_url'),
                            'file_type': message_data.get('file_type'),
                            'file_name': message_data.get('file_name')
                        }
                    )
                    print(f"Message with file sent to room group successfully")
                    
                    if '_pending_notification' in message_data and message_data['_pending_notification']:
                        notification = message_data['_pending_notification']
                        user_id = notification.user.id
                        await self.send_notification_via_websocket(user_id, notification)
                        print(f"Notification sent via WebSocket to user {user_id}")
                except Exception as e:
                    print(f"Error sending to room group: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"Error saving message with file: {e}")
            import traceback
            traceback.print_exc()
    
    @database_sync_to_async
    def _save_message_to_db(self, message_text):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            message = ChatMessage.objects.create(
                room=room,
                sender=self.user,
                message=message_text,
            )
            room.save(update_fields=['updated_at'])
            sender_name = self.user.get_full_name() or getattr(self.user, 'username', None) or self.user.email
            return {
                'message_text': message_text,
                'sender_id': self.user.id,
                'sender_name': sender_name or 'Unknown',
                'is_from_support': False,
                'created_at': message.created_at.isoformat(),
                'message_id': message.id,
                'attachment_url': None,
                'file_type': None,
                'file_name': None,
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None
    
    @database_sync_to_async
    def _save_message_with_file_to_db(self, message_text, file_base64, file_name, file_type):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            message = ChatMessage.objects.create(
                room=room,
                sender=self.user,
                message=message_text or '',
            )
            room.save(update_fields=['updated_at'])
            sender_name = self.user.get_full_name() or getattr(self.user, 'username', None) or self.user.email
            return {
                'message_text': message_text or '',
                'sender_id': self.user.id,
                'sender_name': sender_name or 'Unknown',
                'is_from_support': False,
                'created_at': message.created_at.isoformat(),
                'message_id': message.id,
                'attachment_url': None,
                'file_type': None,
                'file_name': None,
            }
        except Exception:
            return None

    async def send_notification_via_websocket(self, user_id, notification):
        """
        Send notification via WebSocket to user
        """
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            notification_data = {
                'id': notification.id,
                'user_id': user_id,  # Add user_id to verify in NotificationConsumer
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'related_object_type': notification.related_object_type,
                'related_object_id': notification.related_object_id,
                'data': notification.data,
                'created_at': notification.created_at.isoformat(),
                'status': notification.status
            }
            try:
                await channel_layer.group_send(
                    f'notifications_{user_id}',
                    {
                        'type': 'notification',
                        'notification': notification_data
                    }
                )
                print(f"Notification sent to group 'notifications_{user_id}' successfully")
            except Exception as e:
                print(f"Error sending notification to WebSocket: {e}")
                import traceback
                traceback.print_exc()
    
    @database_sync_to_async
    def handle_typing(self, data):
        """
        Handle typing indicator
        """
        is_typing = data.get('is_typing', False)
        user_name = self.user.get_full_name() or self.user.username
        
        self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': self.user.id,
                'user_name': user_name,
                'is_typing': is_typing
            }
        )
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        pass


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications
    """
    
    async def connect(self):
        """
        Connect to WebSocket for notifications
        User is extracted from JWT token by middleware, no need for user_id in path
        """
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            print(f"WebSocket REJECT: User is anonymous for notifications")
            await self.close()
            return
        
        self.user_id = self.user.id
        self.room_group_name = f'notifications_{self.user_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notifications',
            'user_id': str(self.user_id)
        }))
    
    async def disconnect(self, close_code):
        """
        Leave room group
        """
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', '')
            
            if message_type == 'mark_as_read':
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_as_read(notification_id)
        except json.JSONDecodeError:
            pass
    
    async def notification(self, event):
        """
        Send notification to WebSocket
        Only send if notification is for this user
        """
        notification_data = event.get('notification', {})
        
        # Verify that notification is for this user
        # Check if notification has user_id field or if we need to verify from database
        notification_user_id = notification_data.get('user_id')
        if notification_user_id:
            # Convert to int for comparison
            try:
                notification_user_id = int(notification_user_id)
                if notification_user_id != self.user_id:
                    print(f"⚠️ NotificationConsumer: Skipping notification {notification_data.get('id')} - not for user {self.user_id} (notification is for user {notification_user_id})")
                    return
            except (ValueError, TypeError):
                pass
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification_data
        }))
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """
        Mark notification as read
        """
        try:
            notification = Notification.objects.get(id=notification_id, user=self.user)
            notification.mark_as_read()
        except Notification.DoesNotExist:
            pass

