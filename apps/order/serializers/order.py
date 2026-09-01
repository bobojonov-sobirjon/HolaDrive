from rest_framework import serializers
from django.db import transaction
from django.db.models import Avg, Count
from ..models import (
    Order,
    OrderItem,
    OrderDriver,
    OrderPreferences,
    RideType,
    TripRating,
    UserOrderPreferences,
)
from apps.accounts.serializers.user import UserDetailSerializer
from apps.payment.serializers import SavedCardSerializer
from apps.order.services.multi_stop import MultiStopError, parse_stops_payload


class RideStopInputSerializer(serializers.Serializer):
    """One waypoint in create / estimate ``stops[]`` (pickup | stop | dropoff)."""

    address = serializers.CharField(max_length=255)
    lat = serializers.DecimalField(max_digits=24, decimal_places=18, coerce_to_string=False)
    lng = serializers.DecimalField(max_digits=24, decimal_places=18, coerce_to_string=False)
    type = serializers.ChoiceField(choices=['pickup', 'stop', 'dropoff'])

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = dict(data)
            if 'lat' not in data and data.get('latitude') is not None:
                data['lat'] = data['latitude']
            if 'lng' not in data and data.get('longitude') is not None:
                data['lng'] = data['longitude']
        return super().to_internal_value(data)


class OrderStopsUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['add', 'replace_destination'])
    address = serializers.CharField(max_length=255)
    latitude = serializers.DecimalField(max_digits=24, decimal_places=18, coerce_to_string=False)
    longitude = serializers.DecimalField(max_digits=24, decimal_places=18, coerce_to_string=False)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = dict(data)
            if 'latitude' not in data and data.get('lat') is not None:
                data['latitude'] = data['lat']
            if 'longitude' not in data and data.get('lng') is not None:
                data['longitude'] = data['lng']
        return super().to_internal_value(data)


