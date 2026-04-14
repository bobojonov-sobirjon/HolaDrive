"""
Active ride resolution: orders still in progress (resume after app restart).
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from ..models import Order, OrderDriver
from ..serializers.order import OrderDetailSerializer

# Not terminal: rider/driver can continue the flow
ACTIVE_RIDE_ORDER_STATUSES = frozenset({
    Order.OrderStatus.PENDING,
    Order.OrderStatus.ACCEPTED,
    Order.OrderStatus.ON_THE_WAY,
    Order.OrderStatus.ARRIVED,
    Order.OrderStatus.IN_PROGRESS,
})
TERMINAL_ORDER_STATUSES = frozenset({
    Order.OrderStatus.COMPLETED,
    Order.OrderStatus.CANCELLED,
    Order.OrderStatus.REJECTED,
})


def _order_detail_prefetch(queryset):
    return queryset.select_related('user').prefetch_related(
        'order_items__ride_type',
        'order_preferences',
        'order_drivers__driver__vehicle_details__images',
        'additional_passengers',
    )


def get_rider_active_order(user):
    """
    Latest order owned by user whose status is still "in flow" (pending through in_progress).
    """
    qs = Order.objects.filter(
        user=user,
        status__in=ACTIVE_RIDE_ORDER_STATUSES,
    ).order_by('-updated_at')
    return _order_detail_prefetch(qs).first()


def get_driver_active_order(user):
    """
    Order where this driver has ACCEPTED assignment and order is still in flow.
    """
    od = (
        OrderDriver.objects.filter(
            driver=user,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
            order__status__in=ACTIVE_RIDE_ORDER_STATUSES,
        )
        .select_related('order', 'order__user')
        .prefetch_related(
            'order__order_items__ride_type',
            'order__order_preferences',
            'order__order_drivers__driver__vehicle_details__images',
            'order__additional_passengers',
        )
        .order_by('-order__updated_at')
        .first()
    )
    return od.order if od else None


def _serialize_order(order):
    return OrderDetailSerializer(order, context={}).data


def notify_rider_active_ride_snapshot(user_id: int, order=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f'rider_orders_{user_id}',
        {
            'type': 'active_ride_snapshot',
            'has_active_ride': bool(order),
            'order': _serialize_order(order) if order else None,
            'scope': 'rider',
            'checked_at': timezone.now().isoformat(),
            'message': 'Active ride status refreshed',
        },
    )


def notify_driver_active_ride_snapshot(user_id: int, order=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f'driver_orders_{user_id}',
        {
            'type': 'active_ride_snapshot',
            'has_active_ride': bool(order),
            'order': _serialize_order(order) if order else None,
            'scope': 'driver',
            'checked_at': timezone.now().isoformat(),
            'message': 'Active ride status refreshed',
        },
    )
