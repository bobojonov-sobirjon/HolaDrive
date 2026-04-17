"""
Real-time WebSocket payloads for riders (order lifecycle, assigned driver).
Called from sync code via channel_layer.group_send → RiderOrdersConsumer.
"""
import logging
from decimal import Decimal

from asgiref.sync import async_to_sync
from django.conf import settings
from django.db.models import Avg
from django.utils import timezone

from ..models import Order, OrderDriver, PromoCode, TripRating

logger = logging.getLogger(__name__)


def _http_base_from_websocket_settings() -> str:
    """
    If PUBLIC_BASE_URL is not set, derive HTTP origin from WebSocket settings.
    Rider WS payloads have no Django request; same host:port is usually used for HTTP + WS.
    """
    raw = (getattr(settings, 'WEBSOCKET_URL', '') or '').strip()
    if not raw or raw in ('None:None', 'None'):
        host = getattr(settings, 'WEBSOCKET_HOST', None)
        port = getattr(settings, 'WEBSOCKET_PORT', None)
        if host and str(host).strip() not in ('', 'None'):
            ps = str(port).strip() if port is not None else ''
            if ps and ps not in ('None',):
                raw = f'{host}:{ps}'
            else:
                raw = str(host)
        else:
            return ''

    raw = raw.strip()
    if raw.startswith('ws://'):
        hostpart = raw[5:].split('/')[0].rstrip('/')
        return f'http://{hostpart}' if hostpart else ''
    if raw.startswith('wss://'):
        hostpart = raw[6:].split('/')[0].rstrip('/')
        return f'https://{hostpart}' if hostpart else ''
    if raw.startswith('http://') or raw.startswith('https://'):
        try:
            from urllib.parse import urlparse

            u = urlparse(raw)
            if u.scheme and u.netloc:
                return f'{u.scheme}://{u.netloc}'.rstrip('/')
        except Exception:
            pass
    hostpart = raw.split('/')[0].rstrip('/')
    if not hostpart:
        return ''
    return f'http://{hostpart}'.rstrip('/')


def _media_absolute_url(url_path: str | None, request=None):
    """
    Turn FileField.url (/media/...) into an absolute URL.
    Order: PUBLIC_BASE_URL → WEBSOCKET_URL/WEBSOCKET_HOST (HTTP origin) → request.build_absolute_uri.
    """
    if not url_path:
        return None
    s = str(url_path).strip()
    if not s:
        return None
    if s.startswith('http://') or s.startswith('https://'):
        return s
    base = (getattr(settings, 'PUBLIC_BASE_URL', '') or '').strip().rstrip('/')
    if not base:
        base = _http_base_from_websocket_settings().rstrip('/')
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


