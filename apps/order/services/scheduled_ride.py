"""Scheduled (Later) rides: validate time, payload, delayed dispatch."""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from apps.order.models import Order, OrderSchedule

logger = logging.getLogger(__name__)

MIN_LEAD_MINUTES = 30
MAX_DAYS = 7
DISPATCH_LEAD_MINUTES = 30
FREE_CANCEL_MINUTES = 60
DISPLAY_TZ_NAME = (os.getenv('SCHEDULE_DISPLAY_TIMEZONE') or 'America/Edmonton').strip()


def display_tz():
    try:
        return ZoneInfo(DISPLAY_TZ_NAME)
    except Exception:
        return timezone.get_current_timezone()


def iso_local(dt) -> str | None:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt.astimezone(display_tz()).isoformat()


def parse_scheduled_at(raw) -> datetime:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise serializers.ValidationError('scheduled_at is required for later rides.')
    if isinstance(raw, datetime):
        dt = raw
    else:
        dt = parse_datetime(str(raw).strip())
    if dt is None:
        raise serializers.ValidationError(
            'scheduled_at must be ISO 8601 with offset (e.g. 2026-09-17T20:00:00-06:00).'
        )
    if timezone.is_naive(dt):
        raise serializers.ValidationError(
            'scheduled_at must include a timezone offset (Z or ±HH:MM).'
        )
    return dt


def validate_pickup_window(pickup_at: datetime) -> None:
    now = timezone.now()
    if pickup_at < now + timedelta(minutes=MIN_LEAD_MINUTES):
        raise serializers.ValidationError(
            f'scheduled_at must be at least {MIN_LEAD_MINUTES} minutes from now.'
        )
    if pickup_at > now + timedelta(days=MAX_DAYS):
        raise serializers.ValidationError(
            f'scheduled_at cannot be more than {MAX_DAYS} days from now.'
        )


def estimated_trip_minutes(order: Order) -> int:
    items = list(order.order_items.all())
    total = 0
    for item in items:
        text = (item.estimated_time or '').lower()
        hours = re.search(r'(\d+)\s*h', text)
        mins = re.search(r'(\d+)\s*m', text)
        chunk = 0
        if hours:
            chunk += int(hours.group(1)) * 60
        if mins:
            chunk += int(mins.group(1))
        if chunk == 0 and item.distance_km:
            try:
                chunk = max(1, int(float(item.distance_km) / 45.0 * 60))
            except (TypeError, ValueError):
                chunk = 0
        total += chunk
    return total or 15


def resolve_times(schedule_type: str, user_at: datetime, order: Order) -> tuple[datetime, datetime | None]:
    """Return (pickup_at, dropoff_at). dropoff_at set only for drop_off_by."""
    if schedule_type == OrderSchedule.ScheduleType.DROP_OFF_BY:
        duration = timedelta(minutes=estimated_trip_minutes(order))
        pickup_at = user_at - duration
        return pickup_at, user_at
    return user_at, None


def apply_schedule(
    order: Order,
    *,
    schedule_type: str,
    user_at: datetime,
) -> OrderSchedule:
    pickup_at, dropoff_at = resolve_times(schedule_type, user_at, order)
    validate_pickup_window(pickup_at)

    local = pickup_at.astimezone(display_tz())
    defaults = {
        'schedule_type': schedule_type,
        'scheduled_at': user_at,
        'pickup_at': pickup_at,
        'dropoff_at': dropoff_at,
        'schedule_date': local.date(),
        'schedule_time': local.time().replace(microsecond=0),
        'schedule_time_type': OrderSchedule.ScheduleTime.SELECT_DATE,
        'dispatched_at': None,
    }
    existing = (
        OrderSchedule.objects.filter(order=order)
        .order_by('-id')
        .first()
    )
    if existing:
        for key, val in defaults.items():
            setattr(existing, key, val)
        existing.save()
        return existing
    return OrderSchedule.objects.create(order=order, **defaults)


