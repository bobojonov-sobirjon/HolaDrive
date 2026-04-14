"""
Celery tasks for notification management.
Handles async push notifications to avoid blocking API responses.
"""
import logging
from celery import shared_task
from apps.accounts.models import CustomUser
from apps.notification.services import send_push_to_user

logger = logging.getLogger(__name__)


@shared_task(name='apps.notification.tasks.send_push_notification_async')
def send_push_notification_async(user_id, title, body, data=None):
    """
    Async task: Send push notification to user (non-blocking).
    This task is called to avoid blocking API responses when sending push notifications.
    
    Args:
        user_id: User ID
        title: Notification title
        body: Notification body
        data: Optional notification data dict
    
    Returns:
        tuple: (success: bool, error: str or None)
    """
    logger.info(
        "[PUSH DEBUG] send_push_notification_async START | user_id=%s title=%r",
        user_id,
        title,
    )

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        logger.error("[PUSH DEBUG] user_id=%s topilmadi (CustomUser)", user_id)
        return False, "user_not_found"

    try:
        success, error = send_push_to_user(
            user=user,
            title=title,
            body=body,
            data=data or {}
        )
        if success:
            logger.info(
                "[PUSH DEBUG] send_push_notification_async OK | user_id=%s",
                user_id,
            )
        else:
            logger.warning(
                "[PUSH DEBUG] send_push_notification_async FAIL | user_id=%s error=%r "
                "(ko‘p hollarda: UserDeviceToken yo‘q yoki Firebase xato)",
                user_id,
                error,
            )
        return success, error
    except Exception as e:
        logger.error(
            f"Failed to send push notification to user {user_id}: {e}",
            exc_info=True
        )
        return False, str(e)

