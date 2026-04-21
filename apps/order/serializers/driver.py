from rest_framework import serializers

from apps.accounts.models import CustomUser, DriverPreferences
from ..models import Order, OrderItem, OrderDriver, DriverCashout, TripRating
from ..services.surge_pricing_service import calculate_distance


class DriverNearbyOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for showing nearby orders to drivers.
    Includes distance from driver and basic route info.
    """

    address_from = serializers.SerializerMethodField()
    address_to = serializers.SerializerMethodField()
    latitude_from = serializers.SerializerMethodField()
    longitude_from = serializers.SerializerMethodField()
    latitude_to = serializers.SerializerMethodField()
    longitude_to = serializers.SerializerMethodField()
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

    def get_address_from(self, obj):
        item = obj.order_items.first()
        return item.address_from if item else None

    def get_address_to(self, obj):
        item = obj.order_items.first()
        return item.address_to if item else None

    def get_latitude_from(self, obj):
        item = obj.order_items.first()
        return item.latitude_from if item else None

    def get_longitude_from(self, obj):
        item = obj.order_items.first()
        return item.longitude_from if item else None

    def get_latitude_to(self, obj):
        item = obj.order_items.first()
        return item.latitude_to if item else None

    def get_longitude_to(self, obj):
        item = obj.order_items.first()
        return item.longitude_to if item else None


class DriverOrderActionSerializer(serializers.Serializer):
    """
    Serializer for driver actions on orders (accept / reject).
    """

    order_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['accept', 'reject'])


class DriverOrderLifecycleSerializer(serializers.Serializer):
    """Body: order_id — driver lifecycle steps (on the way, arrived)."""

    order_id = serializers.IntegerField()


class DriverPickupSerializer(serializers.Serializer):
    """Serializer for driver pickup confirmation (client in car)."""
    order_id = serializers.IntegerField()

    def validate_order_id(self, value):
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        return value


class DriverCompleteSerializer(serializers.Serializer):
    """Serializer for driver complete/dropoff confirmation (ride finished)."""
    order_id = serializers.IntegerField()

    def validate_order_id(self, value):
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        return value

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

    latitude = serializers.DecimalField(max_digits=22, decimal_places=14)
    longitude = serializers.DecimalField(max_digits=22, decimal_places=14)


class DriverLocationSerializer(serializers.Serializer):
    """
    Serializer for returning driver's current location to rider.
    """

    driver_id = serializers.IntegerField()
    latitude = serializers.DecimalField(max_digits=22, decimal_places=14)
    longitude = serializers.DecimalField(max_digits=22, decimal_places=14)
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


class DriverOnlineStatusSerializer(serializers.Serializer):
    """Serializer for driver online/offline status."""
    is_online = serializers.BooleanField()


class DriverOverviewSerializer(serializers.Serializer):
    """Overview stats (Last 30 days). Figma: Rides, Made in Today, Made in Week, Tip, Promotion."""
    rides = serializers.IntegerField()
    made_in_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    made_in_week = serializers.DecimalField(max_digits=12, decimal_places=2)
    tip = serializers.DecimalField(max_digits=12, decimal_places=2)
    promotion = serializers.DecimalField(max_digits=12, decimal_places=2)


class DriverCashoutSerializer(serializers.ModelSerializer):
    """Cashout history item. Figma: 4 Apr 2025 Pending / $148.00 + payment_type."""
    payment_type = serializers.ChoiceField(choices=DriverCashout.PaymentType.choices, read_only=True)

    class Meta:
        model = DriverCashout
        fields = ['id', 'amount', 'payment_type', 'status', 'created_at']


