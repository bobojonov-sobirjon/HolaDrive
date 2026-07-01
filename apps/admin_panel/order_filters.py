"""Admin panel order list filters (Rides sidebar)."""
from __future__ import annotations

from django.db.models import Exists, OuterRef, QuerySet

from apps.order.models import Order, OrderSchedule

TERMINAL_STATUSES = (
    Order.OrderStatus.COMPLETED,
    Order.OrderStatus.CANCELLED,
    Order.OrderStatus.REJECTED,
)

ADMIN_ORDER_FILTERS = {
    'all': 'All rides',
    'scheduled': 'Scheduled rides (has schedule, not completed/cancelled)',
    'pending': 'Pending rides',
    'cancelled': 'Cancelled / rejected rides',
    'running': 'Active rides (accepted → in progress)',
    'completed': 'Completed rides',
}


def apply_admin_order_list_filters(
    qs: QuerySet,
    *,
    filter_value: str | None = None,
    status_value: str | None = None,
) -> tuple[QuerySet, str, str | None]:
    """
    Returns (queryset, applied_filter, applied_status).
    `filter` matches admin sidebar; `status` is exact Order.status override.
    """
    fv = (filter_value or 'all').strip().lower()
    sv = (status_value or '').strip().lower() or None

    if sv:
        valid = {c[0] for c in Order.OrderStatus.choices}
        if sv not in valid:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(sorted(valid))}')
        return qs.filter(status=sv), fv, sv

    if fv == 'all' or not fv:
        return qs, 'all', None

    if fv == 'pending':
        return qs.filter(status=Order.OrderStatus.PENDING), fv, None

    if fv == 'cancelled':
        return qs.filter(
            status__in=(Order.OrderStatus.CANCELLED, Order.OrderStatus.REJECTED)
        ), fv, None

    if fv == 'completed':
        return qs.filter(status=Order.OrderStatus.COMPLETED), fv, None

    if fv == 'running':
        return qs.filter(
            status__in=(
                Order.OrderStatus.ACCEPTED,
                Order.OrderStatus.ON_THE_WAY,
                Order.OrderStatus.ARRIVED,
                Order.OrderStatus.IN_PROGRESS,
            )
        ), fv, None

    if fv == 'scheduled':
        has_schedule = OrderSchedule.objects.filter(order_id=OuterRef('pk'))
        return (
            qs.filter(Exists(has_schedule))
            .exclude(status__in=TERMINAL_STATUSES)
            .distinct(),
            fv,
            None,
        )

    raise ValueError(
        f'Invalid filter. Must be one of: {", ".join(ADMIN_ORDER_FILTERS.keys())}'
    )


def admin_orders_base_queryset() -> QuerySet:
    return (
        Order.objects.select_related('user', 'saved_card')
        .prefetch_related(
            'order_items__ride_type',
            'order_preferences',
            'additional_passengers',
            'order_schedules',
            'order_drivers__driver',
            'cancel_orders',
            'payment_splits',
        )
        .order_by('-created_at')
    )
