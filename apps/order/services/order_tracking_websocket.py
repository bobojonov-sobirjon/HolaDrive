"""
Order live tracking WebSocket helpers (driver + rider locations).
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


def _rider_active_order_ids(rider_id: int):
    return list(
        Order.objects.filter(
            user_id=rider_id,
            status__in=ACTIVE_TRACKING_STATUSES,
        ).values_list("id", flat=True)
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


def notify_rider_location_updated(rider_id: int, latitude, longitude, updated_at=None, order_id: int | None = None):
    """
    Push rider live location to order tracking room(s) so the assigned driver can see the passenger.
    If order_id is set, only that order is notified (must belong to rider and be active).
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    if order_id is not None:
        order = (
            Order.objects.filter(
                id=order_id,
                user_id=rider_id,
                status__in=ACTIVE_TRACKING_STATUSES,
            )
            .only("id")
            .first()
        )
        order_ids = [order.id] if order else []
    else:
        order_ids = _rider_active_order_ids(rider_id)

    if not order_ids:
        return

    payload = {
        "type": "rider_location_update",
        "rider_id": rider_id,
        "latitude": str(latitude) if latitude is not None else None,
        "longitude": str(longitude) if longitude is not None else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }

    for oid in order_ids:
        try:
            async_to_sync(channel_layer.group_send)(
                f"order_tracking_{oid}",
                {
                    **payload,
                    "order_id": oid,
                },
            )
        except Exception as e:
            logger.warning(
                "Failed sending rider tracking update (rider=%s, order=%s): %s",
                rider_id,
                oid,
                e,
            )


def get_initial_tracking_payload(order_id: int):
    """
    Snapshot payload for tracking socket immediately after connect (driver location).
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


def get_initial_rider_location_payload(order_id: int):
    """Snapshot of passenger location for tracking socket (for driver map)."""
    order = (
        Order.objects.filter(id=order_id, status__in=ACTIVE_TRACKING_STATUSES)
        .select_related("user")
        .first()
    )
    if not order or not order.user:
        return None

    rider = order.user
    if rider.latitude is None or rider.longitude is None:
        return {
            "order_id": order_id,
            "rider_id": rider.id,
            "latitude": None,
            "longitude": None,
            "updated_at": rider.updated_at.isoformat() if rider.updated_at else None,
        }

    return {
        "order_id": order_id,
        "rider_id": rider.id,
        "latitude": str(rider.latitude),
        "longitude": str(rider.longitude),
        "updated_at": rider.updated_at.isoformat() if rider.updated_at else None,
    }


def notify_order_cancelled_on_tracking(
    order_id: int,
    *,
    change: str,
    message: str | None = None,
) -> None:
    """
    Broadcast cancel reason to ws/order/{order_id}/tracking/ so both parties
    still connected to the live map get the cancellation + reason.
    """
    from .cancel_ws import build_cancel_ws_payload
    from .rider_orders_websocket import build_rider_order_payload, _fetch_order_for_rider_ws

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    order = _fetch_order_for_rider_ws(order_id)
    if not order:
        return

    cancel = build_cancel_ws_payload(order)
    order_payload = build_rider_order_payload(order)
    event = {
        "type": "order_cancelled",
        "order_id": order_id,
        "change": change,
        "message": message or "This ride has been cancelled.",
        "cancel": cancel,
        "order": order_payload,
    }
    try:
        async_to_sync(channel_layer.group_send)(f"order_tracking_{order_id}", event)
        logger.info(
            "tracking ws: order_cancelled order=%s change=%s cancel=%s",
            order_id,
            change,
            cancel,
        )
    except Exception as e:
        logger.warning(
            "Failed tracking order_cancelled for order %s: %s", order_id, e
        )
