import logging
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from channels.db import database_sync_to_async
from channels.sessions import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
import jwt
from urllib.parse import parse_qs, unquote

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_jwt(token_key):
    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token_key)
        user = jwt_auth.get_user(validated_token)
        return user
    except jwt.ExpiredSignatureError as e:
        logger.warning("[WS JWT] Token expired: %s", e)
        return AnonymousUser()
    except jwt.InvalidTokenError as e:
        logger.warning("[WS JWT] Invalid token: %s", e)
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

            # /ws/driver/orders/... — take full suffix so JWT is never split by path segments
            if path_decoded.startswith("/ws/driver/orders/"):
                suffix = path_decoded[len("/ws/driver/orders/"):].strip("/")
                if suffix.startswith("token="):
                    token_key = suffix[6:].strip()
                elif "." in suffix and len(suffix) > 50:
                    token_key = suffix
                token_source = "path"
                logger.debug(
                    "[WS driver/orders] path=%r suffix_len=%s token_found=%s token_preview=%s",
                    path[:80], len(suffix), bool(token_key),
                    f"{token_key[:20]}...{token_key[-20:]}" if token_key and len(token_key) > 45 else (token_key or ""),
                )

            # Check if path has format: /ws/chat/1/TOKEN or /ws/chat/1/token=TOKEN
            elif len(path_parts) >= 4 and path_parts[0] == "ws" and path_parts[1] == "chat":
                if len(path_parts) > 3:
                    potential_token = path_parts[3]
                    if potential_token.startswith("token="):
                        token_key = potential_token[6:]
                    elif "." in potential_token and len(potential_token) > 50:
                        token_key = potential_token

            # Check if path has format: /ws/notifications/TOKEN or /ws/notifications/token=TOKEN
            elif len(path_parts) >= 3 and path_parts[0] == "ws" and path_parts[1] == "notifications":
                if len(path_parts) > 2:
                    potential_token = path_parts[2]
                    if potential_token.startswith("token="):
                        token_key = potential_token[6:]
                    elif "." in potential_token and len(potential_token) > 50:
                        token_key = potential_token

        if path.startswith("/ws/driver/orders"):
            logger.debug(
                "[WS driver/orders] token_source=%s token_found=%s",
                token_source, bool(token_key),
            )

        if token_key:
            # Use JWT authentication
            try:
                scope["user"] = await get_user_from_jwt(token_key)
                if path.startswith("/ws/driver/orders"):
                    user = scope["user"]
                    logger.info(
                        "[WS driver/orders] token_ok user_id=%s is_anonymous=%s",
                        getattr(user, "id", None),
                        getattr(user, "is_anonymous", True),
                    )
            except Exception as e:
                logger.warning("[WS JWT] Validation failed: %s", e)
                scope["user"] = AnonymousUser()
        else:
            # For admin panel, AuthMiddlewareStack has already set user from session
            if "user" not in scope:
                scope["user"] = AnonymousUser()
            if path.startswith("/ws/driver/orders"):
                logger.info("[WS driver/orders] No token in query or path")

        return await super().__call__(scope, receive, send)
