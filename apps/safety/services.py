from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.chat.utils import get_support_admin_random
from apps.order.models import Order, OrderDriver

from .models import SafetyMessage, SafetyRoom, TripShareLink, TripVoiceRecording

ACTIVE_SHARE_STATUSES = (
    Order.OrderStatus.ACCEPTED,
    Order.OrderStatus.ON_THE_WAY,
    Order.OrderStatus.ARRIVED,
    Order.OrderStatus.IN_PROGRESS,
)


class SafetyServiceError(Exception):
    def __init__(self, message: str, code: str = 'error', errors: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.errors = errors or {}


def _is_staff(user) -> bool:
    return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


def user_can_access_order(user, order: Order) -> bool:
    if order.user_id == user.id:
        return True
    if _is_staff(user):
        return True
    return OrderDriver.objects.filter(
        order=order,
        driver=user,
        status=OrderDriver.DriverRequestStatus.ACCEPTED,
    ).exists()


def create_trip_share(*, user, order_id: int) -> TripShareLink:
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise SafetyServiceError('Order not found.', code='not_found')

    if order.user_id != user.id and not _is_staff(user):
        raise SafetyServiceError('Only the rider can share this trip.', code='forbidden')

    if order.status not in ACTIVE_SHARE_STATUSES:
        raise SafetyServiceError(
            'Trip can only be shared while it is active.',
            code='invalid_order_status',
            errors={'order_status': order.status},
        )

    hours = int(getattr(settings, 'SAFETY_SHARE_EXPIRE_HOURS', 6) or 6)
    expire_at = timezone.now() + timedelta(hours=hours)

    # One active link per order: revoke previous
    TripShareLink.objects.filter(order=order, is_active=True, revoked_at__isnull=True).update(
        is_active=False,
        revoked_at=timezone.now(),
    )

    return TripShareLink.objects.create(
        order=order,
        created_by=user,
        expires_at=expire_at,
    )


def revoke_trip_share(*, user, token: str) -> TripShareLink:
    try:
        link = TripShareLink.objects.select_related('order').get(token=token)
    except TripShareLink.DoesNotExist:
        raise SafetyServiceError('Share link not found.', code='not_found')

    if link.created_by_id != user.id and link.order.user_id != user.id and not _is_staff(user):
        raise SafetyServiceError('Forbidden.', code='forbidden')

    link.is_active = False
    link.revoked_at = timezone.now()
    link.save(update_fields=['is_active', 'revoked_at', 'updated_at'])
    return link


def get_valid_share_link(token: str) -> TripShareLink:
    try:
        link = TripShareLink.objects.select_related('order', 'order__user').get(token=token)
    except TripShareLink.DoesNotExist:
        raise SafetyServiceError('Share link not found.', code='not_found')
    if not link.is_valid:
        raise SafetyServiceError('Share link expired or revoked.', code='share_inactive')
    if link.order.status not in ACTIVE_SHARE_STATUSES:
        raise SafetyServiceError('Trip is no longer active.', code='trip_ended')
    return link


def build_public_share_payload(link: TripShareLink) -> dict:
    """Sanitized trip snapshot for friends (no phone / payment)."""
    order = link.order
    item = order.order_items.first() if hasattr(order, 'order_items') else None
    od = (
        OrderDriver.objects.filter(
            order=order,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        )
        .select_related('driver')
        .first()
    )
    driver = od.driver if od else None

    from apps.order.services.order_tracking_websocket import get_initial_tracking_payload

    tracking = get_initial_tracking_payload(order.id) or {}

    def _f(val):
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    pickup_lat = _f(getattr(item, 'latitude_from', None)) if item else None
    pickup_lng = _f(getattr(item, 'longitude_from', None)) if item else None
    dest_lat = _f(getattr(item, 'latitude_to', None)) if item else None
    dest_lng = _f(getattr(item, 'longitude_to', None)) if item else None

    return {
        'token': link.token,
        'share_url': link.share_url,
        'deep_link': link.deep_link,
        'public_api_url': link.public_api_url,
        'expires_at': link.expires_at.isoformat(),
        'order': {
            'id': order.id,
            'order_code': getattr(order, 'order_code', None),
            'status': order.status,
            'pickup': getattr(item, 'address_from', None) if item else None,
            'destination': getattr(item, 'address_to', None) if item else None,
            'pickup_latitude': pickup_lat,
            'pickup_longitude': pickup_lng,
            'destination_latitude': dest_lat,
            'destination_longitude': dest_lng,
        },
        'route': {
            'pickup': {'latitude': pickup_lat, 'longitude': pickup_lng},
            'destination': {'latitude': dest_lat, 'longitude': dest_lng},
        },
        'driver': None
        if not driver
        else {
            'id': driver.id,
            'full_name': driver.get_full_name() or None,
            # No phone / email for public share
        },
        'location': {
            'latitude': tracking.get('latitude'),
            'longitude': tracking.get('longitude'),
            'updated_at': tracking.get('updated_at'),
            'eta_minutes': tracking.get('eta_minutes'),
            'tracking_phase': tracking.get('tracking_phase'),
        },
        'ws_url_path': f'/ws/safety/share/{link.token}/',
    }


def open_safety_room(*, user, order_id: int | None = None) -> SafetyRoom:
    agent = get_support_admin_random()
    if not agent:
        raise SafetyServiceError('Safety agent is not available.', code='no_agent')

    with transaction.atomic():
        room, created = SafetyRoom.objects.select_for_update().get_or_create(
            user=user,
            agent=agent,
        )
        order_obj = None
        if order_id:
            order_obj = Order.objects.filter(pk=order_id).first()
            if order_obj and not user_can_access_order(user, order_obj) and not _is_staff(user):
                raise SafetyServiceError('You cannot attach this order.', code='forbidden')
            if order_obj and not room.orders.filter(pk=order_obj.pk).exists():
                room.orders.add(order_obj)
                SafetyMessage.objects.create(
                    room=room,
                    sender=user,
                    message_type=SafetyMessage.MessageType.SYSTEM,
                    message=f'Safety chat context: order #{order_obj.id}.',
                    order=order_obj,
                )
        elif created:
            SafetyMessage.objects.create(
                room=room,
                sender=user,
                message_type=SafetyMessage.MessageType.SYSTEM,
                message='Safety chat opened.',
            )
        room.updated_at = timezone.now()
        room.save(update_fields=['updated_at'])
    return room


def start_voice_recording(*, user, order_id: int) -> TripVoiceRecording:
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise SafetyServiceError('Order not found.', code='not_found')

    if not user_can_access_order(user, order):
        raise SafetyServiceError('Forbidden.', code='forbidden')

    if order.status not in ACTIVE_SHARE_STATUSES:
        raise SafetyServiceError(
            'Recording allowed only on active trips.',
            code='invalid_order_status',
        )

    active = TripVoiceRecording.objects.filter(
        order=order,
        user=user,
        status=TripVoiceRecording.Status.RECORDING,
    ).first()
    if active:
        return active

    return TripVoiceRecording.objects.create(order=order, user=user)


def stop_voice_recording(*, user, recording_id: int, audio_file=None, duration_seconds=None):
    try:
        rec = TripVoiceRecording.objects.select_related('order').get(id=recording_id)
    except TripVoiceRecording.DoesNotExist:
        raise SafetyServiceError('Recording not found.', code='not_found')

    if rec.user_id != user.id and not _is_staff(user):
        raise SafetyServiceError('Forbidden.', code='forbidden')

    if rec.status != TripVoiceRecording.Status.RECORDING:
        raise SafetyServiceError('Recording is not active.', code='invalid_status')

    rec.ended_at = timezone.now()
    if duration_seconds is not None:
        try:
            rec.duration_seconds = max(0, int(duration_seconds))
        except (TypeError, ValueError):
            rec.duration_seconds = None
    elif rec.started_at:
        rec.duration_seconds = max(0, int((rec.ended_at - rec.started_at).total_seconds()))

    if audio_file is not None:
        rec.audio_file = audio_file
        rec.status = TripVoiceRecording.Status.UPLOADED
    else:
        # Client stopped timer but upload may follow later — mark uploaded empty as failed soft
        rec.status = TripVoiceRecording.Status.UPLOADED

    rec.save()
    return rec
