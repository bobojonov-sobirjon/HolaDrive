"""
Driver location tracking WebSocket helpers.
"""
import logging
import math
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from ..models import Order, OrderDriver
from .surge_pricing_service import calculate_distance

logger = logging.getLogger(__name__)


ACTIVE_TRACKING_STATUSES = (
    Order.OrderStatus.ACCEPTED,
    Order.OrderStatus.ON_THE_WAY,
    Order.OrderStatus.ARRIVED,
    Order.OrderStatus.IN_PROGRESS,
)
AVERAGE_SPEED_KMH = 45.0


def _driver_active_order_ids(driver_id: int):
    return list(
        OrderDriver.objects.filter(
            driver_id=driver_id,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
            order__status__in=ACTIVE_TRACKING_STATUSES,
        )
        .values_list("order_id", flat=True)
        .distinct()
    )


def _order_tracking_meta(order_ids):
    rows = (
        Order.objects.filter(id__in=order_ids)
        .prefetch_related("order_items")
        .values("id", "status")
    )
    status_map = {row["id"]: row["status"] for row in rows}

    meta = {}
    for order in Order.objects.filter(id__in=order_ids).prefetch_related("order_items"):
        first_item = order.order_items.first()
        meta[order.id] = {
            "status": status_map.get(order.id, order.status),
            "pickup_lat": float(first_item.latitude_from) if first_item and first_item.latitude_from is not None else None,
            "pickup_lon": float(first_item.longitude_from) if first_item and first_item.longitude_from is not None else None,
            "dest_lat": float(first_item.latitude_to) if first_item and first_item.latitude_to is not None else None,
            "dest_lon": float(first_item.longitude_to) if first_item and first_item.longitude_to is not None else None,
        }
    return meta


def _eta_minutes(distance_km: float | None):
    if distance_km is None:
        return None
    if distance_km <= 0:
        return 0
    return int(math.ceil((distance_km / AVERAGE_SPEED_KMH) * 60))


def _build_eta_payload(order_status: str, driver_lat: float | None, driver_lon: float | None, meta: dict):
    if driver_lat is None or driver_lon is None:
        return {
            "eta_minutes": None,
            "eta_to_pickup_minutes": None,
            "eta_to_destination_minutes": None,
            "tracking_phase": "unknown",
        }

    pickup_distance = None
    if meta.get("pickup_lat") is not None and meta.get("pickup_lon") is not None:
        pickup_distance = float(
            calculate_distance(driver_lat, driver_lon, meta["pickup_lat"], meta["pickup_lon"])
        )

    destination_distance = None
    if meta.get("dest_lat") is not None and meta.get("dest_lon") is not None:
        destination_distance = float(
            calculate_distance(driver_lat, driver_lon, meta["dest_lat"], meta["dest_lon"])
        )

    eta_to_pickup = _eta_minutes(pickup_distance)
    eta_to_destination = _eta_minutes(destination_distance)

    if order_status == Order.OrderStatus.IN_PROGRESS:
        tracking_phase = "to_destination"
        eta_minutes = eta_to_destination
    elif order_status == Order.OrderStatus.ARRIVED:
        tracking_phase = "arrived"
        eta_minutes = 0
    else:
        tracking_phase = "to_pickup"
        eta_minutes = eta_to_pickup

    return {
        "eta_minutes": eta_minutes,
        "eta_to_pickup_minutes": eta_to_pickup,
        "eta_to_destination_minutes": eta_to_destination,
        "tracking_phase": tracking_phase,
    }


def notify_driver_location_updated(driver_id: int, latitude, longitude, updated_at=None):
    """
    Push latest location to every active tracking room for driver's accepted orders.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    order_ids = _driver_active_order_ids(driver_id)
    if not order_ids:
        return

    try:
        driver_lat = float(latitude) if latitude is not None else None
        driver_lon = float(longitude) if longitude is not None else None
    except (TypeError, ValueError):
        driver_lat = None
        driver_lon = None

    order_meta = _order_tracking_meta(order_ids)

    payload = {
        "type": "driver_location_update",
        "driver_id": driver_id,
        "latitude": str(latitude) if latitude is not None else None,
        "longitude": str(longitude) if longitude is not None else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }

    for order_id in order_ids:
        try:
            meta = order_meta.get(order_id, {})
            eta_payload = _build_eta_payload(
                meta.get("status"),
                driver_lat,
                driver_lon,
                meta,
            )
            async_to_sync(channel_layer.group_send)(
                f"order_tracking_{order_id}",
                {
                    **payload,
                    "order_id": order_id,
                    **eta_payload,
                },
            )
        except Exception as e:
            logger.warning(
                "Failed sending driver tracking update (driver=%s, order=%s): %s",
                driver_id,
                order_id,
                e,
            )


def get_initial_tracking_payload(order_id: int):
    """
    Snapshot payload for tracking socket immediately after connect.
    """
    od = (
        OrderDriver.objects.filter(
            order_id=order_id,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        )
        .select_related("driver", "order")
        .prefetch_related("order__order_items")
        .first()
    )
    if not od or not od.driver or not od.order:
        return None

    driver = od.driver
    order = od.order
    first_item = order.order_items.first()
    meta = {
        "pickup_lat": float(first_item.latitude_from) if first_item and first_item.latitude_from is not None else None,
        "pickup_lon": float(first_item.longitude_from) if first_item and first_item.longitude_from is not None else None,
        "dest_lat": float(first_item.latitude_to) if first_item and first_item.latitude_to is not None else None,
        "dest_lon": float(first_item.longitude_to) if first_item and first_item.longitude_to is not None else None,
    }

    driver_lat = float(driver.latitude) if driver.latitude is not None else None
    driver_lon = float(driver.longitude) if driver.longitude is not None else None
    eta_payload = _build_eta_payload(order.status, driver_lat, driver_lon, meta)

    return {
        "order_id": order_id,
        "driver_id": driver.id,
        "latitude": str(driver.latitude) if driver.latitude is not None else None,
        "longitude": str(driver.longitude) if driver.longitude is not None else None,
        "updated_at": driver.updated_at.isoformat() if driver.updated_at else None,
        **eta_payload,
    }
