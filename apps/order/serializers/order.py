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


class OrderCreateSerializer(serializers.Serializer):
    address_from = serializers.CharField(max_length=255, required=True)
    address_to = serializers.CharField(max_length=255, required=True)
    latitude_from = serializers.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        required=True,
        coerce_to_string=False
    )
    longitude_from = serializers.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        required=True,
        coerce_to_string=False
    )
    latitude_to = serializers.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        required=True,
        coerce_to_string=False
    )
    longitude_to = serializers.DecimalField(
        max_digits=10, 
        decimal_places=7, 
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

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user

        order_type_value = validated_data.pop('order_type')
        order_type = Order.OrderType.PICKUP if order_type_value == 1 else Order.OrderType.FOR_ME
        ride_type_id = validated_data.pop('ride_type_id', None)
        payment_type = validated_data.pop('payment_type', 'card')
        adjusted_price = validated_data.pop('adjusted_price', None)

        order = Order.objects.create(
            user=user,
            order_type=order_type,
            payment_type=payment_type,
            status=Order.OrderStatus.PENDING
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
        # ride_type so distance_km, estimated_time, calculated_price, min_price, max_price etc. are filled in response
        ride_type = None
        if ride_type_id:
            ride_type = RideType.objects.filter(id=ride_type_id, is_active=True).first()
        if not ride_type:
            ride_type = RideType.objects.filter(is_active=True).order_by('id').first()
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
        def _schedule_driver_assignment(oid):
            """Celery/sync assign — faqat DB commitdan keyin (boshqa process orderni ko‘radi)."""
            try:
                from apps.order.tasks import assign_driver_to_order_async
                assign_driver_to_order_async.delay(oid)
            except ImportError:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Celery task not available, using sync driver assignment")
                from apps.order.services.driver_assignment_service import DriverAssignmentService
                try:
                    o = Order.objects.get(pk=oid)
                    DriverAssignmentService.assign_to_next_driver(o)
                except Order.DoesNotExist:
                    logger.error("Order %s not found for sync driver assignment", oid)
                except Exception as e:
                    logger.error("Failed to assign driver to order %s: %s", oid, e)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error("Failed to schedule async driver assignment for order %s: %s", oid, e)

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
            "Order status: pending, accepted, on_the_way, arrived, in_progress, "
            "completed, cancelled, rejected"
        )
    )
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_code', 'user', 'saved_card', 'client_rating', 'client_tip_count',
            'status', 'order_type', 'payment_type',
            'stripe_trip_payment_intent_id', 'stripe_trip_payment_status',
            'stripe_trip_payment_amount_cents', 'stripe_trip_payment_currency',
            'order_items',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'order_code', 'created_at', 'updated_at',
            'stripe_trip_payment_intent_id', 'stripe_trip_payment_status',
            'stripe_trip_payment_amount_cents', 'stripe_trip_payment_currency',
        ]

    def get_client_rating(self, obj):
        """
        Average rating (1-5) that drivers have given to this order's rider (user).
        Only approved ratings are counted.
        """
        if not obj.user_id:
            return None
        agg = TripRating.objects.filter(
            rider_id=obj.user_id,
            status='approved',
        ).aggregate(avg=Avg('rating'))
        avg = agg['avg']
        return round(float(avg), 2) if avg is not None else None

    def get_client_tip_count(self, obj):
        """
        Total number of times this rider has tipped any driver (approved ratings with tip_amount > 0).
        """
        if not obj.user_id:
            return 0
        return TripRating.objects.filter(
            rider_id=obj.user_id,
            status='approved',
            tip_amount__gt=0,
        ).count()


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
        max_digits=10, 
        decimal_places=7, 
        required=True,
        coerce_to_string=False
    )
    longitude_from = serializers.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        required=True,
        coerce_to_string=False
    )
    latitude_to = serializers.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        required=True,
        coerce_to_string=False
    )
    longitude_to = serializers.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        required=True,
        coerce_to_string=False
    )


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
