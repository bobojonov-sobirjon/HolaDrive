"""
WebSocket URL routing for Django Channels
"""
from django.urls import re_path
from apps.chat import consumers
from apps.order import consumers as order_consumers

websocket_urlpatterns = [
    # Allow token in path after conversation_id (for mobile app compatibility)
    # Pattern matches: /ws/chat/1/ or /ws/chat/1/TOKEN or /ws/chat/1/token=TOKEN
    # Using non-greedy match to capture conversation_id correctly
    re_path(r'^ws/chat/(?P<conversation_id>\d+)(?:/.*)?/?$', consumers.ChatConsumer.as_asgi()),
    # Notifications path - user_id is extracted from JWT token, not from path
    # Pattern matches: /ws/notifications/ or /ws/notifications/TOKEN or /ws/notifications/?token=TOKEN
    re_path(r'^ws/notifications(?:/.*)?/?$', consumers.NotificationConsumer.as_asgi()),
    # Driver orders - real-time order updates (new order, order timeout)
    # Pattern: /ws/driver/orders/ or /ws/driver/orders/?token=TOKEN
    re_path(r'^ws/driver/orders(?:/.*)?/?$', order_consumers.DriverOrdersConsumer.as_asgi()),
]

