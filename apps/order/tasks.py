"""
Celery tasks for order management.
Handles automatic timeout checking and driver reassignment.
OPTIMIZED: Async driver assignment to avoid blocking order creation.
"""
import logging
from celery import shared_task
from django.utils import timezone
from apps.order.models import Order, OrderDriver
from apps.order.services.driver_assignment_service import DriverAssignmentService

logger = logging.getLogger(__name__)


@shared_task(name='apps.order.tasks.check_order_timeouts')
def check_order_timeouts():
    """
    Periodic task: Har 5 soniyada timeout bo'lgan orderlarni tekshirish
    va keyingi driverga yuborish.
    
    Bu task Celery Beat tomonidan avtomatik chaqiriladi.
    """
    logger.info("Starting check_order_timeouts task...")
    
    # Barcha requested statusdagi OrderDriver larni topish
    requested_order_drivers = OrderDriver.objects.filter(
        status=OrderDriver.DriverRequestStatus.REQUESTED
    ).select_related('order', 'driver')
    
    timeout_count = 0
    reassigned_count = 0
    
    for order_driver in requested_order_drivers:
        # Faqat pending orderlar uchun tekshirish
        if order_driver.order.status != Order.OrderStatus.PENDING:
            continue
        
        # Timeout tekshirish
        if order_driver.requested_at:
            time_elapsed = timezone.now() - order_driver.requested_at
            elapsed_seconds = time_elapsed.total_seconds()
            
            if elapsed_seconds >= DriverAssignmentService.TIMEOUT_SECONDS:
                logger.info(
                    f"Order {order_driver.order.id} timeout detected for driver {order_driver.driver.id}. "
                    f"Elapsed: {elapsed_seconds:.2f} seconds"
                )
                
                # Mark as timeout
                order_driver.status = OrderDriver.DriverRequestStatus.TIMEOUT
                order_driver.save()
                timeout_count += 1
                
                # Reassign to next driver
                try:
                    next_order_driver = DriverAssignmentService.assign_to_next_driver(order_driver.order)
                    if next_order_driver:
                        reassigned_count += 1
                        logger.info(
                            f"Order {order_driver.order.id} reassigned to driver {next_order_driver.driver.id}"
                        )
                    else:
                        logger.warning(
                            f"Order {order_driver.order.id} could not be reassigned - no more drivers available"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to reassign order {order_driver.order.id} after timeout: {e}",
                        exc_info=True
                    )
    
    logger.info(
        f"check_order_timeouts task completed. "
        f"Timeouts: {timeout_count}, Reassigned: {reassigned_count}"
    )
    
    return {
        'timeouts': timeout_count,
        'reassigned': reassigned_count,
    }


@shared_task(name='apps.order.tasks.assign_order_with_radius_delayed')
def assign_order_with_radius_delayed(order_id, last_radius_km):
    """
    Delayed task: Radius-based driver search with waiting.
    Searches for driver in expanding radius (5km, 10km, 15km, etc.)
    
    Args:
        order_id: Order ID
        last_radius_km: Last radius that was checked (to continue from next radius)
    
    Returns:
        OrderDriver instance or None
    """
    logger.info(
        f"Starting assign_order_with_radius_delayed for order {order_id}, "
        f"last_radius: {last_radius_km}km"
    )
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return None
    
    # Check if order is still pending (not already assigned)
    if order.status != Order.OrderStatus.PENDING:
        logger.info(f"Order {order_id} is no longer pending (status: {order.status})")
        return None
    
    # Get all tried driver IDs
    exclude_ids = list(
        OrderDriver.objects.filter(order=order)
        .exclude(status=OrderDriver.DriverRequestStatus.ACCEPTED)
        .values_list('driver_id', flat=True)
    )
    
    # Find next radius to check
    try:
        last_radius_index = DriverAssignmentService.SEARCH_RADIUSES.index(last_radius_km)
        next_radius_index = last_radius_index + 1
    except (ValueError, IndexError):
        # Last radius not found or already at last radius
        next_radius_index = 0
    
    if next_radius_index >= len(DriverAssignmentService.SEARCH_RADIUSES):
        # All radii checked, no driver found
        logger.warning(f"Order {order_id} - no driver found in any radius")
        return None
    
    next_radius_km = DriverAssignmentService.SEARCH_RADIUSES[next_radius_index]
    logger.info(f"Searching for driver in radius {next_radius_km}km for order {order_id}")
    
    # Search for driver in this radius
    nearest_driver = DriverAssignmentService.find_nearest_available_driver(
        order, exclude_driver_ids=exclude_ids, max_radius_km=next_radius_km
    )
    
    if nearest_driver:
        # Found driver - assign immediately
        logger.info(f"Found driver {nearest_driver.id} in radius {next_radius_km}km for order {order_id}")
        return DriverAssignmentService.assign_order_to_driver(order, nearest_driver)
    
    # No driver found in this radius - schedule next radius search
    if next_radius_index < len(DriverAssignmentService.SEARCH_RADIUSES) - 1:
        logger.info(
            f"No driver found in radius {next_radius_km}km for order {order_id}. "
            f"Scheduling next radius search in {DriverAssignmentService.WAIT_BETWEEN_RADIUSES} seconds"
        )
        assign_order_with_radius_delayed.apply_async(
            args=[order_id, next_radius_km],
            countdown=DriverAssignmentService.WAIT_BETWEEN_RADIUSES
        )
    else:
        logger.warning(f"Order {order_id} - no driver found in any radius")
    
    return None


@shared_task(name='apps.order.tasks.assign_driver_to_order_async')
def assign_driver_to_order_async(order_id):
    """
    Async task: Assign driver to order (non-blocking).
    This task is called after order creation to avoid blocking the API response.
    
    Args:
        order_id: Order ID
    
    Returns:
        OrderDriver instance or None
    """
    logger.info(f"Starting assign_driver_to_order_async for order {order_id}")
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for async driver assignment")
        return None
    
    # Check if order is still pending (not already assigned)
    if order.status != Order.OrderStatus.PENDING:
        logger.info(f"Order {order_id} is no longer pending (status: {order.status}). Skipping driver assignment.")
        return None
    
    try:
        # Assign to nearest driver using optimized service
        order_driver = DriverAssignmentService.assign_to_next_driver(order)
        if order_driver:
            logger.info(f"Order {order_id} assigned to driver {order_driver.driver.id} via async task")
            # Return JSON-serializable dict instead of OrderDriver object
            return {
                'order_id': order_id,
                'driver_id': order_driver.driver.id,
                'order_driver_id': order_driver.id,
                'status': 'assigned'
            }
        else:
            logger.info(f"Order {order_id} - no driver found (will retry with expanded radius)")
            return {'order_id': order_id, 'status': 'no_driver_found'}
    except Exception as e:
        logger.error(
            f"Failed to assign driver to order {order_id} via async task: {e}",
            exc_info=True
        )
        return {'order_id': order_id, 'status': 'error', 'error': str(e)}

