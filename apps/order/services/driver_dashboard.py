"""Driver dashboard: overview, cash_history, ride_history. Filters: day, week, last_30, range."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import CustomUser
from ..models import Order, OrderDriver, DriverCashout, TripRating


def _parse_filter(filter_type, start_date, end_date):
    """
    Returns (dt_start, dt_end) for filtering.
    filter_type: 'day' | 'week' | 'last_30' | 'range'
    """
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if filter_type == 'day':
        return today, now
    if filter_type == 'week':
        return today - timedelta(days=7), now
    if filter_type == 'last_30':
        return today - timedelta(days=30), now
    if filter_type == 'range' and start_date and end_date:
        from datetime import datetime
        try:
            start = datetime.strptime(str(start_date)[:10], '%Y-%m-%d')
            end = datetime.strptime(str(end_date)[:10], '%Y-%m-%d')
            start = timezone.make_aware(start) if timezone.is_naive(start) else start
            end = timezone.make_aware(end) if timezone.is_naive(end) else end
            end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end
        except (ValueError, TypeError):
            pass
    return today - timedelta(days=30), now


def get_driver_dashboard(user_id, ride_limit=10, filter_type='last_30', start_date=None, end_date=None):
    """Returns (overview, cash_history, ride_history). All filtered by date."""
    user = CustomUser.objects.get(id=user_id)
    dt_start, dt_end = _parse_filter(filter_type, start_date, end_date)

    base = Order.objects.filter(
        order_drivers__driver=user,
        order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
        status=Order.OrderStatus.COMPLETED,
    ).prefetch_related('order_items')

    orders_qs = base.filter(updated_at__gte=dt_start, updated_at__lte=dt_end)

    def _sum_price(qs):
        total = Decimal('0')
        for o in qs:
            for i in o.order_items.all():
                if i.calculated_price:
                    total += Decimal(str(i.calculated_price))
        return total

    order_list = list(orders_qs)
    earnings = _sum_price(order_list)
    tip_val = TripRating.objects.filter(
        driver=user, status='approved',
        order__updated_at__gte=dt_start, order__updated_at__lte=dt_end
    ).aggregate(s=Sum('tip_amount'))['s'] or Decimal('0')

    overview_item = {
        'rides': len(order_list),
        'made_in_today': float(earnings),
        'made_in_week': float(earnings),
        'tip': float(tip_val),
        'promotion': 0.0,
    }

    cashouts = list(DriverCashout.objects.filter(
        driver=user, created_at__gte=dt_start, created_at__lte=dt_end
    ).order_by('-created_at')[:20])
    from ..serializers.driver import DriverCashoutSerializer
    cash_history = DriverCashoutSerializer(cashouts, many=True).data

    ride_orders = list(base.filter(
        updated_at__gte=dt_start, updated_at__lte=dt_end
    ).select_related('user').prefetch_related('order_items__ride_type').order_by('-updated_at')[:ride_limit])
    from ..serializers.order import OrderSerializer
    ride_history = OrderSerializer(ride_orders, many=True).data

    return [overview_item], cash_history, ride_history


def get_cash_history(user_id, filter_type='last_30', start_date=None, end_date=None, page=1, page_size=20):
    """Paginated cash history for See all. Returns (list, total_count)."""
    user = CustomUser.objects.get(id=user_id)
    dt_start, dt_end = _parse_filter(filter_type, start_date, end_date)

    qs = DriverCashout.objects.filter(
        driver=user, created_at__gte=dt_start, created_at__lte=dt_end
    ).order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    items = list(qs[start : start + page_size])
    from ..serializers.driver import DriverCashoutSerializer
    data = DriverCashoutSerializer(items, many=True).data
    return data, total


def get_ride_history(user_id, filter_type='last_30', start_date=None, end_date=None, page=1, page_size=10):
    """Paginated ride history. Returns (list, total_count)."""
    user = CustomUser.objects.get(id=user_id)
    dt_start, dt_end = _parse_filter(filter_type, start_date, end_date)

    base = Order.objects.filter(
        order_drivers__driver=user,
        order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
        status=Order.OrderStatus.COMPLETED,
        updated_at__gte=dt_start, updated_at__lte=dt_end,
    ).select_related('user').prefetch_related('order_items__ride_type').order_by('-updated_at')
    total = base.count()
    start = (page - 1) * page_size
    orders = list(base[start : start + page_size])
    from ..serializers.order import OrderSerializer
    data = OrderSerializer(orders, many=True).data
    return data, total