def _order_discount_payload(order):
    """
    Fare breakdown for rider apps (promo + optional line-level delta).
    Matches UI: trip_fare, discount % label, discount_amount, total_paid.
    """
    promo_rows = list(
        order.applied_promo_codes.select_related('promo_code').order_by('created_at', 'id')
    )
    applications = []
    for r in promo_rows:
        pc = r.promo_code
        applications.append(
            {
                'promo_code': pc.code if pc else None,
                'discount_type': pc.discount_type if pc else None,
                'discount_value': _decimal(pc.discount_value) if pc else None,
                'discount_amount': _decimal(r.discount_amount),
                'order_amount_before_discount': _decimal(r.order_amount_before_discount),
                'order_amount_after_discount': _decimal(r.order_amount_after_discount),
            }
        )

    if promo_rows:
        total_discount = sum(Decimal(str(r.discount_amount)) for r in promo_rows)
        trip_fare = Decimal(str(promo_rows[0].order_amount_before_discount))
        total_paid = Decimal(str(promo_rows[-1].order_amount_after_discount))
        primary = promo_rows[-1].promo_code
        label = None
        if primary and primary.discount_type == PromoCode.DiscountType.PERCENTAGE:
            dv = float(primary.discount_value)
            label = f'{int(dv)}%' if dv == int(dv) else f'{dv}%'
        return {
            'has_discount': True,
            'has_promo_discount': True,
            'promo_code': primary.code if primary else None,
            'discount_type': primary.discount_type if primary else None,
            'discount_value': _decimal(primary.discount_value) if primary else None,
            'discount_percentage_label': label,
            'discount_amount': _decimal(total_discount),
            'trip_fare': _decimal(trip_fare),
            'total_paid': _decimal(total_paid),
            'applications': applications,
        }

    trip_fare = Decimal('0')
    total_paid = Decimal('0')
    for it in order.order_items.all().order_by('stop_sequence', 'id'):
        orig = it.original_price
        calc = it.calculated_price
        adj = it.adjusted_price
        if orig is not None:
            base = Decimal(str(orig))
        elif calc is not None:
            base = Decimal(str(calc))
        else:
            base = Decimal('0')
        trip_fare += base
        if adj is not None:
            total_paid += Decimal(str(adj))
        elif calc is not None:
            total_paid += Decimal(str(calc))
        else:
            total_paid += base
    raw_delta = trip_fare - total_paid
    line_discount = raw_delta if raw_delta > 0 else Decimal('0')
    return {
        'has_discount': line_discount > 0,
        'has_promo_discount': False,
        'promo_code': None,
        'discount_type': None,
        'discount_value': None,
        'discount_percentage_label': None,
        'discount_amount': _decimal(line_discount),
        'trip_fare': _decimal(trip_fare),
        'total_paid': _decimal(total_paid),
        'applications': applications,
    }


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


