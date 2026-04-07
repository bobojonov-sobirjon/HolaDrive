import logging
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.db import database_sync_to_async
from channels.sessions import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
import jwt
from urllib.parse import parse_qs, unquote

logger = logging.getLogger(__name__)


def _is_ws_orders_path(path: str) -> bool:
    """Driver/rider order WebSocket paths (plural + driver singular alias)."""
    if path.startswith("/ws/rider/orders"):
        return True
    if path.startswith("/ws/driver/orders"):
        return True
    return path == "/ws/driver/order" or path.startswith((
        "/ws/driver/order/",
        "/ws/driver/order/token=",
    ))


@database_sync_to_async
def get_user_from_jwt(token_key):
    if not token_key:
        return AnonymousUser()
    token_key = str(token_key).strip()
    if token_key.lower().startswith("bearer "):
        token_key = token_key[7:].strip()
    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token_key)
        user = jwt_auth.get_user(validated_token)
        return user
    except jwt.ExpiredSignatureError as e:
        logger.warning("[WS JWT] Token expired (PyJWT): %s", e)
        return AnonymousUser()
    except jwt.InvalidTokenError as e:
        logger.warning("[WS JWT] Invalid token (PyJWT): %s", e)
        return AnonymousUser()
    except (InvalidToken, TokenError) as e:
        # SimpleJWT (masalan: muddat tugagan, noto'g'ri imzo, boshqa SECRET_KEY)
        logger.warning(
            "[WS JWT] Access token rad etildi (login/refresh qiling, yoki shu server SECRET_KEY bilan chiqarilgan token ishlating): %s",
            e,
        )
        return AnonymousUser()


@database_sync_to_async
def get_user_from_session(session_key):
    """
    Get user from Django session (for admin panel)
    """
    try:
        session = Session.objects.get(session_key=session_key)
        user_id = session.get_decoded().get('_auth_user_id')
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.get(id=user_id)
    except (Session.DoesNotExist, KeyError, ValueError):
        pass
    return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        token_key = None
        path = scope.get("path", "") or ""

        # First, try to get token from query string
        query_string = parse_qs(scope.get("query_string", b"").decode())
        token_key = query_string.get("token", [None])[0]
        token_source = "query" if token_key else None

        # If not in query string, try to extract from URL path
        # Decode path so token= and JWT work when URL-encoded (e.g. token%3D, %2F in token)
        if not token_key:
            path_decoded = unquote(path)
            path_parts = [p for p in path_decoded.split("/") if p]  # Remove empty strings

            # /ws/driver/orders/..., /ws/driver/order/..., /ws/rider/orders/... — suffix so JWT is not split by "/"
            for ws_prefix in (
                "/ws/driver/orders/",
                "/ws/driver/order/",
                "/ws/rider/orders/",
            ):
                if path_decoded.startswith(ws_prefix):
                    suffix = path_decoded[len(ws_prefix) :].strip("/")
                    if suffix.startswith("token="):
                        token_key = suffix[6:].strip()
                    elif "." in suffix and len(suffix) > 50:
                        token_key = suffix
                    token_source = "path"
                    if ws_prefix == "/ws/driver/order/":
                        label = "driver/order"
                    elif "rider" in ws_prefix:
                        label = "rider/orders"
                    else:
                        label = "driver/orders"
                    logger.debug(
                        "[WS %s] path=%r suffix_len=%s token_found=%s token_preview=%s",
                        label,
                        path[:80],
                        len(suffix),
                        bool(token_key),
                        f"{token_key[:20]}...{token_key[-20:]}"
                        if token_key and len(token_key) > 45
                        else (token_key or ""),
                    )
                    break

            # Check if path has format: /ws/chat/1/TOKEN or /ws/chat/1/token=TOKEN
            if not token_key and len(path_parts) >= 4 and path_parts[0] == "ws" and path_parts[1] == "chat":
                if len(path_parts) > 3:
                    potential_token = path_parts[3]
                    if potential_token.startswith("token="):
                        token_key = potential_token[6:]
                    elif "." in potential_token and len(potential_token) > 50:
                        token_key = potential_token

            # Check if path has format: /ws/notifications/TOKEN or /ws/notifications/token=TOKEN
            if not token_key and len(path_parts) >= 3 and path_parts[0] == "ws" and path_parts[1] == "notifications":
                if len(path_parts) > 2:
                    potential_token = path_parts[2]
                    if potential_token.startswith("token="):
                        token_key = potential_token[6:]
                    elif "." in potential_token and len(potential_token) > 50:
                        token_key = potential_token

        if _is_ws_orders_path(path):
            logger.debug(
                "[WS orders] token_source=%s token_found=%s path_prefix=%s",
                token_source,
                bool(token_key),
                path[:40],
            )

        if token_key:
            scope["user"] = await get_user_from_jwt(token_key)
            if _is_ws_orders_path(path):
                user = scope["user"]
                logger.info(
                    "[WS orders] after_jwt user_id=%s is_anonymous=%s",
                    getattr(user, "id", None),
                    getattr(user, "is_anonymous", True),
                )
        else:
            # For admin panel, AuthMiddlewareStack has already set user from session
            if "user" not in scope:
                scope["user"] = AnonymousUser()
            if _is_ws_orders_path(path):
                logger.info("[WS orders] No token in query or path")

        return await super().__call__(scope, receive, send)
