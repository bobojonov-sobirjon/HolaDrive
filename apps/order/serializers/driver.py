from rest_framework import serializers

from apps.accounts.models import CustomUser, DriverPreferences
from ..models import Order, OrderItem, OrderDriver
from ..services.surge_pricing_service import calculate_distance


class DriverNearbyOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for showing nearby orders to drivers.
    Includes distance from driver and basic route info.
    """

    address_from = serializers.CharField(source='order_items.first.address_from', read_only=True)
    address_to = serializers.CharField(source='order_items.first.address_to', read_only=True)
    latitude_from = serializers.DecimalField(max_digits=10, decimal_places=7, source='order_items.first.latitude_from', read_only=True)
    longitude_from = serializers.DecimalField(max_digits=10, decimal_places=7, source='order_items.first.longitude_from', read_only=True)
    latitude_to = serializers.DecimalField(max_digits=10, decimal_places=7, source='order_items.first.latitude_to', read_only=True)
    longitude_to = serializers.DecimalField(max_digits=10, decimal_places=7, source='order_items.first.longitude_to', read_only=True)
    distance_to_pickup_km = serializers.FloatField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_code',
            'status',
            'order_type',
            'created_at',
            'address_from',
            'address_to',
            'latitude_from',
            'longitude_from',
            'latitude_to',
            'longitude_to',
            'distance_to_pickup_km',
        ]


class DriverOrderActionSerializer(serializers.Serializer):
    """
    Serializer for driver actions on orders (accept / reject).
    """

    order_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['accept', 'reject'])

    def validate_order_id(self, value):
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        return value


class DriverLocationUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating driver's current GPS location.
    We store it on CustomUser.latitude/longitude.
    """

    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)


class DriverLocationSerializer(serializers.Serializer):
    """
    Serializer for returning driver's current location to rider.
    """

    driver_id = serializers.IntegerField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    updated_at = serializers.DateTimeField()


class DriverInfoSerializer(serializers.Serializer):
    """
    Serializer for driver information (for rider to see driver details).
    Includes driver profile, vehicle info, rating, trips count, etc.
    """
    name = serializers.CharField(help_text="Driver full name")
    avatar = serializers.URLField(allow_null=True, help_text="Driver profile picture URL")
    rating = serializers.FloatField(default=0.0, help_text="Driver rating (0-5, default 0 if no ratings)")
    trips_count = serializers.IntegerField(help_text="Total number of completed trips")
    member_since = serializers.DateField(allow_null=True, help_text="Date when driver joined")
    car_model = serializers.CharField(allow_null=True, help_text="Car brand and model (e.g., Toyota Corolla)")
    color = serializers.CharField(allow_null=True, help_text="Vehicle color")
    plate_number = serializers.CharField(allow_null=True, help_text="Vehicle plate number")
    location = serializers.DictField(
        help_text="Driver current location with latitude, longitude, and updated_at"
    )


class DriverEarningsSerializer(serializers.Serializer):
    """
    Serializer for driver earnings summary.
    """
    today_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    today_rides_count = serializers.IntegerField()
    today_distance_km = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Total distance driven today")
    today_target = serializers.IntegerField(help_text="Target number of rides for today")
    weekly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    weekly_rides_count = serializers.IntegerField()
    weekly_distance_km = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Total distance driven this week")
    monthly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_rides_count = serializers.IntegerField()
    monthly_distance_km = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Total distance driven this month")
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_rides_count = serializers.IntegerField()
    total_distance_km = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Total distance driven (all time)")


class DriverRideHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for driver ride history (completed orders).
    """
    destination = serializers.CharField(source='order_items.first.address_to', read_only=True)
    date = serializers.DateField(source='created_at', read_only=True)
    time = serializers.TimeField(source='created_at', read_only=True)
    distance_km = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    earnings = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_code',
            'destination',
            'date',
            'time',
            'distance_km',
            'duration',
            'earnings',
            'rating',
            'created_at',
        ]
    
    def get_distance_km(self, obj):
        """Get total distance from all order items (sum of all items)."""
        total_distance = 0
        for item in obj.order_items.all():
            if item.distance_km:
                total_distance += float(item.distance_km)
        return round(total_distance, 2) if total_distance > 0 else None
    
    def get_duration(self, obj):
        """Calculate duration from order creation to completion."""
        if obj.status == Order.OrderStatus.COMPLETED and obj.updated_at:
            duration = obj.updated_at - obj.created_at
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes:02d}:{seconds:02d}m"
        return None
    
    def get_earnings(self, obj):
        """Calculate total earnings from all order items."""
        total = 0
        for item in obj.order_items.all():
            if item.calculated_price:
                total += float(item.calculated_price)
        return round(total, 2) if total > 0 else None
    
    def get_rating(self, obj):
        """Get rating for this order if exists."""
        from apps.order.models import TripRating
        try:
            trip_rating = TripRating.objects.get(order=obj, status='approved')
            return trip_rating.rating
        except TripRating.DoesNotExist:
            return None


class DriverOnlineStatusSerializer(serializers.Serializer):
    """
    Serializer for driver online/offline status.
    """
    is_online = serializers.BooleanField()


