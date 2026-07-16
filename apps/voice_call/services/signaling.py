import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.notification.models import Notification
from apps.notification.services import enqueue_push_to_user_id

logger = logging.getLogger(__name__)


def _user_group(user_id: int) -> str:
    return f'voice_call_user_{user_id}'


def _support_duty_group() -> str:
    return 'voice_call_support_duty'


def emit_voice_call_event(user_id: int, event_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            _user_group(user_id),
            {
                'type': 'voice_call_event',
                'event_type': event_type,
                'payload': payload,
            },
        )
    except Exception:
        logger.exception('emit_voice_call_event failed user_id=%s', user_id)


def emit_support_duty_event(event_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            _support_duty_group(),
            {
                'type': 'voice_call_event',
                'event_type': event_type,
                'payload': payload,
            },
        )
    except Exception:
        logger.exception('emit_support_duty_event failed')


def _emit_notification_ws(notification: Notification) -> None:
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        payload = {
            'id': notification.id,
            'user_id': notification.user_id,
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'related_object_type': notification.related_object_type,
            'related_object_id': notification.related_object_id,
            'data': notification.data,
            'created_at': notification.created_at.isoformat() if notification.created_at else None,
            'status': notification.status,
        }
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.user_id}',
            {'type': 'notification', 'notification': payload},
        )
    except Exception:
        return


def notify_incoming_call(
    *,
    callee_user_id: int,
    call_payload: dict,
    title: str,
    body: str,
) -> None:
    emit_voice_call_event(callee_user_id, 'incoming_call', call_payload)
    notification = Notification.objects.create(
        user_id=callee_user_id,
        notification_type=Notification.NotificationType.SYSTEM,
        title=title,
        message=body,
        related_object_type='voice_call',
        related_object_id=call_payload.get('call_id'),
        data=call_payload,
    )
    _emit_notification_ws(notification)
    enqueue_push_to_user_id(
        callee_user_id,
        title=title,
        body=body,
        data={k: str(v) if v is not None else '' for k, v in call_payload.items()},
    )


def notify_call_update(user_ids: list[int], event_type: str, call_payload: dict) -> None:
    for uid in user_ids:
        if uid:
            emit_voice_call_event(uid, event_type, call_payload)


def notify_support_incoming(call_payload: dict, title: str, body: str) -> None:
    emit_support_duty_event('incoming_support_call', call_payload)
    from apps.voice_call.models import SupportAgentDuty

    admin_ids = list(
        SupportAgentDuty.objects.filter(is_on_duty=True).values_list('admin_id', flat=True)
    )
    if not admin_ids:
        from django.contrib.auth.models import Group
        from apps.accounts.models import CustomUser

        g = Group.objects.filter(name='Admin').first()
        if g:
            admin_ids = list(
                CustomUser.objects.filter(groups=g, is_active=True, is_superuser=True).values_list(
                    'id', flat=True
                )
            )
    for admin_id in admin_ids:
        notify_incoming_call(
            callee_user_id=admin_id,
            call_payload=call_payload,
            title=title,
            body=body,
        )


def build_call_ws_payload(
    call,
    *,
    agora: dict | None = None,
    include_agora: bool = False,
) -> dict:
    """
    WS signaling payload. Agora credentials are per-user — never put caller token
    in incoming_call to callee (causes one-way audio / UID clash on support accept).
  """
    caller = call.caller
    callee = call.callee
    payload = {
        'call_id': call.id,
        'call_type': call.call_type,
        'status': call.status,
        'order_id': call.order_id,
        'support_room_id': call.support_room_id,
        'channel_name': call.agora_channel_name,
        'app_id': call.agora_app_id or (agora or {}).get('app_id'),
        'initiator_role': call.initiator_role,
        'ring_started_at': call.ring_started_at.isoformat() if call.ring_started_at else None,
        'answered_at': call.answered_at.isoformat() if call.answered_at else None,
        'caller': {
            'id': caller.id,
            'full_name': caller.get_full_name(),
            'email': caller.email,
        },
        'callee': None
        if not callee
        else {
            'id': callee.id,
            'full_name': callee.get_full_name(),
            'email': callee.email,
        },
    }
    if include_agora and agora:
        payload['agora'] = agora
    return payload
