import time
import uuid

from django.conf import settings
from agora_token_builder.RtcTokenBuilder import RtcTokenBuilder, Role_Publisher


class AgoraNotConfiguredError(Exception):
    pass


def get_agora_settings() -> tuple[str, str, int]:
    app_id = getattr(settings, 'AGORA_APP_ID', '') or ''
    app_certificate = getattr(settings, 'AGORA_APP_CERTIFICATE', '') or ''
    expire_seconds = int(getattr(settings, 'AGORA_TOKEN_EXPIRE_SECONDS', 3600))
    if not app_id or not app_certificate:
        raise AgoraNotConfiguredError(
            'AGORA_APP_ID and AGORA_APP_CERTIFICATE must be set in environment.'
        )
    return app_id, app_certificate, expire_seconds


def build_channel_name(prefix: str, entity_id: int) -> str:
    return f'{prefix}_{entity_id}_{uuid.uuid4().hex[:10]}'


def build_rtc_token(*, channel_name: str, user_id: int) -> dict:
    app_id, app_certificate, expire_seconds = get_agora_settings()
    privilege_expired_ts = int(time.time()) + expire_seconds
    token = RtcTokenBuilder.buildTokenWithUid(
        app_id,
        app_certificate,
        channel_name,
        int(user_id),
        Role_Publisher,
        privilege_expired_ts,
    )
    return {
        'app_id': app_id,
        'channel_name': channel_name,
        'token': token,
        'uid': int(user_id),
        'expires_at': privilege_expired_ts,
    }
