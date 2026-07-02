import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class VoiceCallConsumer(AsyncWebsocketConsumer):
    """
    Real-time voice call signaling for mobile apps and admin panel.

    Connect: wss://host/ws/voice-call/?token=<JWT>

    Events (server → client):
      - connection_established
      - incoming_call
      - call_accepted
      - call_rejected
      - call_cancelled
      - call_ended
      - incoming_support_call (admins on support duty group)
    """

    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close(code=4401)
            return

        self.user_group = f'voice_call_user_{self.user.id}'
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        if await self._is_admin():
            await self.channel_layer.group_add('voice_call_support_duty', self.channel_name)

        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'connection_established',
                    'message': 'Connected to voice call signaling',
                    'user_id': self.user.id,
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, 'user') and not self.user.is_anonymous and await self._is_admin():
            await self.channel_layer.group_discard('voice_call_support_duty', self.channel_name)

    async def receive(self, text_data):
        # Signaling is REST-driven; WS is receive-only for clients.
        pass

    async def voice_call_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': event.get('event_type', 'voice_call_event'),
                    'payload': event.get('payload', {}),
                }
            )
        )

    @database_sync_to_async
    def _is_admin(self) -> bool:
        u = self.user
        return bool(u.is_superuser or u.is_staff)
