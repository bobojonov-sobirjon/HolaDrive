"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator
from channels.sessions import SessionMiddlewareStack
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import routing and middleware after Django setup
from config.routing import websocket_urlpatterns
from config.middleware.tokenauth_middleware import TokenAuthMiddleware

_ws_app = SessionMiddlewareStack(
    AuthMiddlewareStack(
        TokenAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    )
)
# In DEBUG, allow WebSocket without Origin header (Postman, mobile apps).
# AllowedHostsOriginValidator returns 403 when Origin is missing, so our middleware never runs.
if getattr(settings, "DEBUG", False):
    _ws_app = OriginValidator(_ws_app, ["*"])
else:
    _ws_app = AllowedHostsOriginValidator(_ws_app)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": _ws_app,
})
