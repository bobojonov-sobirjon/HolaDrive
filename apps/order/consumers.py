"""
WebSocket consumers for real-time order updates.
Driver connects to receive new order assignments and order timeout notifications.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import Group


class DriverOrdersConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for driver real-time order updates.
    - new_order: when a new order is assigned to this driver
    - order_timeout: when an order is removed (timeout/reassigned to another driver)
    """

    async def connect(self):
        """Connect - driver must be authenticated via JWT and be in Driver group."""
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        is_driver = await self._check_driver_role(self.user)
        if not is_driver:
            await self.close()
            return

        self.driver_id = self.user.id
        self.room_group_name = f'driver_orders_{self.driver_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to driver orders',
            'driver_id': self.driver_id
        }))

        # Avtomatik: hozirgi pending orderlarni yuborish
        orders_data = await self._get_current_orders()
        await self.send(text_data=json.dumps({
            'type': 'initial_orders',
            'orders': orders_data,
            'message': 'Current pending orders'
        }))

    async def disconnect(self, close_code):
        """Leave room group."""
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Optional: handle ping/pong for keepalive."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def new_order(self, event):
        """Send new order to driver."""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order': event.get('order', {}),
            'message': event.get('message', 'New ride request available')
        }))

    async def order_timeout(self, event):
        """Notify driver that order was removed (timeout/reassigned)."""
        await self.send(text_data=json.dumps({
            'type': 'order_timeout',
            'order_id': event.get('order_id'),
            'message': event.get('message', 'Order expired or reassigned to another driver')
        }))

    @database_sync_to_async
    def _check_driver_role(self, user):
        """Check if user is in Driver group."""
        return user.groups.filter(name='Driver').exists()

    @database_sync_to_async
    def _get_current_orders(self):
        """Get driver's current pending orders for initial send."""
        from apps.order.services.driver_orders_websocket import get_driver_current_orders
        return get_driver_current_orders(self.user)
