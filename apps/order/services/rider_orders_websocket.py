"""
Real-time WebSocket payloads for riders (order lifecycle, assigned driver).
Called from sync code via channel_layer.group_send → RiderOrdersConsumer.
"""
import logging
from decimal import Decimal

from asgiref.sync import async_to_sync
from django.conf import settings

from ..models import Order, OrderDriver

logger = logging.getLogger(__name__)


def _media_absolute_url(url_path: str | None, request=None):
    """
    Turn FileField.url (/media/...) into an absolute URL.
    Prefer PUBLIC_BASE_URL from settings; if unset and ``request`` is given, use request.build_absolute_uri.
    """
    if not url_path:
        return None
    s = str(url_path).strip()
    if not s:
        return None
    if s.startswith('http://') or s.startswith('https://'):
        return s
    base = getattr(settings, 'PUBLIC_BASE_URL', '') or ''
    base = base.rstrip('/')
    if base:
        if not s.startswith('/'):
            s = '/' + s
        return f'{base}{s}'
    if request is not None:
        try:
            return request.build_absolute_uri(s)
        except Exception:
            logger.debug('build_absolute_uri failed for %r', s, exc_info=True)
    return s


def _decimal(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def _ride_type_dict(rt):
    if not rt:
        return None
    return {
        'id': rt.id,
        'name': rt.name or '',
        'name_large': rt.name_large or '',
    }


def _order_items_payload(order):
    items = []
    for it in order.order_items.all().order_by('stop_sequence', 'id'):
        items.append({
            'id': it.id,
            'address_from': it.address_from,
            'address_to': it.address_to,
            'latitude_from': str(it.latitude_from) if it.latitude_from is not None else None,
            'longitude_from': str(it.longitude_from) if it.longitude_from is not None else None,
            'latitude_to': str(it.latitude_to) if it.latitude_to is not None else None,
            'longitude_to': str(it.longitude_to) if it.longitude_to is not None else None,
            'stop_sequence': it.stop_sequence,
            'is_final_stop': it.is_final_stop,
            'ride_type': _ride_type_dict(it.ride_type),
            'distance_km': _decimal(it.distance_km),
            'estimated_time': it.estimated_time,
            'calculated_price': _decimal(it.calculated_price),
            'original_price': _decimal(it.original_price),
            'adjusted_price': _decimal(it.adjusted_price),
            'min_price': _decimal(it.min_price),
            'max_price': _decimal(it.max_price),
            'is_price_adjusted': it.is_price_adjusted,
            'price_adjustment_percentage': _decimal(it.price_adjustment_percentage),
            'created_at': it.created_at.isoformat() if it.created_at else None,
            'updated_at': it.updated_at.isoformat() if it.updated_at else None,
        })
    return items


def _order_preferences_payload(order):
    from ..models import OrderPreferences

    try:
        p = order.order_preferences.first()
    except Exception:
        p = OrderPreferences.objects.filter(order_id=order.pk).first()
    if not p:
        return None
    return {
        'chatting_preference': p.chatting_preference,
        'temperature_preference': p.temperature_preference,
        'music_preference': p.music_preference,
        'volume_level': p.volume_level,
        'pet_preference': p.pet_preference,
        'kids_chair_preference': p.kids_chair_preference,
        'wheelchair_preference': p.wheelchair_preference,
        'gender_preference': p.gender_preference,
        'favorite_driver_preference': p.favorite_driver_preference,
    }


def _vehicle_payload(vehicle, request=None):
    """VehicleDetails instance + images (absolute URLs when base/request available)."""
    if not vehicle:
        return None
    images = []
    for img in vehicle.images.all():
        images.append({
            'id': img.id,
            'image': _media_absolute_url(img.image.url if img.image else None, request=request),
            'created_at': img.created_at.isoformat() if img.created_at else None,
        })
    return {
        'id': vehicle.id,
        'brand': vehicle.brand,
        'model': vehicle.model,
        'year_of_manufacture': vehicle.year_of_manufacture,
        'plate_number': vehicle.plate_number,
        'color': vehicle.color,
        'vehicle_condition': vehicle.vehicle_condition,
        'images': images,
    }


def build_driver_for_rider(driver_user, request=None):
    """Full driver profile for rider apps (absolute media URLs via PUBLIC_BASE_URL or request)."""
    from apps.accounts.models import VehicleDetails

    vehicle = (
        VehicleDetails.objects.filter(user=driver_user)
        .prefetch_related('images')
        .order_by('-created_at')
        .first()
    )
    return {
        'id': driver_user.id,
        'email': driver_user.email or '',
        'username': driver_user.username or '',
        'first_name': driver_user.first_name or '',
        'last_name': driver_user.last_name or '',
        'full_name': driver_user.get_full_name() or driver_user.email or '',
        'phone_number': driver_user.phone_number or '',
        'avatar': _media_absolute_url(
            driver_user.avatar.url if driver_user.avatar else None,
            request=request,
        ),
        'latitude': str(driver_user.latitude) if driver_user.latitude is not None else None,
        'longitude': str(driver_user.longitude) if driver_user.longitude is not None else None,
        'is_online': driver_user.is_online,
        'vehicle': _vehicle_payload(vehicle, request=request),
    }


def _order_driver_row(order_driver: OrderDriver | None):
    if not order_driver:
        return None
    return {
        'id': order_driver.id,
        'status': order_driver.status,
        'pin_code': order_driver.pin_code,
        'requested_at': order_driver.requested_at.isoformat() if order_driver.requested_at else None,
        'responded_at': order_driver.responded_at.isoformat() if order_driver.responded_at else None,
        'pickup_confirmed_at': order_driver.pickup_confirmed_at.isoformat() if order_driver.pickup_confirmed_at else None,
    }


def build_rider_order_payload(order: Order, accepted_assignment: OrderDriver | None = None):
    """
    Full order JSON for rider WebSocket (no nested rider user — client already is the rider).
    """
    driver_assignment = accepted_assignment
    if driver_assignment is None and order.status in (
        Order.OrderStatus.CONFIRMED,
        Order.OrderStatus.IN_PROGRESS,
    ):
        driver_assignment = (
            order.order_drivers.filter(status=OrderDriver.DriverRequestStatus.ACCEPTED)
            .select_related('driver')
            .first()
        )

    driver_payload = None
    if driver_assignment and driver_assignment.driver_id:
        driver_payload = build_driver_for_rider(driver_assignment.driver)

    return {
        'id': order.id,
        'order_code': order.order_code,
        'status': order.status,
        'order_type': order.order_type,
        'payment_type': order.payment_type,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        'order_items': _order_items_payload(order),
        'order_preferences': _order_preferences_payload(order),
        'driver': driver_payload,
        'order_driver': _order_driver_row(driver_assignment),
    }


def _fetch_order_for_rider_ws(order_id: int) -> Order | None:
    try:
        return (
            Order.objects.filter(id=order_id)
            .prefetch_related(
                'order_items__ride_type',
                'order_preferences',
                'order_drivers__driver',
                'order_drivers__driver__vehicle_details__images',
            )
            .first()
        )
    except Exception as e:
        logger.warning('rider ws: failed to load order %s: %s', order_id, e)
        return None


def get_rider_active_orders(rider_user):
    """Orders the rider still cares about (not terminal)."""
    terminal = [
        Order.OrderStatus.COMPLETED,
        Order.OrderStatus.CANCELLED,
        Order.OrderStatus.REFUNDED,
        Order.OrderStatus.FAILED,
    ]
    qs = (
        Order.objects.filter(user=rider_user)
        .exclude(status__in=terminal)
        .prefetch_related(
            'order_items__ride_type',
            'order_preferences',
            'order_drivers__driver',
            'order_drivers__driver__vehicle_details__images',
        )
        .order_by('-updated_at')
    )
    out = []
    for o in qs:
        assignment = None
        if o.status in (Order.OrderStatus.CONFIRMED, Order.OrderStatus.IN_PROGRESS):
            assignment = (
                o.order_drivers.filter(status=OrderDriver.DriverRequestStatus.ACCEPTED)
                .select_related('driver')
                .first()
            )
        out.append(build_rider_order_payload(o, accepted_assignment=assignment))
    return out


def _send_to_rider_group(rider_user_id: int, message: dict):
    try:
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        group = f'rider_orders_{rider_user_id}'
        async_to_sync(channel_layer.group_send)(group, message)
    except Exception as e:
        logger.warning('rider ws group_send failed: %s', e)


def send_rider_order_driver_accepted(order_id: int):
    """After driver accepts — notify rider with full order + driver (fresh from DB)."""
    order_full = _fetch_order_for_rider_ws(order_id)
    if not order_full:
        return
    assignment = (
        order_full.order_drivers.filter(status=OrderDriver.DriverRequestStatus.ACCEPTED)
        .select_related('driver')
        .first()
    )
    payload = build_rider_order_payload(order_full, accepted_assignment=assignment)
    _send_to_rider_group(
        order_full.user_id,
        {
            'type': 'rider_order_accepted',
            'order': payload,
            'message': 'A driver accepted your ride',
        },
    )
    logger.info('rider ws: rider_order_accepted order=%s rider=%s', order_id, order_full.user_id)


def send_rider_order_driver_rejected(
    order_id: int,
    *,
    rejected_driver_id: int,
    rider_message: str,
    reassigned: bool,
):
    """After driver rejects — rider still waiting for another driver."""
    order_full = _fetch_order_for_rider_ws(order_id)
    if not order_full:
        return
    payload = build_rider_order_payload(order_full, accepted_assignment=None)
    _send_to_rider_group(
        order_full.user_id,
        {
            'type': 'rider_driver_rejected',
            'order': payload,
            'rejected_driver_id': rejected_driver_id,
            'reassigned': reassigned,
            'message': rider_message,
        },
    )
    logger.info(
        'rider ws: rider_driver_rejected order=%s rider=%s driver=%s',
        order_id,
        order_full.user_id,
        rejected_driver_id,
    )
