"""
Service to send real-time WebSocket messages to drivers.
Used when order is assigned or when order times out.
Can be called from sync code (Celery, views, services).
"""
import logging
from asgiref.sync import async_to_sync
from django.utils import timezone

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
    ).select_related('order').prefetch_related('order__order_items')

    orders_data = []
    for order_driver in order_drivers:
        order = order_driver.order
        if order.status != Order.OrderStatus.PENDING:
            continue
        if order_driver.requested_at:
            elapsed = (timezone.now() - order_driver.requested_at).total_seconds()
            if elapsed >= DriverAssignmentService.TIMEOUT_SECONDS:
                continue  # Skip timed out - Celery will handle
        order_dict = _order_to_dict(order, driver)
        if order_dict:
            orders_data.append(order_dict)
    return orders_data


def _order_to_dict(order, driver=None):
    """
    Build order dict for WebSocket (matches DriverNearbyOrderSerializer structure).
    """
    first_item = order.order_items.first()
    if not first_item:
        return None

    result = {
        'id': order.id,
        'order_code': order.order_code,
        'status': order.status,
        'order_type': order.order_type,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'address_from': first_item.address_from,
        'address_to': first_item.address_to,
        'latitude_from': str(first_item.latitude_from) if first_item.latitude_from else None,
        'longitude_from': str(first_item.longitude_from) if first_item.longitude_from else None,
        'latitude_to': str(first_item.latitude_to) if first_item.latitude_to else None,
        'longitude_to': str(first_item.longitude_to) if first_item.longitude_to else None,
        'distance_to_pickup_km': None,
    }

    if driver and driver.latitude and driver.longitude and first_item.latitude_from and first_item.longitude_from:
        from .surge_pricing_service import calculate_distance
        distance = calculate_distance(
            float(driver.latitude), float(driver.longitude),
            float(first_item.latitude_from), float(first_item.longitude_from)
        )
        result['distance_to_pickup_km'] = round(float(distance), 2)

    return result


def send_new_order_to_driver(order, driver):
    """
    Send new_order WebSocket message to driver when order is assigned.
    Called from DriverAssignmentService.assign_order_to_driver and assign_to_next_driver.
    """
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        order_data = _order_to_dict(order, driver)
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
