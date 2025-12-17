import json
import logging
import os
from typing import Optional, Tuple

from django.conf import settings

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:  # pragma: no cover - firebase_admin not installed
    firebase_admin = None
    credentials = None
    messaging = None

try:
    import requests
except ImportError:  # pragma: no cover - in case requests is not installed
    requests = None

from apps.accounts.models import UserDeviceToken


logger = logging.getLogger(__name__)


FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"

_firebase_app: Optional["firebase_admin.App"] = None


def _init_firebase_app() -> Optional["firebase_admin.App"]:
    """
    Lazily initialize firebase_admin app from FIREBASE_* environment variables.

    Bu yerdagi nomlar sizdagi .env bilan bir xil bo‘lishi kerak:
    FIREBASE_TYPE, FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY_ID, FIREBASE_PRIVATE_KEY,
    FIREBASE_CLIENT_EMAIL, FIREBASE_CLIENT_ID, FIREBASE_AUTH_URI,
    FIREBASE_TOKEN_URI, FIREBASE_AUTH_PROVIDER_X509_CERT_URL, FIREBASE_CLIENT_X509_CERT_URL
    """
    global _firebase_app

    if firebase_admin is None or credentials is None:
        logger.warning("Firebase Admin SDK (firebase_admin) o‘rnatilmagan – pip install firebase-admin")
        return None

    if _firebase_app is not None:
        return _firebase_app

    required_keys = [
        "FIREBASE_TYPE",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_PRIVATE_KEY_ID",
        "FIREBASE_PRIVATE_KEY",
        "FIREBASE_CLIENT_EMAIL",
        "FIREBASE_CLIENT_ID",
        "FIREBASE_AUTH_URI",
        "FIREBASE_TOKEN_URI",
        "FIREBASE_AUTH_PROVIDER_X509_CERT_URL",
        "FIREBASE_CLIENT_X509_CERT_URL",
    ]

    env = {k: os.getenv(k) for k in required_keys}
    if not all(env.values()):
        logger.warning(
            "Firebase service account env lar to‘liq emas, push uchun firebase_admin ishlamaydi: %s",
            {k: bool(v) for k, v in env.items()},
        )
        return None

    # PRIVATE_KEY ichidagi \n larni to‘g‘rilab qo‘yamiz
    env["FIREBASE_PRIVATE_KEY"] = env["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n")

    service_account_info = {
        "type": env["FIREBASE_TYPE"],
        "project_id": env["FIREBASE_PROJECT_ID"],
        "private_key_id": env["FIREBASE_PRIVATE_KEY_ID"],
        "private_key": env["FIREBASE_PRIVATE_KEY"],
        "client_email": env["FIREBASE_CLIENT_EMAIL"],
        "client_id": env["FIREBASE_CLIENT_ID"],
        "auth_uri": env["FIREBASE_AUTH_URI"],
        "token_uri": env["FIREBASE_TOKEN_URI"],
        "auth_provider_x509_cert_url": env["FIREBASE_AUTH_PROVIDER_X509_CERT_URL"],
        "client_x509_cert_url": env["FIREBASE_CLIENT_X509_CERT_URL"],
    }

    try:
        cred = credentials.Certificate(service_account_info)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase app muvaffaqiyatli initialize qilindi")
        return _firebase_app
    except Exception as exc:  # pragma: no cover
        logger.exception("Firebase app initialize bo‘lmadi: %s", exc)
        _firebase_app = None
        return None


def _send_via_firebase_admin(tokens, title: str, body: str, data: Optional[dict]) -> Tuple[bool, Optional[str]]:
    app = _init_firebase_app()
    if app is None or messaging is None:
        return False, "firebase_admin_not_available"

    try:
        success_count = 0
        failure_count = 0

        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={k: str(v) for k, v in (data or {}).items()},
                    token=token,
                )
                messaging.send(message, app=app)
                success_count += 1
            except Exception as token_exc:  # pragma: no cover
                failure_count += 1
                logger.warning("send_push_to_user (firebase_admin): token=%s xatolik=%s", token, token_exc)

        logger.info(
            "send_push_to_user (firebase_admin): success_count=%s failure_count=%s",
            success_count,
            failure_count,
        )
        if failure_count == 0 and success_count > 0:
            return True, None
        if success_count > 0:
            return True, f"partial_failures_{failure_count}"
        return False, "all_failed"
    except Exception as exc:  # pragma: no cover
        logger.exception("send_push_to_user (firebase_admin): xatolik: %s", exc)
        return False, str(exc)


def _send_via_http_legacy(tokens, title: str, body: str, data: Optional[dict]) -> Tuple[bool, Optional[str]]:
    if requests is None:
        logger.warning("send_push_to_user: 'requests' library is not installed – push disabled")
        return False, "requests_not_installed"

    server_key = getattr(settings, "FCM_SERVER_KEY", None)
    if not server_key:
        env_value = os.getenv("FCM_SERVER_KEY")
        logger.warning(
            "send_push_to_user: FCM_SERVER_KEY is not set or empty – legacy HTTP push disabled "
            "(settings.FCM_SERVER_KEY=%r, os.getenv('FCM_SERVER_KEY')=%r)",
            server_key,
            env_value,
        )
        return False, "missing_fcm_server_key"

    payload = {
        "registration_ids": list(tokens),
        "notification": {
            "title": title,
            "body": body,
        },
        "data": data or {},
    }

    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            FCM_ENDPOINT,
            headers=headers,
            data=json.dumps(payload),
            timeout=5,
        )
        logger.info(
            "send_push_to_user (legacy HTTP): FCM response status=%s body=%s",
            resp.status_code,
            resp.text,
        )
        if resp.status_code == 200:
            return True, None
        return False, f"fcm_http_{resp.status_code}"
    except Exception as exc:  # pragma: no cover
        logger.exception("send_push_to_user (legacy HTTP): error while sending push: %s", exc)
        return False, str(exc)


def send_push_to_user(user, title: str, body: str, data: dict | None = None) -> tuple[bool, str | None]:
    """
    Send push notification to all device tokens of given user.

    Currently uses Firebase Cloud Messaging (FCM) HTTP v1 legacy API.

    Returns (success: bool, error_message: Optional[str])
    """
    if user is None:
        return False, "User is None"

    tokens = list(
        UserDeviceToken.objects.filter(user=user)
        .values_list("token", flat=True)
    )

    if not tokens:
        logger.info("send_push_to_user: no device tokens for user=%s", user.id)
        return False, "no_tokens"

    # 1) Avval firebase_admin orqali (sizdagi FIREBASE_* env lar bilan) jo‘natishga harakat qilamiz
    success, error = _send_via_firebase_admin(tokens, title, body, data)
    if success or error not in {"firebase_admin_not_available", "firebase_service_account_invalid"}:
        return success, error

    # 2) Agar firebase_admin ishlamasa, eski HTTP legacy (server key) usuliga fallback qilamiz
    return _send_via_http_legacy(tokens, title, body, data)


