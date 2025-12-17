from rest_framework import serializers
from ..models import Order, OrderItem


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating Order and OrderItem
    """
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
    
    def validate_order_type(self, value):
        """
        Validate order_type: 1 = PICKUP, 2 = FOR_ME
        """
        if value not in [1, 2]:
            raise serializers.ValidationError("order_type must be 1 (PICKUP) or 2 (FOR_ME)")
        return value
    
    def create(self, validated_data):
        """
        Create Order and OrderItem
        After creation, automatically assign to nearest driver (Uber model)
        """
        user = self.context['request'].user
        
        # Convert order_type: 1 = 'pickup', 2 = 'for_me'
        order_type_value = validated_data.pop('order_type')
        order_type = Order.OrderType.PICKUP if order_type_value == 1 else Order.OrderType.FOR_ME
        
        # Create Order
        order = Order.objects.create(
            user=user,
            order_type=order_type,
            status=Order.OrderStatus.PENDING
        )
        
        # Create OrderItem
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
        
        # Automatically assign to nearest driver (Uber model) - ASYNC via Celery task
        try:
            from apps.order.tasks import assign_driver_to_order_async
            assign_driver_to_order_async.delay(order.id)  # Non-blocking async task
        except ImportError:
            # Fallback to sync if Celery task not available
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Celery task not available, using sync driver assignment")
            from apps.order.services.driver_assignment_service import DriverAssignmentService
            try:
                DriverAssignmentService.assign_to_next_driver(order)
            except Exception as e:
                logger.error(f"Failed to assign driver to order {order.id}: {e}")
        except Exception as e:
            # Log error but don't fail order creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to schedule async driver assignment for order {order.id}: {e}")
        
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


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order model
    """
    order_items = OrderItemSerializer(many=True, read_only=True)
    order_type = serializers.ChoiceField(
        choices=Order.OrderType.choices,
        help_text="Order type: pickup (Pickup), for_me (For Me)"
    )
    status = serializers.ChoiceField(
        choices=Order.OrderStatus.choices,
        help_text="Order status: pending, confirmed, cancelled, completed, refunded, failed"
    )
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_code',
            'user',
            'status',
            'order_type',
            'order_items',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'order_code', 'created_at', 'updated_at']


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
