"""
Service to send real-time WebSocket messages to drivers.
Used when order is assigned, times out, or is cancelled by the rider.
Can be called from sync code (Celery, views, services).
"""
import logging
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.db.models import Avg, Count, Q
from .rider_orders_websocket import _media_absolute_url

from ..models import TripRating

logger = logging.getLogger(__name__)


def get_driver_current_orders(driver):
    """
    Get list of current pending orders for driver (REQUESTED, not timed out).
    Used when driver connects to WebSocket - send initial orders.
    """
    from .driver_assignment_service import DriverAssignmentService
    from ..models import Order, OrderDriver

    order_drivers = OrderDriver.objects.filter(
        driver=driver,
        status=OrderDriver.DriverRequestStatus.REQUESTED
    ).select_related('order', 'order__user').prefetch_related('order__order_items__ride_type')

    orders_data = []
    for order_driver in order_drivers:
        order = order_driver.order
        if order.status != Order.OrderStatus.PENDING:
            continue
        if order_driver.requested_at:
            elapsed = (timezone.now() - order_driver.requested_at).total_seconds()
            if elapsed >= DriverAssignmentService.TIMEOUT_SECONDS:
                continue  # Skip timed out - Celery will handle
        order_dict = _order_to_dict(order, driver, order_driver.requested_at)
        if order_dict:
            orders_data.append(order_dict)
    return orders_data


def _order_to_dict(order, driver=None, requested_at=None):
    """
    Build order dict for WebSocket.
    Includes: vaqt (time), client (rider) info, net_price.
    """
    first_item = order.order_items.first()
    if not first_item:
        return None

    net_price = 0
    for item in order.order_items.all():
        price = item.adjusted_price or item.calculated_price or item.original_price
        if price is not None:
            net_price += float(price)
        elif item.ride_type and item.distance_km:
            try:
                calculated = item.ride_type.calculate_price(float(item.distance_km))
                net_price += float(calculated)
            except (TypeError, ValueError, AttributeError):
                pass
        elif item.distance_km:
            # No price/ride_type yet: use first active RideType for estimated price so driver sees non-zero
            try:
                from ..models import RideType
                fallback_ride = RideType.objects.filter(is_active=True).order_by('id').first()
                if fallback_ride and fallback_ride.base_price is not None and fallback_ride.price_per_km is not None:
                    estimated = fallback_ride.calculate_price(float(item.distance_km))
                    net_price += float(estimated)
            except (TypeError, ValueError, AttributeError):
                pass
    net_price = round(net_price, 2) if net_price else 0

    user = order.user
    client_info = None
    client_rating = None
    client_tip_count = 0
    if user:
        avatar_url = None
        if user.avatar:
            try:
                avatar_url = _media_absolute_url(user.avatar.url)
            except (ValueError, AttributeError):
                avatar_url = None
        client_info = {
            'id': user.id,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'full_name': user.get_full_name() or user.email or '',
            'phone_number': user.phone_number or '',
            'email': user.email or '',
            'avatar': avatar_url,
        }
        agg = TripRating.objects.filter(
            rider_id=user.id,
            status='approved',
        ).aggregate(
            avg=Avg('rating'),
            tip_count=Count('id', filter=Q(tip_amount__gt=0)),
        )
        if agg['avg'] is not None:
            client_rating = round(float(agg['avg']), 2)
        client_tip_count = agg['tip_count'] or 0

    ride_type_info = None
    if first_item.ride_type_id:
        rt = first_item.ride_type
        ride_type_info = {
            'id': rt.id,
            'name': rt.name or rt.name_large or '',
            'name_large': rt.name_large or '',
        }

    result = {
        'id': order.id,
        'order_code': order.order_code,
        'status': order.status,
        'order_type': order.order_type,
        'ride_type': ride_type_info,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'requested_at': requested_at.isoformat() if requested_at else None,
        'estimated_time': first_item.estimated_time,
        'address_from': first_item.address_from,
        'address_to': first_item.address_to,
        'latitude_from': str(first_item.latitude_from) if first_item.latitude_from else None,
        'longitude_from': str(first_item.longitude_from) if first_item.longitude_from else None,
        'latitude_to': str(first_item.latitude_to) if first_item.latitude_to else None,
        'longitude_to': str(first_item.longitude_to) if first_item.longitude_to else None,
        'distance_to_pickup_km': None,
        'net_price': net_price,
        'client': client_info,
        'client_rating': client_rating,
        'client_tip_count': client_tip_count,
    }

    if driver and driver.latitude and driver.longitude and first_item.latitude_from and first_item.longitude_from:
        from .surge_pricing_service import calculate_distance
        distance = calculate_distance(
            float(driver.latitude), float(driver.longitude),
            float(first_item.latitude_from), float(first_item.longitude_from)
        )
        result['distance_to_pickup_km'] = round(float(distance), 2)

    return result