class OrderCreateSerializer(serializers.Serializer):
    address_from = serializers.CharField(max_length=255, required=True)
    address_to = serializers.CharField(max_length=255, required=True)
    latitude_from = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    longitude_from = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    latitude_to = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    longitude_to = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    order_type = serializers.IntegerField(
        required=True,
        help_text="Order type: 1 = PICKUP (Pickup), 2 = FOR_ME (For Me)"
    )
    ride_type_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Ride type (tariff) ID. If omitted, first active RideType is used. Fills distance_km, estimated_time, calculated_price, etc."
    )
    payment_type = serializers.ChoiceField(
        choices=['card', 'cash', 'hola_wallet_cash'],
        default='card',
        required=False,
        help_text="Payment type: card, cash, hola_wallet_cash (Card, Cash, Hola Wallet Cash)"
    )
    adjusted_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text=(
            "Optional. After ride_type and prices are computed, same rules as manage-price "
            "(must be between min_price and max_price)."
        ),
    )
    stops = RideStopInputSerializer(
        many=True,
        required=False,
        help_text='Optional multi-stop waypoints: pickup, one or more stop, dropoff. Omit for a 1-leg trip.',
    )
    when = serializers.ChoiceField(
        choices=['now', 'later'],
        required=False,
        default='now',
        help_text='now = dispatch immediately; later = scheduled ride (no driver until pickup is near).',
    )
    schedule_type = serializers.ChoiceField(
        choices=['pickup_at', 'drop_off_by'],
        required=False,
        default='pickup_at',
    )
    scheduled_at = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='ISO 8601 with offset. Required when when=later.',
    )

    def validate_order_type(self, value):
        if value not in [1, 2]:
            raise serializers.ValidationError("order_type must be 1 (PICKUP) or 2 (FOR_ME)")
        return value

    def validate_ride_type_id(self, value):
        if value is None:
            return value
        if not RideType.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Ride type not found or inactive.")
        return value

    def validate(self, data):
        raw_stops = data.get('stops')
        if raw_stops:
            try:
                data['_waypoints'] = parse_stops_payload(
                    [dict(s) for s in raw_stops],
                    pickup={
                        'address': data['address_from'],
                        'lat': float(data['latitude_from']),
                        'lng': float(data['longitude_from']),
                    },
                    dropoff={
                        'address': data['address_to'],
                        'lat': float(data['latitude_to']),
                        'lng': float(data['longitude_to']),
                    },
                )
            except MultiStopError as e:
                raise serializers.ValidationError({'stops': str(e)})

        when = (data.get('when') or 'now').strip().lower()
        data['when'] = when
        if when == 'later':
            from apps.order.services.scheduled_ride import parse_scheduled_at

            try:
                data['_scheduled_at'] = parse_scheduled_at(data.get('scheduled_at'))
            except serializers.ValidationError as e:
                raise serializers.ValidationError({'scheduled_at': e.detail})
        return data

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user

        order_type_value = validated_data.pop('order_type')
        order_type = Order.OrderType.PICKUP if order_type_value == 1 else Order.OrderType.FOR_ME
        ride_type_id = validated_data.pop('ride_type_id', None)
        payment_type = validated_data.pop('payment_type', 'card')
        adjusted_price = validated_data.pop('adjusted_price', None)
        validated_data.pop('stops', None)
        waypoints = validated_data.pop('_waypoints', None)
        when = validated_data.pop('when', 'now')
        schedule_type = validated_data.pop('schedule_type', 'pickup_at') or 'pickup_at'
        validated_data.pop('scheduled_at', None)
        user_scheduled_at = validated_data.pop('_scheduled_at', None)
        is_later = when == 'later'

        order = Order.objects.create(
            user=user,
            order_type=order_type,
            payment_type=payment_type,
            status=Order.OrderStatus.SCHEDULED if is_later else Order.OrderStatus.PENDING,
        )

        template = UserOrderPreferences.objects.filter(user=user).first()
        if template:
            OrderPreferences.objects.create(
                order=order,
                chatting_preference=template.chatting_preference,
                temperature_preference=template.temperature_preference,
                music_preference=template.music_preference,
                volume_level=template.volume_level,
                pet_preference=template.pet_preference,
                kids_chair_preference=template.kids_chair_preference,
                wheelchair_preference=template.wheelchair_preference,
                gender_preference=template.gender_preference,
                favorite_driver_preference=template.favorite_driver_preference,
            )

        ride_type = None
        if ride_type_id:
            ride_type = RideType.objects.filter(id=ride_type_id, is_active=True).first()
        if not ride_type:
            ride_type = RideType.objects.filter(is_active=True).order_by('sort_order', 'id').first()

        if waypoints:
            from apps.order.services.multi_stop import create_items_from_waypoints

            try:
                create_items_from_waypoints(
                    order,
                    waypoints,
                    ride_type=ride_type,
                    adjusted_price=adjusted_price,
                )
            except ValueError as e:
                raise serializers.ValidationError({'adjusted_price': str(e)})
        else:
            order_item = OrderItem.objects.create(
                order=order,
                address_from=validated_data['address_from'],
                address_to=validated_data['address_to'],
                latitude_from=validated_data['latitude_from'],
                longitude_from=validated_data['longitude_from'],
                latitude_to=validated_data['latitude_to'],
                longitude_to=validated_data['longitude_to'],
                stop_sequence=1,
                is_final_stop=True
            )
            if ride_type:
                order_item.ride_type = ride_type
                order_item.save()
            if adjusted_price is not None:
                order_item.refresh_from_db()
                if not order_item.original_price:
                    raise serializers.ValidationError(
                        {'adjusted_price': 'Prices not computed; check ride_type and coordinates.'}
                    )
                if not order_item.min_price or not order_item.max_price:
                    min_p, max_p = order_item.calculate_price_range()
                    order_item.min_price = min_p
                    order_item.max_price = max_p
                    order_item.save(update_fields=['min_price', 'max_price'])
                try:
                    order_item.adjust_price(float(adjusted_price))
                except ValueError as e:
                    raise serializers.ValidationError({'adjusted_price': str(e)})
        try:
            from apps.chat.models import ChatRoom
            ChatRoom.objects.create(
                order=order,
                initiator=user,
                receiver=None,
                status=ChatRoom.RoomStatus.PENDING,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create ChatRoom for order {order.id}: {e}")

        if is_later:
            from apps.order.services.scheduled_ride import apply_schedule

            try:
                apply_schedule(
                    order,
                    schedule_type=schedule_type,
                    user_at=user_scheduled_at,
                )
            except serializers.ValidationError as e:
                raise serializers.ValidationError({'scheduled_at': e.detail})
            return order

        def _schedule_driver_assignment(oid):
            """Celery/sync assign — faqat DB commitdan keyin (boshqa process orderni ko‘radi)."""
            import logging
            from django.conf import settings

            logger = logging.getLogger(__name__)

            def _assign_sync():
                from apps.order.services.driver_assignment_service import DriverAssignmentService
                try:
                    o = Order.objects.get(pk=oid)
                    DriverAssignmentService.assign_to_next_driver(o)
                except Order.DoesNotExist:
                    logger.error("Order %s not found for sync driver assignment", oid)
                except Exception as e:
                    logger.error("Failed to assign driver to order %s: %s", oid, e)

            # Local/dev: Celery worker bo‘lmasa ham driverga darhol offer qilinsin
            if getattr(settings, 'DEBUG', False) or getattr(
                settings, 'CELERY_TASK_ALWAYS_EAGER', False
            ):
                _assign_sync()
                return

            try:
                from apps.order.tasks import assign_driver_to_order_async
                assign_driver_to_order_async.delay(oid)
            except ImportError:
                logger.warning("Celery task not available, using sync driver assignment")
                _assign_sync()
            except Exception as e:
                logger.error(
                    "Failed to schedule async driver assignment for order %s: %s — falling back to sync",
                    oid,
                    e,
                )
                _assign_sync()

        transaction.on_commit(lambda oid=order.id: _schedule_driver_assignment(oid))

        return order


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderItem model
    """
    ride_type_name = serializers.CharField(source='ride_type.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'address_from',
            'address_to',
            'latitude_from',
            'longitude_from',
            'latitude_to',
            'longitude_to',
            'stop_sequence',
            'is_final_stop',
            'ride_type',
            'ride_type_name',
            'distance_km',
            'estimated_time',
            'calculated_price',
            'original_price',
            'min_price',
            'max_price',
            'adjusted_price',
            'is_price_adjusted',
            'price_adjustment_percentage',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderSetPaymentCardSerializer(serializers.Serializer):
    """Assign a saved card to an order (rider)."""

    card_id = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""
    order_items = OrderItemSerializer(many=True, read_only=True)
    user = UserDetailSerializer(read_only=True)
    saved_card = SavedCardSerializer(read_only=True, allow_null=True)
    client_rating = serializers.SerializerMethodField()
    client_tip_count = serializers.SerializerMethodField()
    payment_type = serializers.ChoiceField(choices=Order.PaymentType.choices, read_only=True, allow_null=True)
    order_type = serializers.ChoiceField(
        choices=Order.OrderType.choices,
        help_text="Order type: pickup (Pickup), for_me (For Me)"
    )
    status = serializers.ChoiceField(
        choices=Order.OrderStatus.choices,
        help_text=(
            "Order status: scheduled, pending, accepted, on_the_way, arrived, "
            "in_progress, completed, cancelled, rejected"
        )
    )
    schedule = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_code', 'user', 'saved_card', 'client_rating', 'client_tip_count',
            'status', 'order_type', 'payment_type',
            'stripe_trip_payment_intent_id', 'stripe_trip_payment_status',
            'stripe_trip_payment_amount_cents', 'stripe_trip_payment_currency',
            'order_items', 'schedule',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'order_code', 'created_at', 'updated_at',
            'stripe_trip_payment_intent_id', 'stripe_trip_payment_status',
            'stripe_trip_payment_amount_cents', 'stripe_trip_payment_currency',
        ]

    def get_client_rating(self, obj):
        cached = getattr(obj, '_client_rating', None)
        if cached is not None:
            return round(float(cached), 2)
        if not obj.user_id:
            return None
        agg = TripRating.objects.filter(
            rider_id=obj.user_id,
            status='approved',
        ).aggregate(avg=Avg('rating'))
        avg = agg['avg']
        return round(float(avg), 2) if avg is not None else None

    def get_client_tip_count(self, obj):
        cached = getattr(obj, '_client_tip_count', None)
        if cached is not None:
            return int(cached)
        if not obj.user_id:
            return 0
        return TripRating.objects.filter(
            rider_id=obj.user_id,
            status='approved',
            tip_amount__gt=0,
        ).count()

    def get_schedule(self, obj):
        from apps.order.services.scheduled_ride import schedule_payload

        return schedule_payload(obj)


class OrderDetailSerializer(OrderSerializer):
    """Order by id: includes assigned driver (same shape as rider WebSocket) when status has ACCEPTED OrderDriver."""

    driver = serializers.SerializerMethodField()
    order_driver = serializers.SerializerMethodField()

    class Meta(OrderSerializer.Meta):
        fields = list(OrderSerializer.Meta.fields) + ['driver', 'order_driver']

    def _accepted_order_driver(self, obj):
        for row in obj.order_drivers.all():
            if row.status == OrderDriver.DriverRequestStatus.ACCEPTED:
                return row
        return None

    def get_driver(self, obj):
        od = self._accepted_order_driver(obj)
        if not od or not od.driver_id:
            return None
        from ..services.rider_orders_websocket import build_driver_for_rider

        return build_driver_for_rider(od.driver, request=self.context.get('request'))

    def get_order_driver(self, obj):
        from ..services.rider_orders_websocket import _order_driver_row

        return _order_driver_row(self._accepted_order_driver(obj))


class PriceEstimateSerializer(serializers.Serializer):
    """
    Serializer for price estimation
    """
    latitude_from = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    longitude_from = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    latitude_to = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    longitude_to = serializers.DecimalField(
        max_digits=24,
        decimal_places=18,
        required=True,
        coerce_to_string=False
    )
    stops = RideStopInputSerializer(
        many=True,
        required=False,
        help_text='Optional multi-stop waypoints. When present, distance is the full route.',
    )

    def validate(self, data):
        """
        Reject invalid GPS (often intermittent from device); avoids odd distance/price edge cases.
        """
        lat_from = float(data['latitude_from'])
        lon_from = float(data['longitude_from'])
        lat_to = float(data['latitude_to'])
        lon_to = float(data['longitude_to'])
        if not (-90.0 <= lat_from <= 90.0):
            raise serializers.ValidationError(
                {'latitude_from': 'Latitude must be between -90 and 90.'}
            )
        if not (-90.0 <= lat_to <= 90.0):
            raise serializers.ValidationError(
                {'latitude_to': 'Latitude must be between -90 and 90.'}
            )
        if not (-180.0 <= lon_from <= 180.0):
            raise serializers.ValidationError(
                {'longitude_from': 'Longitude must be between -180 and 180.'}
            )
        if not (-180.0 <= lon_to <= 180.0):
            raise serializers.ValidationError(
                {'longitude_to': 'Longitude must be between -180 and 180.'}
            )
        raw_stops = data.get('stops')
        if raw_stops:
            try:
                data['_waypoints'] = parse_stops_payload(
                    [dict(s) for s in raw_stops],
                    pickup={'address': '', 'lat': lat_from, 'lng': lon_from},
                    dropoff={'address': '', 'lat': lat_to, 'lng': lon_to},
                )
            except MultiStopError as e:
                raise serializers.ValidationError({'stops': str(e)})
        return data


class PriceEstimateManagePriceSerializer(PriceEstimateSerializer):
    """
    Plan bosqichi: buyurtma yaratilmasdan narxni min/max oralig'ida tekshirish.
    price-estimate dagi ``id`` / ``ride_type_id`` bilan bir xil maydondan foydalaning.
    """

    ride_type_id = serializers.IntegerField(required=True)
    adjusted_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        coerce_to_string=False,
    )

    def validate_ride_type_id(self, value):
        if not RideType.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('Ride type not found or inactive.')
        return value


class OrderItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating OrderItem with ride_type
    """
    ride_type_id = serializers.IntegerField(write_only=True, required=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'ride_type_id',
            'ride_type',
            'distance_km',
            'calculated_price',
            'original_price',
            'min_price',
            'max_price',
            'adjusted_price',
            'is_price_adjusted',
            'price_adjustment_percentage',
            'updated_at'
        ]
        read_only_fields = ['id', 'ride_type', 'distance_km', 'calculated_price', 'original_price', 'min_price', 'max_price', 'adjusted_price', 'is_price_adjusted', 'price_adjustment_percentage', 'updated_at']
    
    def validate_ride_type_id(self, value):
        """
        Validate that ride_type exists and is active
        """
        from ..models import RideType
        try:
            ride_type = RideType.objects.get(id=value, is_active=True)
        except RideType.DoesNotExist:
            raise serializers.ValidationError("Ride type not found or inactive.")
        return value
    
    def update(self, instance, validated_data):
        """
        Update OrderItem with ride_type and calculate price
        """
        ride_type_id = validated_data.pop('ride_type_id')
        from ..models import RideType
        ride_type = RideType.objects.get(id=ride_type_id)
        
        instance.ride_type = ride_type
        
        # Save will automatically calculate distance and prices via save() method
        instance.save()
        return instance


class OrderItemManagePriceSerializer(serializers.Serializer):
    """
    Serializer for managing (adjusting) OrderItem price
    """
    adjusted_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=True,
        help_text="New price to set (must be between min_price and max_price)"
    )
