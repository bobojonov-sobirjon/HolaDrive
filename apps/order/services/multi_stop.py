"""Multi-stop rides: waypoints → OrderItem chain, reprice, limits."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from apps.order.models import Order, OrderItem, RideType
from apps.order.services.surge_pricing_service import SurgePricingService, calculate_distance

MAX_INTERMEDIATE_STOPS = 3
ALLOWED_MID_RIDE_STATUSES = (
    Order.OrderStatus.ACCEPTED,
    Order.OrderStatus.ON_THE_WAY,
    Order.OrderStatus.ARRIVED,
    Order.OrderStatus.IN_PROGRESS,
)


class MultiStopError(ValueError):
    pass


@dataclass
class Waypoint:
    address: str
    lat: float
    lng: float
    kind: str  # pickup | stop | dropoff


def _coord(value) -> float:
    return float(value)


def _eta_label(distance_km: float) -> str:
    minutes = int((distance_km / 45.0) * 60)
    if minutes < 60:
        return f'{max(minutes, 1)} min'
    hours = minutes // 60
    rest = minutes % 60
    if rest:
        return f'{hours}h {rest}m'
    return f'{hours}h'


def parse_stops_payload(raw_stops, *, pickup, dropoff) -> list[Waypoint] | None:
    """
    Returns None when FE omitted stops (single-leg).
    Raises MultiStopError when stops is present but invalid.
    pickup/dropoff: dicts with address, lat, lng from create body.
    """
    if raw_stops is None:
        return None
    if not isinstance(raw_stops, (list, tuple)):
        raise MultiStopError('stops must be a list.')
    if not raw_stops:
        return None

    points: list[Waypoint] = []
    for i, row in enumerate(raw_stops):
        if not isinstance(row, dict):
            raise MultiStopError(f'stops[{i}] must be an object.')
        kind = str(row.get('type') or '').strip().lower()
        if kind not in ('pickup', 'stop', 'dropoff'):
            raise MultiStopError(f'stops[{i}].type must be pickup, stop, or dropoff.')
        address = str(row.get('address') or '').strip()
        if not address:
            raise MultiStopError(f'stops[{i}].address is required.')
        lat = row.get('lat', row.get('latitude'))
        lng = row.get('lng', row.get('longitude'))
        if lat is None or lng is None:
            raise MultiStopError(f'stops[{i}] requires lat and lng.')
        try:
            lat_f = _coord(lat)
            lng_f = _coord(lng)
        except (TypeError, ValueError) as exc:
            raise MultiStopError(f'stops[{i}] has invalid coordinates.') from exc
        if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lng_f <= 180.0):
            raise MultiStopError(f'stops[{i}] coordinates out of range.')
        points.append(Waypoint(address=address, lat=lat_f, lng=lng_f, kind=kind))

    intermediate = [p for p in points if p.kind == 'stop']
    if not intermediate:
        raise MultiStopError('stops must include at least one type "stop".')
    if len(intermediate) > MAX_INTERMEDIATE_STOPS:
        raise MultiStopError(f'Maximum {MAX_INTERMEDIATE_STOPS} intermediate stops allowed.')

    if points[0].kind != 'pickup':
        points.insert(
            0,
            Waypoint(
                address=pickup['address'],
                lat=pickup['lat'],
                lng=pickup['lng'],
                kind='pickup',
            ),
        )
    if points[-1].kind != 'dropoff':
        points.append(
            Waypoint(
                address=dropoff['address'],
                lat=dropoff['lat'],
                lng=dropoff['lng'],
                kind='dropoff',
            ),
        )

    if points[0].kind != 'pickup' or points[-1].kind != 'dropoff':
        raise MultiStopError('stops must start with pickup and end with dropoff.')
    mid = points[1:-1]
    if any(p.kind != 'stop' for p in mid):
        raise MultiStopError('Only type "stop" is allowed between pickup and dropoff.')
    if not mid:
        raise MultiStopError('stops must include at least one type "stop".')
    if len(mid) > MAX_INTERMEDIATE_STOPS:
        raise MultiStopError(f'Maximum {MAX_INTERMEDIATE_STOPS} intermediate stops allowed.')
    return points


def route_distance_km(waypoints: list[Waypoint]) -> float:
    total = 0.0
    for a, b in zip(waypoints, waypoints[1:]):
        total += float(calculate_distance(a.lat, a.lng, b.lat, b.lng))
    return round(total, 2)


def distance_km_from_validated(data: dict) -> float:
    points = data.get('_waypoints')
    if points:
        return route_distance_km(points)
    return round(
        float(
            calculate_distance(
                float(data['latitude_from']),
                float(data['longitude_from']),
                float(data['latitude_to']),
                float(data['longitude_to']),
            )
        ),
        2,
    )


def intermediate_stop_count(order: Order) -> int:
    n = order.order_items.count()
    return max(0, n - 1)


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def apply_total_fare(
    items: list[OrderItem],
    *,
    ride_type: RideType | None,
    pickup_lat: float,
    pickup_lng: float,
    adjusted_price=None,
) -> Decimal:
    """One base fare for the whole route; extra legs keep distance/ETA only."""
    total_km = sum(float(it.distance_km or 0) for it in items)
    total_km = round(total_km, 2)
    surge = Decimal('1.00')
    if ride_type:
        surge = Decimal(
            str(SurgePricingService.get_multiplier(pickup_lat, pickup_lng) or 1.0)
        )
        fare = _money(ride_type.calculate_price(total_km, float(surge)))
    else:
        fare = _money(0)

    if not items:
        return fare

    first, *rest = items
    first.distance_km = _money(total_km)
    first.estimated_time = _eta_label(total_km)
    first.original_price = fare
    first.calculated_price = fare
    first.min_price, first.max_price = first.calculate_price_range()
    if adjusted_price is not None:
        first.adjust_price(float(adjusted_price))
    else:
        first.adjusted_price = None
        first.is_price_adjusted = False
        first.price_adjustment_percentage = None
        first.save(
            update_fields=[
                'distance_km',
                'estimated_time',
                'original_price',
                'calculated_price',
                'min_price',
                'max_price',
                'adjusted_price',
                'is_price_adjusted',
                'price_adjustment_percentage',
                'updated_at',
            ]
        )

    for it in rest:
        OrderItem.objects.filter(pk=it.pk).update(
            original_price=_money(0),
            calculated_price=_money(0),
            adjusted_price=None,
            min_price=_money(0),
            max_price=_money(0),
            is_price_adjusted=False,
            price_adjustment_percentage=None,
        )
    return first.get_final_price() or fare


def create_items_from_waypoints(
    order: Order,
    waypoints: list[Waypoint],
    *,
    ride_type: RideType | None,
    adjusted_price=None,
) -> list[OrderItem]:
    items: list[OrderItem] = []
    last_index = len(waypoints) - 2
    for seq, (a, b) in enumerate(zip(waypoints, waypoints[1:]), start=1):
        item = OrderItem(
            order=order,
            address_from=a.address,
            address_to=b.address,
            latitude_from=a.lat,
            longitude_from=a.lng,
            latitude_to=b.lat,
            longitude_to=b.lng,
            stop_sequence=seq,
            is_final_stop=(seq - 1 == last_index),
            ride_type=ride_type,
        )
        dist = calculate_distance(a.lat, a.lng, b.lat, b.lng)
        item.distance_km = round(float(dist), 2)
        item.estimated_time = _eta_label(float(item.distance_km))
        item.save()
        items.append(item)

    apply_total_fare(
        items,
        ride_type=ride_type,
        pickup_lat=waypoints[0].lat,
        pickup_lng=waypoints[0].lng,
        adjusted_price=adjusted_price,
    )
    return items


def _ordered_items(order: Order) -> list[OrderItem]:
    return list(order.order_items.order_by('stop_sequence', 'id'))


def _waypoints_from_items(items: list[OrderItem]) -> list[Waypoint]:
    if not items:
        return []
    points = [
        Waypoint(
            address=items[0].address_from or '',
            lat=float(items[0].latitude_from),
            lng=float(items[0].longitude_from),
            kind='pickup',
        )
    ]
    for it in items:
        kind = 'dropoff' if it.is_final_stop else 'stop'
        points.append(
            Waypoint(
                address=it.address_to or '',
                lat=float(it.latitude_to),
                lng=float(it.longitude_to),
                kind=kind,
            )
        )
    return points


def _rebuild_items(
    order: Order,
    waypoints: list[Waypoint],
    *,
    ride_type: RideType | None,
) -> Decimal:
    order.order_items.all().delete()
    items = create_items_from_waypoints(order, waypoints, ride_type=ride_type)
    first = items[0] if items else None
    return first.get_final_price() if first else Decimal('0')


@transaction.atomic
def add_intermediate_stop(
    order: Order,
    *,
    address: str,
    latitude,
    longitude,
) -> Decimal:
    if order.status not in ALLOWED_MID_RIDE_STATUSES:
        raise MultiStopError('Stops can only be changed while the ride is accepted or in progress.')
    if intermediate_stop_count(order) >= MAX_INTERMEDIATE_STOPS:
        raise MultiStopError(f'Maximum {MAX_INTERMEDIATE_STOPS} intermediate stops allowed.')

    items = _ordered_items(order)
    if not items:
        raise MultiStopError('Order has no route items.')

    lat_f = _coord(latitude)
    lng_f = _coord(longitude)
    points = _waypoints_from_items(items)
    new_stop = Waypoint(address=address.strip(), lat=lat_f, lng=lng_f, kind='stop')
    points.insert(-1, new_stop)

    ride_type = items[0].ride_type
    return _rebuild_items(order, points, ride_type=ride_type)


@transaction.atomic
def replace_final_destination(
    order: Order,
    *,
    address: str,
    latitude,
    longitude,
) -> Decimal:
    if order.status not in ALLOWED_MID_RIDE_STATUSES:
        raise MultiStopError('Destination can only be changed while the ride is accepted or in progress.')

    items = _ordered_items(order)
    if not items:
        raise MultiStopError('Order has no route items.')

    lat_f = _coord(latitude)
    lng_f = _coord(longitude)
    points = _waypoints_from_items(items)
    points[-1] = Waypoint(address=address.strip(), lat=lat_f, lng=lng_f, kind='dropoff')

    ride_type = items[0].ride_type
    return _rebuild_items(order, points, ride_type=ride_type)
