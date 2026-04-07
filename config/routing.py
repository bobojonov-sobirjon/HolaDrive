from django.urls import re_path
from apps.chat import consumers
from apps.order import consumers as order_consumers

websocket_urlpatterns = [
    re_path(r"^ws/chat/(?P<conversation_id>\d+)(?:/.*)?/?$", consumers.ChatConsumer.as_asgi()),
    re_path(r"^ws/notifications(?:/.*)?/?$", consumers.NotificationConsumer.as_asgi()),
    re_path(r"^ws/driver/orders(?:/.*)?/?$", order_consumers.DriverOrdersConsumer.as_asgi()),
    # Alias: some clients use singular "order"; same consumer as /ws/driver/orders/
    re_path(r"^ws/driver/order(?:/.*)?/?$", order_consumers.DriverOrdersConsumer.as_asgi()),
    re_path(r"^ws/rider/orders(?:/.*)?/?$", order_consumers.RiderOrdersConsumer.as_asgi()),
    re_path(r"^ws/driver/surge-zones(?:/.*)?/?$", order_consumers.DriverSurgeZonesConsumer.as_asgi()),
    re_path(r"^ws/order/(?P<order_id>\d+)/chat(?:/.*)?/?$", order_consumers.OrderChatConsumer.as_asgi()),
]
