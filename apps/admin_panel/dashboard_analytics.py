"""Helpers for admin analytics dashboard (site stats, ride status chart, driver donut, recent rides)."""
from __future__ import annotations

from calendar import month_abbr
from datetime import date

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.db.models import DecimalField, Value
from django.utils import timezone

from apps.accounts.models import CustomUser, DriverVerification
from apps.order.models import Order, OrderDriver, OrderItem, RideType

RUNNING_STATUSES = (
    Order.OrderStatus.ACCEPTED,
    Order.OrderStatus.ON_THE_WAY,
    Order.OrderStatus.ARRIVED,
    Order.OrderStatus.IN_PROGRESS,
)

CANCELLED_STATUSES = (
    Order.OrderStatus.CANCELLED,
    Order.OrderStatus.REJECTED,
)

_PRICE_EXPR = Coalesce(
    'adjusted_price',
    'calculated_price',
    'original_price',
    output_field=DecimalField(max_digits=12, decimal_places=2),
)


def _order_trip_total(order: Order) -> float:
    total = 0.0
    for it in order.order_items.all():
        total += float(it.adjusted_price or it.calculated_price or it.original_price or 0)
    return round(total, 2)


def _pickup_dropoff(order: Order) -> tuple[str | None, str | None]:
    items = list(order.order_items.all().order_by('stop_sequence', 'id'))
    if not items:
        return None, None
    pickup = items[0].address_from or items[0].address_to
    dropoff = None
    for it in reversed(items):
        if it.is_final_stop and it.address_to:
            dropoff = it.address_to
            break
    if not dropoff:
        dropoff = items[-1].address_to or items[-1].address_from
    return pickup, dropoff


def _accepted_driver_name(order: Order) -> str | None:
    od = (
        OrderDriver.objects.filter(
            order_id=order.id,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        )
        .select_related('driver')
        .first()
    )
    if not od or not od.driver_id:
        return None
    d = od.driver
    name = d.get_full_name() or d.username or d.email
    return name or None


