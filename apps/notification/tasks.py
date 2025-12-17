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
    logger.info(f"Starting send_push_notification_async for user {user_id}")
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        logger.error(f"User {user_id} not found for push notification")
        return False, "user_not_found"
    
    try:
        success, error = send_push_to_user(
            user=user,
            title=title,
            body=body,
            data=data or {}
        )
        if success:
            logger.info(f"Push notification sent successfully to user {user_id}")
        else:
            logger.warning(f"Push notification failed for user {user_id}: {error}")
        return success, error
    except Exception as e:
        logger.error(
            f"Failed to send push notification to user {user_id}: {e}",
            exc_info=True
        )
        return False, str(e)

