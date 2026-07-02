from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.chat.models import SupportRoom
from apps.chat.utils import get_support_admin_random
from apps.order.models import Order, OrderDriver

from ..models import CallRecording, SupportAgentDuty, VoiceCallSession
from .agora import AgoraNotConfiguredError, build_channel_name, build_rtc_token, get_agora_settings
from .signaling import (
    build_call_ws_payload,
    notify_call_update,
    notify_incoming_call,
    notify_support_incoming,
)

logger = logging.getLogger(__name__)

TRIP_CALL_ORDER_STATUSES = (
    Order.OrderStatus.ACCEPTED,
    Order.OrderStatus.ON_THE_WAY,
    Order.OrderStatus.ARRIVED,
    Order.OrderStatus.IN_PROGRESS,
)

ACTIVE_CALL_STATUSES = (
    VoiceCallSession.Status.RINGING,
    VoiceCallSession.Status.ANSWERED,
)


@dataclass
class CallActionResult:
    call: VoiceCallSession
    agora: dict | None = None


class CallServiceError(Exception):
    def __init__(self, message: str, code: str = 'error', errors: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.errors = errors or {}


def _is_admin(user: CustomUser) -> bool:
    return bool(user.is_superuser or user.is_staff)


def _user_group_names(user: CustomUser) -> set[str]:
    return set(user.groups.values_list('name', flat=True))


def user_role_on_order(user: CustomUser, order: Order) -> str | None:
    if order.user_id == user.id:
        return VoiceCallSession.InitiatorRole.RIDER
    if OrderDriver.objects.filter(
        order=order,
        driver=user,
        status=OrderDriver.DriverRequestStatus.ACCEPTED,
    ).exists():
        return VoiceCallSession.InitiatorRole.DRIVER
    return None


def get_assigned_driver(order: Order) -> CustomUser | None:
    od = (
        OrderDriver.objects.filter(
            order=order,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        )
        .select_related('driver')
        .first()
    )
    return od.driver if od else None


def _active_call_q(user: CustomUser) -> Q:
    return Q(status__in=ACTIVE_CALL_STATUSES) & (Q(caller=user) | Q(callee=user))


def _ensure_no_active_call(user: CustomUser) -> None:
    if VoiceCallSession.objects.filter(_active_call_q(user)).exists():
        raise CallServiceError(
            'You already have an active call.',
            code='active_call_exists',
        )


def _ensure_agora_configured() -> tuple[str, str, int]:
    try:
        return get_agora_settings()
    except AgoraNotConfiguredError as exc:
        raise CallServiceError(str(exc), code='agora_not_configured') from exc


def _create_recording_stub(call: VoiceCallSession) -> CallRecording:
    recording, _ = CallRecording.objects.get_or_create(call=call)
    return recording


@transaction.atomic
def initiate_trip_call(*, user: CustomUser, order_id: int) -> CallActionResult:
    _ensure_agora_configured()
    _ensure_no_active_call(user)

    try:
        order = Order.objects.select_related('user').get(id=order_id)
    except Order.DoesNotExist:
        raise CallServiceError('Order not found.', code='not_found')

    if order.status not in TRIP_CALL_ORDER_STATUSES:
        raise CallServiceError(
            'Calls are allowed only after driver accepts the order.',
            code='invalid_order_status',
            errors={'order_status': order.status},
        )

    role = user_role_on_order(user, order)
    if not role:
        raise CallServiceError('You are not a participant of this order.', code='forbidden')

    driver = get_assigned_driver(order)
    if not driver:
        raise CallServiceError('No driver assigned to this order yet.', code='no_driver')

    if role == VoiceCallSession.InitiatorRole.RIDER:
        callee = driver
        if driver.id == user.id:
            raise CallServiceError('Cannot call yourself.', code='invalid_callee')
    else:
        callee = order.user
        if callee.id == user.id:
            raise CallServiceError('Cannot call yourself.', code='invalid_callee')

    if VoiceCallSession.objects.filter(
        order=order,
        status__in=ACTIVE_CALL_STATUSES,
    ).exists():
        raise CallServiceError(
            'There is already an active call for this order.',
            code='order_call_active',
        )

    app_id, _, _ = get_agora_settings()
    channel = build_channel_name('trip', order.id)
    call = VoiceCallSession.objects.create(
        call_type=VoiceCallSession.CallType.TRIP,
        status=VoiceCallSession.Status.RINGING,
        order=order,
        caller=user,
        callee=callee,
        agora_channel_name=channel,
        agora_app_id=app_id,
        initiator_role=role,
    )
    _create_recording_stub(call)

    caller_agora = build_rtc_token(channel_name=channel, user_id=user.id)
    payload = build_call_ws_payload(call, agora=caller_agora, for_user_id=user.id)
    notify_incoming_call(
        callee_user_id=callee.id,
        call_payload=payload,
        title='Incoming call',
        body=f'{user.get_full_name() or user.email} is calling about order {order.order_code}',
    )
    return CallActionResult(call=call, agora=caller_agora)


def _get_or_create_support_room(user: CustomUser, order_id: int | None) -> SupportRoom:
    """Reuse rider/driver's latest support room to avoid duplicate (user, admin) rows."""
    room = SupportRoom.objects.filter(user=user).order_by('-updated_at').first()
    if not room:
        admin = get_support_admin_random()
        if not admin:
            raise CallServiceError('Support is not available.', code='no_support_admin')
        room, _ = SupportRoom.objects.get_or_create(user=user, admin=admin)
    if order_id:
        from apps.order.models import Order

        try:
            order = Order.objects.get(id=order_id, user=user)
        except Order.DoesNotExist:
            if not _is_admin(user):
                try:
                    order = Order.objects.get(id=order_id)
                    if user_role_on_order(user, order) != VoiceCallSession.InitiatorRole.DRIVER:
                        order = None
                except Order.DoesNotExist:
                    order = None
            else:
                order = None
        if order:
            room.orders.add(order)
    return room


@transaction.atomic
def initiate_support_call(*, user: CustomUser, order_id: int | None = None) -> CallActionResult:
    _ensure_agora_configured()
    _ensure_no_active_call(user)

    groups = _user_group_names(user)
    if 'Rider' in groups:
        call_type = VoiceCallSession.CallType.RIDER_SUPPORT
        initiator_role = VoiceCallSession.InitiatorRole.RIDER
    elif 'Driver' in groups:
        call_type = VoiceCallSession.CallType.DRIVER_SUPPORT
        initiator_role = VoiceCallSession.InitiatorRole.DRIVER
    else:
        raise CallServiceError('Only riders or drivers can call support.', code='forbidden')

    room = _get_or_create_support_room(user, order_id)
    app_id, _, _ = get_agora_settings()
    channel = build_channel_name('support', room.id)
    call = VoiceCallSession.objects.create(
        call_type=call_type,
        status=VoiceCallSession.Status.RINGING,
        support_room=room,
        order_id=order_id,
        caller=user,
        callee=None,
        agora_channel_name=channel,
        agora_app_id=app_id,
        initiator_role=initiator_role,
    )
    _create_recording_stub(call)

    caller_agora = build_rtc_token(channel_name=channel, user_id=user.id)
    payload = build_call_ws_payload(call, agora=caller_agora, for_user_id=user.id)
    notify_support_incoming(
        call_payload=payload,
        title='Support call',
        body=f'{user.get_full_name() or user.email} is calling support',
    )
    return CallActionResult(call=call, agora=caller_agora)


def _finalize_duration(call: VoiceCallSession) -> None:
    if call.answered_at and call.ended_at:
        delta = call.ended_at - call.answered_at
        call.duration_seconds = max(0, int(delta.total_seconds()))


@transaction.atomic
def accept_call(*, user: CustomUser, call_id: int) -> CallActionResult:
    _ensure_agora_configured()
    try:
        call = (
            VoiceCallSession.objects.select_for_update(of=('self',))
            .select_related('caller', 'callee', 'order', 'support_room')
            .get(id=call_id)
        )
    except VoiceCallSession.DoesNotExist:
        raise CallServiceError('Call not found.', code='not_found')

    if call.status != VoiceCallSession.Status.RINGING:
        raise CallServiceError('Call is not ringing.', code='invalid_status')

    is_support = call.call_type in (
        VoiceCallSession.CallType.RIDER_SUPPORT,
        VoiceCallSession.CallType.DRIVER_SUPPORT,
    )

    if is_support:
        if not _is_admin(user):
            raise CallServiceError('Only support agents can accept this call.', code='forbidden')
        call.callee = user
        # Do not reassign support_room.admin — UniqueConstraint (user, admin) would fail
        # if another room already exists for this user+accepting admin pair.
    else:
        if call.callee_id != user.id:
            raise CallServiceError('You are not the callee for this call.', code='forbidden')

    call.status = VoiceCallSession.Status.ANSWERED
    call.answered_at = timezone.now()
    call.save(update_fields=['status', 'callee', 'answered_at', 'updated_at'])

    callee_agora = build_rtc_token(channel_name=call.agora_channel_name, user_id=user.id)
    caller_agora = build_rtc_token(channel_name=call.agora_channel_name, user_id=call.caller_id)

    payload_callee = build_call_ws_payload(call, agora=callee_agora, for_user_id=user.id)
    payload_caller = build_call_ws_payload(call, agora=caller_agora, for_user_id=call.caller_id)

    notify_call_update([call.caller_id], 'call_accepted', payload_caller)
    if is_support:
        notify_call_update([user.id], 'call_accepted', payload_callee)
    else:
        notify_call_update([user.id], 'call_accepted', payload_callee)

    agora_for_user = callee_agora if user.id == call.callee_id else caller_agora
    return CallActionResult(call=call, agora=agora_for_user)


@transaction.atomic
def reject_call(*, user: CustomUser, call_id: int, reason: str = '') -> VoiceCallSession:
    try:
        call = VoiceCallSession.objects.select_for_update().get(id=call_id)
    except VoiceCallSession.DoesNotExist:
        raise CallServiceError('Call not found.', code='not_found')

    if call.status != VoiceCallSession.Status.RINGING:
        raise CallServiceError('Call is not ringing.', code='invalid_status')

    is_support = call.call_type in (
        VoiceCallSession.CallType.RIDER_SUPPORT,
        VoiceCallSession.CallType.DRIVER_SUPPORT,
    )
    if is_support:
        if not _is_admin(user):
            raise CallServiceError('Forbidden.', code='forbidden')
    elif call.callee_id != user.id:
        raise CallServiceError('Forbidden.', code='forbidden')

    call.status = VoiceCallSession.Status.REJECTED
    call.ended_at = timezone.now()
    call.end_reason = reason or 'rejected'
    call.save(update_fields=['status', 'ended_at', 'end_reason', 'updated_at'])

    payload = build_call_ws_payload(call)
    notify_call_update([call.caller_id], 'call_rejected', payload)
    return call


@transaction.atomic
def cancel_call(*, user: CustomUser, call_id: int, reason: str = '') -> VoiceCallSession:
    try:
        call = VoiceCallSession.objects.select_for_update().get(id=call_id)
    except VoiceCallSession.DoesNotExist:
        raise CallServiceError('Call not found.', code='not_found')

    if call.caller_id != user.id:
        raise CallServiceError('Only the caller can cancel.', code='forbidden')
    if call.status != VoiceCallSession.Status.RINGING:
        raise CallServiceError('Call is not ringing.', code='invalid_status')

    call.status = VoiceCallSession.Status.CANCELLED
    call.ended_at = timezone.now()
    call.end_reason = reason or 'cancelled_by_caller'
    call.save(update_fields=['status', 'ended_at', 'end_reason', 'updated_at'])

    payload = build_call_ws_payload(call)
    targets = [call.caller_id]
    if call.callee_id:
        targets.append(call.callee_id)
    notify_call_update(targets, 'call_cancelled', payload)
    return call


@transaction.atomic
def end_call(*, user: CustomUser, call_id: int, reason: str = '') -> VoiceCallSession:
    try:
        call = VoiceCallSession.objects.select_for_update().get(id=call_id)
    except VoiceCallSession.DoesNotExist:
        raise CallServiceError('Call not found.', code='not_found')

    if user.id not in (call.caller_id, call.callee_id):
        raise CallServiceError('Forbidden.', code='forbidden')
    if call.status not in (VoiceCallSession.Status.RINGING, VoiceCallSession.Status.ANSWERED):
        raise CallServiceError('Call already finished.', code='invalid_status')

    now = timezone.now()
    if call.status == VoiceCallSession.Status.RINGING:
        call.status = VoiceCallSession.Status.MISSED
        call.end_reason = reason or 'missed'
    else:
        call.status = VoiceCallSession.Status.ENDED
        call.end_reason = reason or 'ended'
    call.ended_at = now
    _finalize_duration(call)
    call.save(
        update_fields=['status', 'ended_at', 'end_reason', 'duration_seconds', 'updated_at']
    )

    payload = build_call_ws_payload(call)
    targets = [call.caller_id]
    if call.callee_id:
        targets.append(call.callee_id)
    notify_call_update(targets, 'call_ended', payload)
    return call


def set_support_duty(*, admin: CustomUser, is_on_duty: bool) -> SupportAgentDuty:
    if not _is_admin(admin):
        raise CallServiceError('Only admins can set support duty.', code='forbidden')
    duty, _ = SupportAgentDuty.objects.get_or_create(admin=admin)
    duty.is_on_duty = is_on_duty
    duty.save(update_fields=['is_on_duty', 'updated_at'])
    return duty


def get_call_for_user(user: CustomUser, call_id: int) -> VoiceCallSession:
    try:
        call = VoiceCallSession.objects.select_related(
            'caller', 'callee', 'order', 'support_room', 'recording'
        ).get(id=call_id)
    except VoiceCallSession.DoesNotExist:
        raise CallServiceError('Call not found.', code='not_found')

    if _is_admin(user):
        return call
    if user.id in (call.caller_id, call.callee_id):
        return call
    raise CallServiceError('Forbidden.', code='forbidden')


def list_calls_for_user(
    user: CustomUser,
    *,
    call_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    if _is_admin(user):
        qs = VoiceCallSession.objects.all()
    else:
        qs = VoiceCallSession.objects.filter(Q(caller=user) | Q(callee=user))

    if call_type:
        qs = qs.filter(call_type=call_type)

    qs = qs.select_related('caller', 'callee', 'order', 'support_room', 'recording').order_by(
        '-created_at'
    )
    total = qs.count()
    start = (page - 1) * page_size
    rows = list(qs[start : start + page_size])
    return rows, total
