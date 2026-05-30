import json
import logging
import os
from typing import Optional, Tuple

from django.conf import settings

try:
    from firebase_admin import messaging
except ImportError:  # pragma: no cover - firebase_admin not installed
    messaging = None

from apps.common.firebase import get_firebase_app

try:
    import requests
except ImportError:  # pragma: no cover - in case requests is not installed
    requests = None

from apps.accounts.models import UserDeviceToken


logger = logging.getLogger(__name__)


FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"


def _send_via_firebase_admin(tokens, title: str, body: str, data: Optional[dict]) -> Tuple[bool, Optional[str]]:
    app = get_firebase_app()
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
                err_txt = str(token_exc)
                logger.warning(
                    "send_push_to_user (firebase_admin): token=%s error=%s", token, token_exc
                )
                if "SenderId" in err_txt or "sender id" in err_txt.lower():
                    pid = os.getenv("FIREBASE_PROJECT_ID") or "(FIREBASE_PROJECT_ID)"
                    logger.error(
                        "[PUSH] SenderId mismatch: FCM token project does not match backend "
                        "FIREBASE_PROJECT_ID=%s. Align service account and app google-services.json.",
                        pid,
                    )

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
        logger.exception("send_push_to_user (firebase_admin): %s", exc)
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


def _token_fingerprint(token: str) -> str:
    if not token or len(token) < 8:
        return "(short)"
    return f"{token[:6]}…{token[-4:]}"


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
        logger.warning("send_push_to_user: no device tokens for user_id=%s", user.id)
        return False, "no_tokens"

    success, error = _send_via_firebase_admin(tokens, title, body, data)

    if success or error not in {"firebase_admin_not_available", "firebase_service_account_invalid"}:
        return success, error

    return _send_via_http_legacy(tokens, title, body, data)


def enqueue_push_to_user_id(
    user_id: int, title: str, body: str, data: dict | None = None
) -> None:
    """
    Queue an FCM push by user primary key (best-effort, async-safe).
    If Celery is unavailable or queueing fails, we only log and return.
    This helper must never raise into API flow.
    """
    try:
        from apps.notification.tasks import send_push_notification_async

        send_push_notification_async.delay(
            user_id=user_id,
            title=title,
            body=body,
            data=data or {},
        )
    except ImportError:
        logger.warning(
            "enqueue_push_to_user_id: Celery task unavailable user_id=%s; push skipped",
            user_id,
        )
    except Exception as exc:
        logger.warning(
            "enqueue_push_to_user_id: queue failed user_id=%s: %s; push skipped",
            user_id,
            exc,
        )


