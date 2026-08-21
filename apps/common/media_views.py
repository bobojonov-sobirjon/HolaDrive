"""Serve private media only to authenticated users (KYC / documents / recordings)."""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.views import View
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


PRIVATE_MEDIA_PREFIXES = (
    'driver_documents/',
    'driver_identification_',
    'driver_agreements/',
    'order_chat/',
    'chat/attachments/',
    'safety/',
    'trip_recordings/',
)


def _user_from_jwt(raw_token):
    if not raw_token:
        return None
    token = str(raw_token).strip()
    if token.lower().startswith('bearer '):
        token = token[7:].strip()
    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(token)
        return jwt_auth.get_user(validated)
    except (InvalidToken, TokenError, Exception):
        return None


class ProtectedMediaView(View):
    def get(self, request, path: str):
        rel = (path or '').replace('\\', '/').lstrip('/')
        if not rel or '..' in Path(rel).parts:
            raise Http404()

        is_private = any(rel.startswith(prefix) for prefix in PRIVATE_MEDIA_PREFIXES)
        user = getattr(request, 'user', None)
        if is_private and (not user or not user.is_authenticated):
            user = _user_from_jwt(request.headers.get('Authorization')) or _user_from_jwt(
                request.GET.get('token')
            )
            if not user or not getattr(user, 'is_authenticated', False):
                return HttpResponseForbidden('Authentication required')

        full = Path(settings.MEDIA_ROOT) / rel
        try:
            full.resolve().relative_to(Path(settings.MEDIA_ROOT).resolve())
        except ValueError:
            raise Http404()
        if not full.is_file():
            raise Http404()
        return FileResponse(full.open('rb'))