def build_site_statistics() -> dict:
    """All-time site overview cards."""
    total_riders = CustomUser.objects.filter(groups__name='Rider').distinct().count()
    total_drivers = CustomUser.objects.filter(groups__name='Driver').distinct().count()
    vehicle_types = RideType.objects.filter(is_active=True).count()

    completed_orders = Order.objects.filter(status=Order.OrderStatus.COMPLETED)
    revenue_from_rides = (
        OrderItem.objects.filter(
            order__status=Order.OrderStatus.COMPLETED,
            is_final_stop=True,
        ).aggregate(
            total=Coalesce(
                Sum(_PRICE_EXPR, output_field=DecimalField(max_digits=14, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )['total']
        or 0
    )
    completed_count = completed_orders.count()

    return {
        'total_riders': total_riders,
        'total_drivers': total_drivers,
        'vehicle_types': vehicle_types,
        'revenue': {
            'amount': float(revenue_from_rides),
            'currency': 'USD',
            'from_completed_rides': completed_count,
        },
    }


def build_ride_statistics() -> dict:
    """All-time ride count cards."""
    qs = Order.objects.all()
    return {
        'total_rides': qs.count(),
        'cancelled_rides': qs.filter(status__in=CANCELLED_STATUSES).count(),
        'running_rides': qs.filter(status__in=RUNNING_STATUSES).count(),
        'completed_rides': qs.filter(status=Order.OrderStatus.COMPLETED).count(),
        'pending_rides': qs.filter(status=Order.OrderStatus.PENDING).count(),
    }


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _next_month(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1)
    return d.replace(month=d.month + 1, day=1)


def _month_range(d1: date, d2: date):
    cur = _month_start(d1)
    end = _month_start(d2)
    while cur <= end:
        yield cur
        cur = _next_month(cur)


def build_ride_status_series(dt_from, dt_to, interval: str = 'month') -> list[dict]:
    """
    Stacked area chart: cancelled vs completed per time bucket.
    """
    trunc = TruncMonth('created_at')
    base_qs = Order.objects.filter(created_at__range=(dt_from, dt_to))

    cancelled_rows = (
        base_qs.filter(status__in=CANCELLED_STATUSES)
        .annotate(bucket=trunc)
        .values('bucket')
        .annotate(value=Count('id'))
    )
    completed_rows = (
        base_qs.filter(status=Order.OrderStatus.COMPLETED)
        .annotate(bucket=trunc)
        .values('bucket')
        .annotate(value=Count('id'))
    )

    cancelled_map = {}
    for r in cancelled_rows:
        b = r.get('bucket')
        if b:
            cancelled_map[b.date().replace(day=1)] = int(r.get('value') or 0)

    completed_map = {}
    for r in completed_rows:
        b = r.get('bucket')
        if b:
            completed_map[b.date().replace(day=1)] = int(r.get('value') or 0)

    date_from = dt_from.date() if hasattr(dt_from, 'date') else dt_from
    date_to = dt_to.date() if hasattr(dt_to, 'date') else dt_to

    points = []
    for d in _month_range(date_from, date_to):
        points.append(
            {
                'x': d.strftime('%Y-%m'),
                'label': month_abbr[d.month],
                'cancelled': cancelled_map.get(d, 0),
                'completed': completed_map.get(d, 0),
            }
        )
    return points


def build_driver_statistics() -> dict:
    """Donut chart: driver verification / activity breakdown."""
    drivers = CustomUser.objects.filter(groups__name='Driver').distinct()
    total = drivers.count()

    approved = drivers.filter(
        driver_verification__status=DriverVerification.Status.APPROVED,
    ).count()
    in_review = drivers.filter(
        driver_verification__status=DriverVerification.Status.IN_REVIEW,
    ).count()
    rejected = drivers.filter(
        driver_verification__status=DriverVerification.Status.REJECTED,
    ).count()
    not_submitted = drivers.filter(
        Q(driver_verification__isnull=True)
        | Q(driver_verification__status=DriverVerification.Status.NOT_SUBMITTED)
    ).count()
    suspended = drivers.filter(is_active=False).count()

    pending = in_review + not_submitted

    breakdown = [
        {'key': 'approved', 'label': 'Approved Drivers', 'count': approved},
        {'key': 'pending', 'label': 'Pending Drivers', 'count': pending},
        {'key': 'in_review', 'label': 'In Review', 'count': in_review},
        {'key': 'not_submitted', 'label': 'Not Submitted', 'count': not_submitted},
        {'key': 'rejected', 'label': 'Rejected Drivers', 'count': rejected},
        {'key': 'suspended', 'label': 'Suspended Drivers', 'count': suspended},
    ]

    return {
        'total_drivers': total,
        'approved_drivers': approved,
        'pending_drivers': pending,
        'breakdown': breakdown,
    }


def build_recent_rides(limit: int = 10) -> list[dict]:
    """Recent rides table for admin dashboard."""
    orders = (
        Order.objects.select_related('user')
        .prefetch_related('order_items', 'order_drivers__driver')
        .order_by('-created_at')[:limit]
    )

    rows = []
    for o in orders:
        pickup, dropoff = _pickup_dropoff(o)
        fare = _order_trip_total(o)
        rider = o.user
        rider_name = (rider.get_full_name() or '').strip() or rider.email or rider.username
        status = o.status
        rows.append(
            {
                'ride_id': o.order_code or str(o.id),
                'order_id': o.id,
                'order_code': o.order_code,
                'rider_name': rider_name,
                'rider_id': rider.id,
                'driver_name': _accepted_driver_name(o),
                'pickup_address': pickup,
                'dropoff_address': dropoff,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'ride_fare': fare,
                'currency': 'USD',
                'status': status,
                'status_label': o.get_status_display(),
                'action': 'view_invoice' if status == Order.OrderStatus.COMPLETED else 'view_details',
            }
        )
    return rows