def _driver_rider_profile_stats(driver_user):
    """
    Rating (approved TripRating avg), completed trips count, full calendar years since signup (staj).
    """
    agg = TripRating.objects.filter(driver_id=driver_user.id, status='approved').aggregate(
        avg=Avg('rating')
    )
    avg_rating = agg['avg']

    trips_count = (
        Order.objects.filter(
            order_drivers__driver_id=driver_user.id,
            order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
            status=Order.OrderStatus.COMPLETED,
        )
        .distinct()
        .count()
    )

    experience_years = 0
    member_since = None
    if driver_user.created_at:
        member_since = driver_user.created_at.date().isoformat()
        today = timezone.now().date()
        joined = driver_user.created_at.date()
        y = today.year - joined.year
        if (today.month, today.day) < (joined.month, joined.day):
            y -= 1
        experience_years = max(0, y)

    return {
        'rating': round(float(avg_rating), 2) if avg_rating is not None else 0.0,
        'trips_count': trips_count,
        'experience_years': experience_years,
        'member_since': member_since,
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
    stats = _driver_rider_profile_stats(driver_user)
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
        'rating': stats['rating'],
        'trips_count': stats['trips_count'],
        'experience_years': stats['experience_years'],
        'member_since': stats['member_since'],
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


def _saved_card_ws_payload(order: Order):
    if not getattr(order, 'saved_card_id', None):
        return None
    sc = getattr(order, 'saved_card', None)
    if sc is None:
        return {'id': order.saved_card_id}
    return {
        'id': sc.id,
        'brand': sc.brand or '',
        'last4': sc.last4 or '',
        'holder_role': sc.holder_role,
        'is_default': sc.is_default,
    }


def build_rider_order_payload(order: Order, accepted_assignment: OrderDriver | None = None):
    """
    Full order JSON for rider WebSocket (no nested rider user — client already is the rider).
    """
    driver_assignment = accepted_assignment
    # Include assigned driver on terminal statuses too (completed / cancelled) for rider UI.
    if driver_assignment is None and order.status in (
        Order.OrderStatus.ACCEPTED,
        Order.OrderStatus.ON_THE_WAY,
        Order.OrderStatus.ARRIVED,
        Order.OrderStatus.IN_PROGRESS,
        Order.OrderStatus.COMPLETED,
        Order.OrderStatus.CANCELLED,
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
        'saved_card': _saved_card_ws_payload(order),
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        'order_items': _order_items_payload(order),
        'order_preferences': _order_preferences_payload(order),
        'discount': _order_discount_payload(order),
        'driver': driver_payload,
        'order_driver': _order_driver_row(driver_assignment),
    }


def _fetch_order_for_rider_ws(order_id: int) -> Order | None:
    try:
        return (
            Order.objects.filter(id=order_id)
            .select_related('saved_card')
            .prefetch_related(
                'order_items__ride_type',
                'order_preferences',
                'applied_promo_codes__promo_code',
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
        Order.OrderStatus.REJECTED,
    ]
    qs = (
        Order.objects.filter(user=rider_user)
        .exclude(status__in=terminal)
        .select_related('saved_card')
        .prefetch_related(
            'order_items__ride_type',
            'order_preferences',
            'applied_promo_codes__promo_code',
            'order_drivers__driver',
            'order_drivers__driver__vehicle_details__images',
        )
        .order_by('-updated_at')
    )
    out = []
    for o in qs:
        assignment = None
        if o.status in (
            Order.OrderStatus.ACCEPTED,
            Order.OrderStatus.ON_THE_WAY,
            Order.OrderStatus.ARRIVED,
            Order.OrderStatus.IN_PROGRESS,
        ):
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


def notify_rider_order_updated(
    order_id: int,
    change: str,
    message: str,
    *,
    rejected_driver_id: int | None = None,
    reassigned: bool | None = None,
):
    """
    Universal rider WS snapshot on lifecycle changes.

    ``change`` (for clients): accepted | driver_rejected | in_progress | completed
    | cancelled_driver | cancelled_rider
    """
    order_full = _fetch_order_for_rider_ws(order_id)
    if not order_full:
        return
    payload = build_rider_order_payload(order_full)
    event = {
        'type': 'rider_order_updated',
        'change': change,
        'order': payload,
        'message': message,
    }
    if rejected_driver_id is not None:
        event['rejected_driver_id'] = rejected_driver_id
    if reassigned is not None:
        event['reassigned'] = reassigned
    _send_to_rider_group(order_full.user_id, event)
    logger.info(
        'rider ws: rider_order_updated order=%s rider=%s change=%s',
        order_id,
        order_full.user_id,
        change,
    )


def send_rider_order_driver_accepted(order_id: int):
    """After driver accepts — universal update + legacy rider_order_accepted."""
    order_full = _fetch_order_for_rider_ws(order_id)
    if not order_full:
        return
    assignment = (
        order_full.order_drivers.filter(status=OrderDriver.DriverRequestStatus.ACCEPTED)
        .select_related('driver')
        .first()
    )
    payload = build_rider_order_payload(order_full, accepted_assignment=assignment)
    rider_id = order_full.user_id
    msg = 'A driver accepted your ride'
    _send_to_rider_group(
        rider_id,
        {
            'type': 'rider_order_updated',
            'change': 'accepted',
            'order': payload,
            'message': msg,
        },
    )
    _send_to_rider_group(
        rider_id,
        {
            'type': 'rider_order_accepted',
            'order': payload,
            'message': msg,
        },
    )
    logger.info('rider ws: rider_order_accepted order=%s rider=%s', order_id, rider_id)


def send_rider_order_driver_rejected(
    order_id: int,
    *,
    rejected_driver_id: int,
    rider_message: str,
    reassigned: bool,
):
    """After driver rejects — universal update + legacy rider_driver_rejected."""
    order_full = _fetch_order_for_rider_ws(order_id)
    if not order_full:
        return
    payload = build_rider_order_payload(order_full, accepted_assignment=None)
    rider_id = order_full.user_id
    _send_to_rider_group(
        rider_id,
        {
            'type': 'rider_order_updated',
            'change': 'driver_rejected',
            'order': payload,
            'rejected_driver_id': rejected_driver_id,
            'reassigned': reassigned,
            'message': rider_message,
        },
    )
    _send_to_rider_group(
        rider_id,
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
        rider_id,
        rejected_driver_id,
    )
