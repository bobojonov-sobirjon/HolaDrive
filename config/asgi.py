"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
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


class AllowMissingOriginValidator(OriginValidator):
    """
    Native apps and Postman often omit Origin. Channels' default validator
    treats a missing Origin as 403 before JWT middleware runs.
    If Origin is sent, the host must still match ALLOWED_HOSTS.
    """

    def valid_origin(self, parsed_origin):
        if parsed_origin is None:
            return True
        return super().valid_origin(parsed_origin)


_ws_app = SessionMiddlewareStack(
    AuthMiddlewareStack(
        TokenAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    )
)
_allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
if getattr(settings, "DEBUG", False) and not _allowed_hosts:
    _allowed_hosts = ["localhost", "127.0.0.1", "[::1]"]
_ws_app = AllowMissingOriginValidator(_ws_app, _allowed_hosts)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": _ws_app,
})