def send_new_order_to_driver(order, driver, requested_at=None):
    """
    Send new_order WebSocket message to driver when order is assigned.
    Called from DriverAssignmentService.assign_order_to_driver and assign_to_next_driver.
    """
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        order_data = _order_to_dict(order, driver, requested_at)
        if not order_data:
            return

        group_name = f'driver_orders_{driver.id}'
        message = {
            'type': 'new_order',
            'order': order_data,
            'message': 'New ride request available',
        }

        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.info(f"WebSocket new_order sent to driver {driver.id} for order {order.id}")
    except Exception as e:
        logger.warning(f"Failed to send WebSocket new_order to driver: {e}")


def send_order_timeout_to_driver(driver_id, order_id):
    """
    Send order_timeout WebSocket message to driver when order is removed (timeout/reassigned).
    Called from check_order_timeouts task and DriverNearbyOrdersView.
    """
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        group_name = f'driver_orders_{driver_id}'
        message = {
            'type': 'order_timeout',
            'order_id': order_id,
            'message': 'Order expired or reassigned to another driver',
        }

        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.info(f"WebSocket order_timeout sent to driver {driver_id} for order {order_id}")
    except Exception as e:
        logger.warning(f"Failed to send WebSocket order_timeout to driver {driver_id}: {e}")


def notify_drivers_order_cancelled_by_rider(order_id: int, request=None):
    """
    After rider cancels: notify every driver who still had this order as REQUESTED or ACCEPTED.
    Payload uses OrderDetailSerializer (same shape as REST) plus cancel metadata.
    """
    from channels.layers import get_channel_layer
    from ..models import Order, OrderDriver
    from apps.order.serializers.order import OrderDetailSerializer

    order = (
        Order.objects.filter(pk=order_id)
        .select_related('user')
        .prefetch_related(
            'order_items__ride_type',
            'order_drivers__driver',
            'cancel_orders',
        )
        .first()
    )
    if not order:
        logger.warning(
            'notify_drivers_order_cancelled_by_rider: order %s not found', order_id
        )
        return

    ctx = {'request': request} if request is not None else {}
    order_data = OrderDetailSerializer(order, context=ctx).data

    cancel = order.cancel_orders.first()
    cancel_data = None
    if cancel:
        cancel_data = {
            'cancelled_by': cancel.cancelled_by,
            'reason': cancel.reason,
            'other_reason': cancel.other_reason,
            'created_at': cancel.created_at.isoformat() if cancel.created_at else None,
        }
        if cancel.driver_id:
            cancel_data['order_driver_id'] = cancel.driver_id

    driver_ids = list(
        OrderDriver.objects.filter(
            order_id=order_id,
            status__in=(
                OrderDriver.DriverRequestStatus.REQUESTED,
                OrderDriver.DriverRequestStatus.ACCEPTED,
            ),
        )
        .values_list('driver_id', flat=True)
        .distinct()
    )

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    if not driver_ids:
        logger.debug(
            'notify_drivers_order_cancelled_by_rider: no REQUESTED/ACCEPTED drivers for order %s',
            order_id,
        )
        return

    message = {
        'type': 'order_cancelled_by_rider',
        'change': 'cancelled_rider',
        'message': 'The rider cancelled this ride.',
        'order': order_data,
        'cancel': cancel_data,
    }

    for did in driver_ids:
        try:
            async_to_sync(channel_layer.group_send)(f'driver_orders_{did}', message)
            logger.info(
                'WebSocket order_cancelled_by_rider sent to driver %s for order %s',
                did,
                order_id,
            )
        except Exception as e:
            logger.warning(
                'Failed WebSocket order_cancelled_by_rider to driver %s: %s', did, e
            )

    try:
        from apps.notification.services import enqueue_push_to_user_id

        for did in driver_ids:
            enqueue_push_to_user_id(
                did,
                title='Ride cancelled',
                body='The rider cancelled this ride.',
                data={
                    'type': 'ride_cancelled_by_rider',
                    'order_id': order.id,
                    'order_code': order.order_code or '',
                },
            )
    except Exception as e:
        logger.warning(
            'Failed FCM ride_cancelled_by_rider for order %s drivers %s: %s',
            order_id,
            driver_ids,
            e,
        )
