"""
Service for finding and assigning nearest drivers to orders (Uber model).
Handles driver assignment with timeout and fallback to next nearest driver.
OPTIMIZED VERSION - Uses prefetch_related to avoid N+1 queries.
"""
import logging
from django.utils import timezone
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt
from django.db.models import Prefetch
from apps.accounts.models import CustomUser, DriverPreferences, VehicleDetails
from apps.order.models import Order, OrderItem, OrderDriver, RideType

logger = logging.getLogger(__name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on the earth (in kilometers)
    Using Haversine formula
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


class DriverAssignmentService:
    """
    Service for Uber-style driver assignment:
    - Find nearest available driver
    - Assign order to driver (OrderDriver with status=requested)
    - Handle timeout (25 seconds) and reassign to next driver
    - Radius-based search: first nearby (5km), then expand (10km, 15km, etc.)
    - Waiting time between search attempts to allow drivers to become available
    """
    
    TIMEOUT_SECONDS = 300  # 5 minutes timeout (300 seconds)
    SEARCH_RADIUSES = [5.0, 10.0, 15.0, 20.0]  # km - search in expanding circles
    WAIT_BETWEEN_RADIUSES = 10  # seconds - wait before expanding search radius
    MAX_DESTINATION_DISTANCE_KM = 3.0  # km - max distance from driver's destination to new pickup (Uber-style)
    
    @staticmethod
    def _is_driver_available(driver, new_order_pickup_lat=None, new_order_pickup_lon=None):
        """
        Check if driver is available (no active orders) OR 
        driver's current order destination is near new order pickup (Uber-style).
        
        OPTIMIZED: Uses prefetched data if available, otherwise falls back to query.
        
        Args:
            driver: CustomUser instance (driver)
            new_order_pickup_lat: New order pickup latitude (optional)
            new_order_pickup_lon: New order pickup longitude (optional)
        
        Returns:
            tuple: (is_available: bool, distance_from_destination: float or None, is_destination_match: bool)
        """
        # Use prefetched data if available (optimized path)
        if hasattr(driver, 'active_order_drivers'):
            active_order_drivers = driver.active_order_drivers
        else:
            # Fallback: query database (slower, but works if prefetch not used)
            active_order_drivers = OrderDriver.objects.filter(
                driver=driver,
                status=OrderDriver.DriverRequestStatus.ACCEPTED
            ).select_related('order').prefetch_related('order__order_items')
        
        # Check if any of these orders are still active
        for order_driver in active_order_drivers:
            if order_driver.order.status in [
                Order.OrderStatus.PENDING,  # Driver accept qilgan, lekin hali boshlanmagan
                Order.OrderStatus.CONFIRMED,  # Driver accept qilgan va ride boshlangan
            ]:
                # Driver has active order - check if destination is near new pickup (Uber-style)
                if new_order_pickup_lat and new_order_pickup_lon:
                    # Get driver's current order destination (final stop)
                    # Use prefetched order_items if available
                    current_order = order_driver.order
                    if hasattr(current_order, 'order_items'):
                        # Prefetched data - iterate through items
                        final_item = None
                        for item in current_order.order_items.all():
                            if item.is_final_stop:
                                final_item = item
                                break
                    else:
                        # Fallback: query database
                        final_item = current_order.order_items.filter(is_final_stop=True).first()
                    
                    if final_item and final_item.latitude_to and final_item.longitude_to:
                        # Calculate distance from driver's destination to new order pickup
                        distance_from_destination = calculate_distance(
                            float(final_item.latitude_to),
                            float(final_item.longitude_to),
                            float(new_order_pickup_lat),
                            float(new_order_pickup_lon)
                        )
                        
                        # If destination is near new pickup (within 3km), driver is available (Uber-style)
                        if distance_from_destination <= DriverAssignmentService.MAX_DESTINATION_DISTANCE_KM:
                            logger.info(
                                f"Driver {driver.id} has active order, but destination ({final_item.latitude_to}, {final_item.longitude_to}) "
                                f"is {distance_from_destination:.2f}km from new pickup ({new_order_pickup_lat}, {new_order_pickup_lon}) - "
                                f"driver is available (Uber-style matching)"
                            )
                            return True, distance_from_destination, True  # Available via destination matching
                
                # Driver has active order and destination is not near
                return False, None, False
        
        # Driver is completely available (no active orders)
        return True, None, False
    
    @staticmethod
    def find_nearest_available_driver(order, exclude_driver_ids=None, max_radius_km=None):
        """
        Find the nearest available driver for an order within specified radius.
        
        Args:
            order: Order instance
            exclude_driver_ids: List of driver IDs to exclude (already tried or rejected)
            max_radius_km: Maximum search radius in km (None = use driver's max_pickup_distance)
        
        Returns:
            CustomUser instance (driver) or None if no driver found
        """
        if exclude_driver_ids is None:
            exclude_driver_ids = []
        
        # Get first order item for pickup location
        first_item = order.order_items.first()
        if not first_item or not first_item.latitude_from or not first_item.longitude_from:
            return None
        
        pickup_lat = float(first_item.latitude_from)
        pickup_lon = float(first_item.longitude_from)
        
        # Get all drivers (users in Driver group) with OPTIMIZED prefetch_related
        from django.contrib.auth.models import Group
        try:
            driver_group = Group.objects.get(name='Driver')
            all_drivers = CustomUser.objects.filter(
                groups=driver_group,
                is_active=True,
                is_online=True,  # Only online drivers
                latitude__isnull=False,
                longitude__isnull=False
            ).exclude(id__in=exclude_driver_ids).prefetch_related(
                # Prefetch VehicleDetails - barcha driverlar uchun bir marta query
                Prefetch(
                    'vehicle_details',
                    queryset=VehicleDetails.objects.all(),
                    to_attr='vehicle_list'
                ),
                # Prefetch DriverPreferences - barcha driverlar uchun bir marta query
                Prefetch(
                    'driver_preferences',
                    queryset=DriverPreferences.objects.all(),
                    to_attr='prefs_list'
                ),
                # Prefetch active OrderDrivers va ularning order_items - destination matching uchun
                Prefetch(
                    'order_drivers',
                    queryset=OrderDriver.objects.filter(
                        status=OrderDriver.DriverRequestStatus.ACCEPTED
                    ).select_related('order').prefetch_related(
                        Prefetch(
                            'order__order_items',
                            queryset=OrderItem.objects.all(),
                            to_attr='order_items_list'
                        )
                    ),
                    to_attr='active_order_drivers'
                ),
            )
        except Group.DoesNotExist:
            return None
        
        # Convert to list to avoid multiple queries and enable prefetch access
        all_drivers_list = list(all_drivers)
        
        # Pre-calculate vehicle existence and preferences (from prefetched data)
        driver_vehicles = {}
        driver_prefs = {}
        for driver in all_drivers_list:
            driver_vehicles[driver.id] = bool(getattr(driver, 'vehicle_list', []))
            prefs_list = getattr(driver, 'prefs_list', [])
            driver_prefs[driver.id] = prefs_list[0] if prefs_list else None
        
        # Filter drivers who have vehicle, are available, and within radius
        driver_distances = []
        for driver in all_drivers_list:
            # Check vehicle (from prefetched data - no database query!)
            if not driver_vehicles.get(driver.id, False):
                continue
            
            # Check if driver is available (uses prefetched data if available)
            is_available, distance_from_destination, is_destination_match = DriverAssignmentService._is_driver_available(
                driver,
                new_order_pickup_lat=pickup_lat,
                new_order_pickup_lon=pickup_lon
            )
            
            if not is_available:
                continue
            
            # Calculate distance - use destination distance if driver has active order (Uber-style)
            if is_destination_match and distance_from_destination is not None:
                # Driver has active order, but destination is near - use destination distance
                distance = distance_from_destination
                logger.info(
                    f"Driver {driver.id} matched via destination (Uber-style): "
                    f"destination is {distance:.2f}km from new pickup"
                )
            else:
                # Driver is completely free - use current location distance
                distance = calculate_distance(
                    pickup_lat, pickup_lon,
                    float(driver.latitude), float(driver.longitude)
                )
            
            # Get driver preferences (from prefetched data - no database query!)
            prefs = driver_prefs.get(driver.id)
            driver_max_distance_km = 5.0  # default
            if prefs and prefs.maximum_pickup_distance:
                try:
                    driver_max_distance_km = float(prefs.maximum_pickup_distance)
                except (ValueError, TypeError):
                    driver_max_distance_km = 5.0
            
            # For destination matching, use MAX_DESTINATION_DISTANCE_KM instead of driver's max_pickup_distance
            if is_destination_match:
                effective_max_distance = DriverAssignmentService.MAX_DESTINATION_DISTANCE_KM
            else:
                # Use the smaller of: max_radius_km (if specified) or driver's max_pickup_distance
                effective_max_distance = driver_max_distance_km
                if max_radius_km is not None:
                    effective_max_distance = min(max_radius_km, driver_max_distance_km)
            
            # Only include if within effective max distance
            if distance <= effective_max_distance:
                driver_distances.append((driver, distance))
        
        if not driver_distances:
            return None
        
        # Sort by distance and return nearest
        driver_distances.sort(key=lambda x: x[1])
        nearest_driver, _ = driver_distances[0]
        
        return nearest_driver
    
    @staticmethod
    def assign_order_to_driver(order, driver):
        """
        Assign order to a driver by creating OrderDriver with status=requested.
        OPTIMIZED: Push notification sent asynchronously via Celery task.
        
        Args:
            order: Order instance
            driver: CustomUser instance (driver)
        
        Returns:
            OrderDriver instance
        """
        from django.utils import timezone
        
        order_driver, created = OrderDriver.objects.get_or_create(
            order=order,
            driver=driver,
            defaults={
                'status': OrderDriver.DriverRequestStatus.REQUESTED,
                'requested_at': timezone.now(),
            }
        )
        
        if not created:
            # Update if already exists
            order_driver.status = OrderDriver.DriverRequestStatus.REQUESTED
            order_driver.requested_at = timezone.now()
            order_driver.save()
        
        # Send push notification ASYNC (non-blocking) via Celery task
        try:
            from apps.notification.tasks import send_push_notification_async
            send_push_notification_async.delay(
                user_id=driver.id,
                title="New ride request",
                body=f"New ride request available nearby. Order: {order.order_code}",
                data={
                    "order_id": order.id,
                    "order_code": order.order_code,
                    "type": "ride_request"
                }
            )
        except ImportError:
            # Fallback to sync if Celery task not available
            logger.warning("Celery task not available, using sync push notification")
            from apps.notification.services import send_push_to_user
            try:
                send_push_to_user(
                    user=driver,
                    title="New ride request",
                    body=f"New ride request available nearby. Order: {order.order_code}",
                    data={
                        "order_id": order.id,
                        "order_code": order.order_code,
                        "type": "ride_request"
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send push notification to driver {driver.id}: {e}")
        except Exception as e:
            # Log error but don't fail assignment
            logger.error(f"Failed to send async push notification to driver {driver.id}: {e}")

        # Real-time WebSocket: notify driver of new order
        try:
            from .driver_orders_websocket import send_new_order_to_driver
            send_new_order_to_driver(order, driver)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket new_order to driver {driver.id}: {e}")

        return order_driver
    
    @staticmethod
    def check_and_handle_timeout(order):
        """
        Check if current driver request has timed out and reassign to next driver.
        
        Args:
            order: Order instance
        
        Returns:
            OrderDriver instance (new assignment) or None if no more drivers
        """
        # Get current requested driver (not responded yet)
        current_request = OrderDriver.objects.filter(
            order=order,
            status=OrderDriver.DriverRequestStatus.REQUESTED
        ).first()
        
        if not current_request:
            # No current request, try to assign to first available driver
            return DriverAssignmentService.assign_to_next_driver(order)
        
        # Check if timeout
        if current_request.requested_at:
            time_elapsed = timezone.now() - current_request.requested_at
            if time_elapsed.total_seconds() >= DriverAssignmentService.TIMEOUT_SECONDS:
                # Mark current as timeout
                current_request.status = OrderDriver.DriverRequestStatus.TIMEOUT
                current_request.save()
                
                # Get all tried driver IDs (rejected, timeout)
                exclude_ids = list(
                    OrderDriver.objects.filter(order=order)
                    .exclude(status=OrderDriver.DriverRequestStatus.ACCEPTED)
                    .values_list('driver_id', flat=True)
                )
                
                # Find next nearest driver using radius-based search
                next_order_driver = DriverAssignmentService.assign_to_next_driver(
                    order, use_radius_search=True
                )
                
                if next_order_driver:
                    return next_order_driver
                else:
                    # No more drivers available
                    return None
        
        return None
    
    @staticmethod
    def assign_to_next_driver(order, use_radius_search=True):
        """
        Assign order to next available driver using radius-based search.
        First searches nearby (5km), then expands if no driver found.
        
        Args:
            order: Order instance
            use_radius_search: If True, use expanding radius search with waiting
        
        Returns:
            OrderDriver instance or None if no driver found
        """
        # Get all tried driver IDs
        exclude_ids = list(
            OrderDriver.objects.filter(order=order)
            .exclude(status=OrderDriver.DriverRequestStatus.ACCEPTED)
            .values_list('driver_id', flat=True)
        )
        
        if not use_radius_search:
            # Simple search - no radius expansion
            nearest_driver = DriverAssignmentService.find_nearest_available_driver(
                order, exclude_driver_ids=exclude_ids
            )
            if nearest_driver:
                return DriverAssignmentService.assign_order_to_driver(order, nearest_driver)
            return None
        
        # Radius-based search: try first radius immediately
        first_radius_km = DriverAssignmentService.SEARCH_RADIUSES[0]
        nearest_driver = DriverAssignmentService.find_nearest_available_driver(
            order, exclude_driver_ids=exclude_ids, max_radius_km=first_radius_km
        )
        
        if nearest_driver:
            # Found driver in first radius - assign immediately
            return DriverAssignmentService.assign_order_to_driver(order, nearest_driver)
        
        # No driver found in first radius - schedule delayed search with next radius
        if len(DriverAssignmentService.SEARCH_RADIUSES) > 1:
            from apps.order.tasks import assign_order_with_radius_delayed
            assign_order_with_radius_delayed.apply_async(
                args=[order.id, first_radius_km],
                countdown=DriverAssignmentService.WAIT_BETWEEN_RADIUSES
            )
            logger.info(
                f"Order {order.id} - no driver found in {first_radius_km}km radius. "
                f"Scheduling expanded search in {DriverAssignmentService.WAIT_BETWEEN_RADIUSES} seconds"
            )
            return None  # Will be assigned later via Celery
        
        # No driver found in any radius
        return None

