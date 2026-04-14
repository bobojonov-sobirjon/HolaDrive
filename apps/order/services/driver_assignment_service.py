import logging
from django.utils import timezone
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt
from django.db.models import Prefetch
from apps.accounts.models import CustomUser, DriverPreferences, VehicleDetails
from apps.order.models import Order, OrderItem, OrderDriver, RideType

logger = logging.getLogger(__name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    r = 6371
    
    return c * r


class DriverAssignmentService:
    
    TIMEOUT_SECONDS = 20
    SEARCH_RADIUSES = [5.0, 10.0, 15.0, 20.0]
    WAIT_BETWEEN_RADIUSES = 10
    MAX_DESTINATION_DISTANCE_KM = 3.0
    
    @staticmethod
    def _is_driver_available(driver, new_order_pickup_lat=None, new_order_pickup_lon=None):
        if hasattr(driver, 'active_order_drivers'):
            active_order_drivers = driver.active_order_drivers
        else:
            active_order_drivers = OrderDriver.objects.filter(
                driver=driver,
                status=OrderDriver.DriverRequestStatus.ACCEPTED
            ).select_related('order').prefetch_related('order__order_items')
        
        for order_driver in active_order_drivers:
            if order_driver.order.status in [
                Order.OrderStatus.PENDING,
                Order.OrderStatus.ACCEPTED,
                Order.OrderStatus.ON_THE_WAY,
                Order.OrderStatus.ARRIVED,
                Order.OrderStatus.IN_PROGRESS,
            ]:
                if new_order_pickup_lat and new_order_pickup_lon:
                    current_order = order_driver.order
                    if hasattr(current_order, 'order_items'):
                        final_item = None
                        for item in current_order.order_items.all():
                            if item.is_final_stop:
                                final_item = item
                                break
                    else:
                        final_item = current_order.order_items.filter(is_final_stop=True).first()
                    
                    if final_item and final_item.latitude_to and final_item.longitude_to:
                        distance_from_destination = calculate_distance(
                            float(final_item.latitude_to),
                            float(final_item.longitude_to),
                            float(new_order_pickup_lat),
                            float(new_order_pickup_lon)
                        )
                        
                        if distance_from_destination <= DriverAssignmentService.MAX_DESTINATION_DISTANCE_KM:
                            logger.info(
                                f"Driver {driver.id} has active order, but destination ({final_item.latitude_to}, {final_item.longitude_to}) "
                                f"is {distance_from_destination:.2f}km from new pickup ({new_order_pickup_lat}, {new_order_pickup_lon}) - "
                                f"driver is available (Uber-style matching)"
                            )
                            return True, distance_from_destination, True
                
                return False, None, False
        
        return True, None, False
    
    @staticmethod
    def find_nearest_available_driver(order, exclude_driver_ids=None, max_radius_km=None):
        if exclude_driver_ids is None:
            exclude_driver_ids = []
        
        first_item = order.order_items.first()
        if not first_item or not first_item.latitude_from or not first_item.longitude_from:
            return None
        
        pickup_lat = float(first_item.latitude_from)
        pickup_lon = float(first_item.longitude_from)
        
        from django.contrib.auth.models import Group
        try:
            driver_group = Group.objects.get(name='Driver')
            all_drivers = CustomUser.objects.filter(
                groups=driver_group,
                is_active=True,
                is_online=True,
                latitude__isnull=False,
                longitude__isnull=False
            ).exclude(id__in=exclude_driver_ids).prefetch_related(
                Prefetch(
                    'vehicle_details',
                    queryset=VehicleDetails.objects.all(),
                    to_attr='vehicle_list'
                ),
                Prefetch(
                    'driver_preferences',
                    queryset=DriverPreferences.objects.all(),
                    to_attr='prefs_list'
                ),
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
        
        all_drivers_list = list(all_drivers)
        
        driver_vehicles = {}
        driver_prefs = {}
        for driver in all_drivers_list:
            driver_vehicles[driver.id] = bool(getattr(driver, 'vehicle_list', []))
            prefs_list = getattr(driver, 'prefs_list', [])
            driver_prefs[driver.id] = prefs_list[0] if prefs_list else None
        
        driver_distances = []
        for driver in all_drivers_list:
            if not driver_vehicles.get(driver.id, False):
                continue
            
            is_available, distance_from_destination, is_destination_match = DriverAssignmentService._is_driver_available(
                driver,
                new_order_pickup_lat=pickup_lat,
                new_order_pickup_lon=pickup_lon
            )
            
            if not is_available:
                continue
            
            if is_destination_match and distance_from_destination is not None:
                distance = distance_from_destination
                logger.info(
                    f"Driver {driver.id} matched via destination (Uber-style): "
                    f"destination is {distance:.2f}km from new pickup"
                )
            else:
                distance = calculate_distance(
                    pickup_lat, pickup_lon,
                    float(driver.latitude), float(driver.longitude)
                )
            
            prefs = driver_prefs.get(driver.id)
            driver_max_distance_km = 5.0
            if prefs and prefs.maximum_pickup_distance:
                try:
                    driver_max_distance_km = float(prefs.maximum_pickup_distance)
                except (ValueError, TypeError):
                    driver_max_distance_km = 5.0
            
            if is_destination_match:
                effective_max_distance = DriverAssignmentService.MAX_DESTINATION_DISTANCE_KM
            else:
                effective_max_distance = driver_max_distance_km
                if max_radius_km is not None:
                    effective_max_distance = min(max_radius_km, driver_max_distance_km)
            
            if distance <= effective_max_distance:
                driver_distances.append((driver, distance))
        
        if not driver_distances:
            return None
        
        driver_distances.sort(key=lambda x: x[1])
        nearest_driver, _ = driver_distances[0]
        
        return nearest_driver
    
    @staticmethod
    def assign_order_to_driver(order, driver):
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
            order_driver.status = OrderDriver.DriverRequestStatus.REQUESTED
            order_driver.requested_at = timezone.now()
            order_driver.save()
        
        try:
            from apps.notification.tasks import send_push_notification_async

            logger.info(
                "[PUSH DEBUG] assign_order_to_driver: enqueue FCM task | order_id=%s order_code=%s driver_id=%s "
                "(keyin log: celery worker terminalida send_push_notification_async)",
                order.id,
                order.order_code,
                driver.id,
            )
            async_result = send_push_notification_async.delay(
                user_id=driver.id,
                title="New ride request",
                body=f"New ride request available nearby. Order: {order.order_code}",
                data={
                    "order_id": order.id,
                    "order_code": order.order_code,
                    "type": "ride_request"
                }
            )
            logger.info(
                "[PUSH DEBUG] Celery task queued OK | task_id=%s (worker ishlamasa push kelmaydi)",
                getattr(async_result, "id", None),
            )
        except ImportError:
            logger.warning(
                "[PUSH DEBUG] Celery import yo‘q — sync send_push_to_user | driver_id=%s order_id=%s",
                driver.id,
                order.id,
            )
            from apps.notification.services import send_push_to_user
            try:
                ok, err = send_push_to_user(
                    user=driver,
                    title="New ride request",
                    body=f"New ride request available nearby. Order: {order.order_code}",
                    data={
                        "order_id": order.id,
                        "order_code": order.order_code,
                        "type": "ride_request"
                    }
                )
                logger.info(
                    "[PUSH DEBUG] sync send_push_to_user tugadi | driver_id=%s success=%s error=%s",
                    driver.id,
                    ok,
                    err,
                )
            except Exception as e:
                logger.error(
                    "[PUSH DEBUG] sync push xato | driver_id=%s order_id=%s: %s",
                    driver.id,
                    order.id,
                    e,
                    exc_info=True,
                )
        except Exception as e:
            logger.error(
                "[PUSH DEBUG] Celery .delay() xato (Redis/worker?) | driver_id=%s order_id=%s: %s",
                driver.id,
                order.id,
                e,
                exc_info=True,
            )

        try:
            from .driver_orders_websocket import send_new_order_to_driver
            send_new_order_to_driver(order, driver, order_driver.requested_at)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket new_order to driver {driver.id}: {e}")

        return order_driver
    
    @staticmethod
    def check_and_handle_timeout(order):
        current_request = OrderDriver.objects.filter(
            order=order,
            status=OrderDriver.DriverRequestStatus.REQUESTED
        ).first()
        
        if not current_request:
            return DriverAssignmentService.assign_to_next_driver(order)
        
        if current_request.requested_at:
            time_elapsed = timezone.now() - current_request.requested_at
            if time_elapsed.total_seconds() >= DriverAssignmentService.TIMEOUT_SECONDS:
                current_request.status = OrderDriver.DriverRequestStatus.TIMEOUT
                current_request.save()
                
                exclude_ids = list(
                    OrderDriver.objects.filter(order=order)
                    .exclude(status=OrderDriver.DriverRequestStatus.ACCEPTED)
                    .values_list('driver_id', flat=True)
                )
                
                next_order_driver = DriverAssignmentService.assign_to_next_driver(
                    order, use_radius_search=True
                )
                
                if next_order_driver:
                    return next_order_driver
                else:
                    return None
        
        return None
    
    @staticmethod
    def assign_to_next_driver(order, use_radius_search=True):
        exclude_ids = list(
            OrderDriver.objects.filter(order=order)
            .exclude(status=OrderDriver.DriverRequestStatus.ACCEPTED)
            .values_list('driver_id', flat=True)
        )
        
        if not use_radius_search:
            nearest_driver = DriverAssignmentService.find_nearest_available_driver(
                order, exclude_driver_ids=exclude_ids
            )
            if nearest_driver:
                return DriverAssignmentService.assign_order_to_driver(order, nearest_driver)
            return None
        
        first_radius_km = DriverAssignmentService.SEARCH_RADIUSES[0]
        nearest_driver = DriverAssignmentService.find_nearest_available_driver(
            order, exclude_driver_ids=exclude_ids, max_radius_km=first_radius_km
        )
        
        if nearest_driver:
            return DriverAssignmentService.assign_order_to_driver(order, nearest_driver)
        
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
            return None
        
        return None