def _legacy_pickup(sched: OrderSchedule):
    if sched.pickup_at:
        return sched.pickup_at
    if sched.scheduled_at:
        return sched.scheduled_at
    if sched.schedule_date and sched.schedule_time:
        naive = datetime.combine(sched.schedule_date, sched.schedule_time)
        return timezone.make_aware(naive, display_tz())
    return None


def canonical_schedule(order: Order) -> OrderSchedule | None:
    schedules = getattr(order, '_prefetched_objects_cache', {}).get('order_schedules')
    if schedules is not None:
        rows = list(schedules)
    else:
        rows = list(order.order_schedules.all())
    if not rows:
        return None
    rows.sort(key=lambda s: s.id, reverse=True)
    with_pickup = [s for s in rows if s.pickup_at or s.scheduled_at]
    return (with_pickup or rows)[0]


def schedule_payload(order: Order) -> dict | None:
    sched = canonical_schedule(order)
    if sched is None:
        return None
    pickup_at = _legacy_pickup(sched)
    if pickup_at is None:
        return None
    user_at = sched.scheduled_at or pickup_at
    dropoff_at = sched.dropoff_at
    sched_type = sched.schedule_type or OrderSchedule.ScheduleType.PICKUP_AT
    dispatch_at = pickup_at - timedelta(minutes=DISPATCH_LEAD_MINUTES)
    free_until = pickup_at - timedelta(minutes=FREE_CANCEL_MINUTES)
    now = timezone.now()
    is_scheduled = order.status == Order.OrderStatus.SCHEDULED
    return {
        'type': sched_type,
        'scheduled_at': iso_local(user_at),
        'pickup_at': iso_local(pickup_at),
        'dropoff_by': iso_local(dropoff_at),
        'timezone': DISPLAY_TZ_NAME,
        'dispatch_at': iso_local(dispatch_at),
        'can_edit': is_scheduled,
        'can_cancel_free': is_scheduled and now < free_until,
        'free_cancel_until': iso_local(free_until),
    }


def cancel_fee_payload(order: Order) -> dict:
    sched = canonical_schedule(order)
    pickup_at = _legacy_pickup(sched) if sched else None
    if order.status != Order.OrderStatus.SCHEDULED or pickup_at is None:
        return {'can_cancel_free': True, 'cancel_fee': None}
    free_until = pickup_at - timedelta(minutes=FREE_CANCEL_MINUTES)
    if timezone.now() < free_until:
        return {'can_cancel_free': True, 'cancel_fee': None}
    return {'can_cancel_free': False, 'cancel_fee': '0.00'}


def dispatch_due_scheduled_orders() -> int:
    """Move due scheduled orders to pending and start driver assignment."""
    from apps.order.services.driver_assignment_service import DriverAssignmentService
    from apps.order.services.rider_orders_websocket import notify_rider_order_updated

    cutoff = timezone.now() + timedelta(minutes=DISPATCH_LEAD_MINUTES)
    due_ids = list(
        Order.objects.filter(
            status=Order.OrderStatus.SCHEDULED,
            order_schedules__pickup_at__lte=cutoff,
        )
        .values_list('id', flat=True)
        .distinct()
    )
    dispatched = 0
    from django.db import transaction

    for oid in due_ids:
        with transaction.atomic():
            qs = Order.objects.filter(pk=oid, status=Order.OrderStatus.SCHEDULED)
            try:
                order = qs.select_for_update(skip_locked=True).first()
            except Exception:
                order = qs.select_for_update().first()
            if not order:
                continue
            order.status = Order.OrderStatus.PENDING
            order.save(update_fields=['status', 'updated_at'])
            OrderSchedule.objects.filter(order=order).update(dispatched_at=timezone.now())
        try:
            DriverAssignmentService.assign_to_next_driver(Order.objects.get(pk=oid))
        except Exception:
            logger.exception('Scheduled dispatch assign failed for order %s', oid)
        try:
            notify_rider_order_updated(
                oid,
                'scheduled_dispatch',
                'Looking for a driver.',
            )
        except Exception:
            logger.warning('Scheduled dispatch WS failed for order %s', oid, exc_info=True)
        dispatched += 1
        logger.info('Dispatched scheduled order %s', oid)
    return dispatched
