from django.db import models
from apps.accounts.models import CustomUser


class Order(models.Model):
    
    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'
        REFUNDED = 'refunded', 'Refunded'
        FAILED = 'failed', 'Failed'
    
    class OrderType(models.TextChoices):
        PICKUP = 'pickup', 'Pickup'
        FOR_ME = 'for_me', 'For Me'
    
    order_code = models.CharField(max_length=255, verbose_name='Order Code', null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.PICKUP)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    
    def __str__(self):
        order_code = self.order_code or "No Code"
        user_name = self.user.get_full_name() if self.user else "Unknown User"
        status = self.status or "Unknown"
        return f"{order_code} - {user_name} - {status}"
    
    def generate_order_code(self):
        if self.id:
            return f"ORD-{self.id:06d}"
        return "ORD-000000"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.order_code:
            self.order_code = self.generate_order_code()
            super().save(update_fields=['order_code'])
    
    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = '01 Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='order_user_idx'),
            models.Index(fields=['status'], name='order_status_idx'),
            models.Index(fields=['created_at'], name='order_created_idx'),
        ]


class RideType(models.Model):
    name = models.CharField(max_length=50, verbose_name='Name', null=True, blank=True)  
    name_large = models.CharField(max_length=50, null=True, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Base Price', null=True, blank=True)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Price Per KM', null=True, blank=True)
    capacity = models.IntegerField(verbose_name='Capacity', null=True, blank=True)
    icon = models.CharField(max_length=50, null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    is_ev = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def calculate_price(self, distance_km, surge_multiplier=1.00):
        """
        Calculate price based on distance and surge multiplier
        """
        from decimal import Decimal
        
        # Convert all to Decimal to avoid type errors
        base_price = Decimal(str(self.base_price)) if self.base_price else Decimal('0')
        price_per_km = Decimal(str(self.price_per_km)) if self.price_per_km else Decimal('0')
        distance = Decimal(str(distance_km))
        surge = Decimal(str(surge_multiplier))
        
        base_total = base_price + (price_per_km * distance)
        final_price = base_total * surge
        return float(round(final_price, 2))
    
    objects = models.Manager()
    
    def __str__(self):
        if self.name and self.name_large:
            return f"{self.name} - {self.name_large}"
        elif self.name:
            return self.name
        elif self.name_large:
            return self.name_large
        return 'Ride Type'
    
    class Meta:
        verbose_name = 'Ride Type'
        verbose_name_plural = '02 Ride Types'
        ordering = ['name']
        indexes = [
            models.Index(fields=['created_at'], name='ride_type_created_idx'),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    address_from = models.CharField(max_length=255, verbose_name='Address From', null=True, blank=True)
    address_to = models.CharField(max_length=255, verbose_name='Address To', null=True, blank=True)
    latitude_from = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='Latitude From', null=True, blank=True)
    longitude_from = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='Longitude From', null=True, blank=True)
    latitude_to = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='Latitude To', null=True, blank=True)
    longitude_to = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='Longitude To', null=True, blank=True)
    stop_sequence = models.IntegerField(
    default=1,
    verbose_name='Stop Sequence',
    help_text='Order of stops (1 = first stop, 2 = second stop, etc.)'
    )
    is_final_stop = models.BooleanField(
        default=False,
        verbose_name='Is Final Stop',
        help_text='Whether this is the final destination'
    )
    ride_type = models.ForeignKey(
        'RideType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='Ride Type'
    )
    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Distance (KM)'
    )
    estimated_time = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Estimated Time'
    )
    calculated_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Calculated Price',
        help_text='Automatically calculated price based on distance and surge'
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Original Price',
        help_text='Initial calculated price before user adjustment'
    )
    adjusted_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Adjusted Price',
        help_text='Price after user adjustment (manage price)'
    )
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Min Price',
        help_text='Minimum allowed price (e.g., 80% of original)'
    )
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Max Price',
        help_text='Maximum allowed price (e.g., 150% of original)'
    )
    price_adjustment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Price Adjustment %',
        help_text='Percentage change from original price'
    )
    is_price_adjusted = models.BooleanField(
        default=False,
        verbose_name='Is Price Adjusted',
        help_text='Whether user has adjusted the price'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    
    def __str__(self):
        if self.order and self.order.user:
            user_name = self.order.user.get_full_name()
        else:
            user_name = "Unknown User"
        address_from = self.address_from or "Unknown"
        address_to = self.address_to or "Unknown"
        return f"{user_name} - {address_from} - {address_to}"
    
    def calculate_price_range(self, min_percentage=20, max_percentage=50):
        """
        Calculate min and max price based on original price
        Default: -20% to +50%
        """
        from decimal import Decimal, ROUND_HALF_UP
        
        if not self.original_price:
            return None, None
        
        min_price = self.original_price * (Decimal('1.00') - Decimal(str(min_percentage / 100)))
        max_price = self.original_price * (Decimal('1.00') + Decimal(str(max_percentage / 100)))
        
        min_price = min_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        max_price = max_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return min_price, max_price
    
    def adjust_price(self, new_price):
        """
        Adjust price and validate against min/max limits
        """
        from decimal import Decimal
        
        if not self.original_price:
            raise ValueError("Original price not set")
        
        if not self.min_price or not self.max_price:
            self.min_price, self.max_price = self.calculate_price_range()
            self.save()
        
        # Validate price range
        if self.min_price and new_price < self.min_price:
            raise ValueError(f"Price cannot be less than {self.min_price}")
        if self.max_price and new_price > self.max_price:
            raise ValueError(f"Price cannot be more than {self.max_price}")
        
        # Set adjusted price
        self.adjusted_price = Decimal(str(new_price))
        self.is_price_adjusted = True
        
        # Calculate adjustment percentage
        adjustment = ((self.adjusted_price - self.original_price) / self.original_price) * 100
        self.price_adjustment_percentage = round(adjustment, 2)
        
        # Update calculated_price to adjusted_price
        self.calculated_price = self.adjusted_price
        
        self.save()
        
        return self.adjusted_price
    
    def get_final_price(self):
        """
        Get final price (adjusted if exists, otherwise calculated)
        """
        if self.adjusted_price:
            return self.adjusted_price
        return self.calculated_price or self.original_price
    
    def calculate_distance_automatically(self):
        """
        Calculate distance from latitude and longitude if not provided
        """
        from apps.order.services.surge_pricing_service import calculate_distance
        
        if self.distance_km:
            return  # Already set
        
        if (self.latitude_from and self.longitude_from and 
            self.latitude_to and self.longitude_to):
            try:
                distance = calculate_distance(
                    float(self.latitude_from),
                    float(self.longitude_from),
                    float(self.latitude_to),
                    float(self.longitude_to)
                )
                self.distance_km = round(distance, 2)
            except (ValueError, TypeError):
                pass
    
    def calculate_prices_automatically(self):
        """
        Automatically calculate prices based on ride_type, distance, and surge
        """
        from decimal import Decimal
        from apps.order.services import SurgePricingService
        
        # Skip if already has original_price and not updating
        if self.original_price and not self._state.adding:
            # Only recalculate if ride_type or distance changed
            return
        
        # Need ride_type and distance to calculate price
        if not self.ride_type or not self.distance_km:
            return
        
        # Calculate surge multiplier
        surge_multiplier = Decimal('1.00')
        if self.latitude_from and self.longitude_from:
            surge_multiplier = Decimal(str(SurgePricingService.get_multiplier(
                float(self.latitude_from),
                float(self.longitude_from)
            )))
        
        # Calculate original price using RideType method
        if self.ride_type.base_price and self.ride_type.price_per_km:
            original_price = self.ride_type.calculate_price(
                float(self.distance_km),
                float(surge_multiplier)
            )
            self.original_price = Decimal(str(original_price))
            
            # Set calculated_price same as original_price (initially)
            if not self.adjusted_price:
                self.calculated_price = self.original_price
            
            # Calculate min and max prices
            self.min_price, self.max_price = self.calculate_price_range()
    
    def update_adjustment_info(self):
        """
        Update price adjustment information if adjusted_price is set
        """
        from decimal import Decimal
        
        if self.adjusted_price and self.original_price:
            # Calculate adjustment percentage
            adjustment = ((self.adjusted_price - self.original_price) / self.original_price) * 100
            self.price_adjustment_percentage = round(adjustment, 2)
            self.is_price_adjusted = True
            # Update calculated_price to adjusted_price
            self.calculated_price = self.adjusted_price
        else:
            # Reset if adjusted_price is removed
            if not self.adjusted_price:
                self.is_price_adjusted = False
                self.price_adjustment_percentage = None
                # Reset calculated_price to original_price
                if self.original_price:
                    self.calculated_price = self.original_price
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically calculate fields
        """
        # Calculate distance if not provided
        self.calculate_distance_automatically()
        
        # Calculate prices automatically
        self.calculate_prices_automatically()
        
        # Update adjustment info if adjusted_price is set
        self.update_adjustment_info()
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = '03 Order Items'
        ordering = ['-created_at', 'order', 'stop_sequence']
        indexes = [
            models.Index(fields=['order'], name='order_item_order_idx'),
            models.Index(fields=['created_at'], name='order_item_created_idx'),
            models.Index(fields=['ride_type'], name='order_item_ride_type_idx'),
        ]


class OrderPreferences(models.Model):
    
    class ChattingPreference(models.TextChoices):
        NO_COMMUNICATION = 'no_communication', 'No Communication'
        CASUAL = 'casual', 'Casual'
        FRIENDLY = 'friendly', 'Friendly'
    
    class TemperaturePreference(models.TextChoices):
        WARM = 'warm', 'Warm (25°C and above)'
        COMFORTABLE = 'comfortable', 'Comfortable (22-24°C)'
        COOL = 'cool', 'Cool (18-21°C)'
        COLD = 'cold', 'Cold (below 18°C)'
    
    class MusicPreference(models.TextChoices):
        POP = 'pop', 'Pop'
        ROCK = 'rock', 'Rock'
        JAZZ = 'jazz', 'Jazz'
        CLASSICAL = 'classical', 'Classical'
        HIP_HOP = 'hip_hop', 'Hip Hop'
        ELECTRONIC = 'electronic', 'Electronic'
        COUNTRY = 'country', 'Country'
        NO_MUSIC = 'no_music', 'No Music'
    
    class VolumeLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        MUTE = 'mute', 'Mute'
    
    class PetPreferences(models.TextChoices):
        YES = 'yes', 'Yes'
        NO = 'no', 'No'
    
    class KidsChairPreferences(models.TextChoices):
        YES = 'yes', 'Yes'
        NO = 'no', 'No'
    
    class WheelchairPreferences(models.TextChoices):
        YES = 'yes', 'Yes'
        NO = 'no', 'No'
        
    class GenderPreferences(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'
    
    class FavoriteDriverPreferences(models.TextChoices):
        YES = 'yes', 'Yes'
        NO = 'no', 'No'
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_preferences')
    
    # Rider Preferences
    chatting_preference = models.CharField(max_length=20, choices=ChattingPreference.choices, default=ChattingPreference.NO_COMMUNICATION)
    temperature_preference = models.CharField(max_length=20, choices=TemperaturePreference.choices, default=TemperaturePreference.COMFORTABLE)
    music_preference = models.CharField(max_length=20, choices=MusicPreference.choices, default=MusicPreference.POP)
    volume_level = models.CharField(max_length=10, choices=VolumeLevel.choices, default=VolumeLevel.MEDIUM)
    pet_preference = models.CharField(max_length=20, choices=PetPreferences.choices, default=PetPreferences.NO)
    kids_chair_preference = models.CharField(max_length=20, choices=KidsChairPreferences.choices, default=KidsChairPreferences.NO)
    wheelchair_preference = models.CharField(max_length=20, choices=WheelchairPreferences.choices, default=WheelchairPreferences.NO)
    
    # Driver Preferences    
    gender_preference = models.CharField(max_length=20, choices=GenderPreferences.choices, default=GenderPreferences.OTHER)
    favorite_driver_preference = models.CharField(max_length=20, choices=FavoriteDriverPreferences.choices, default=FavoriteDriverPreferences.NO)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = models.Manager()

    class Meta:
        verbose_name = 'Order Preferences'
        verbose_name_plural = '04 Order Preferences'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='order_preferences_order_idx'),
            models.Index(fields=['created_at'], name='order_preferences_created_idx'),
        ]
        
class AdditionalPassenger(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='additional_passengers')
    full_name = models.CharField(max_length=255, verbose_name='Full Name', null=True, blank=True)
    phone_number = models.CharField(max_length=255, verbose_name='Phone Number', null=True, blank=True)
    email = models.EmailField(max_length=255, verbose_name='Email', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = models.Manager()
    
    def __str__(self):
        if self.order and self.order.user:
            user_name = self.order.user.get_full_name()
        else:
            user_name = "Unknown User"
        passenger_name = self.full_name or "Unknown"
        return f"{user_name} - {passenger_name}"
    
    class Meta:
        verbose_name = 'Additional Passenger'
        verbose_name_plural = '04 Additional Passengers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='add_pass_order_idx'),
            models.Index(fields=['created_at'], name='add_pass_created_idx'),
        ]


class OrderSchedule(models.Model):
    
    class ScheduleType(models.TextChoices):
        PICKUP_AT = 'pickup_at', 'Pickup At'
        DROP_OFF_BY = 'drop_off_by', 'Drop Off By'
    
    class ScheduleTime(models.TextChoices):
        TODAY = 'today', 'Today'
        TOMORROW = 'tomorrow', 'Tomorrow'
        SELECT_DATE = 'select_date', 'Select Date'
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_schedules', verbose_name='Order', null=True, blank=True)
    schedule_type = models.CharField(max_length=20, choices=ScheduleType.choices, default=ScheduleType.PICKUP_AT)
    schedule_date = models.DateField(verbose_name='Schedule Date', null=True, blank=True)
    schedule_time = models.TimeField(verbose_name='Schedule Time', null=True, blank=True)
    schedule_time_type = models.CharField(max_length=20, choices=ScheduleTime.choices, default=ScheduleTime.TODAY)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = models.Manager()
    
    def __str__(self):
        return f"{self.order.order_code} - {self.schedule_date} - {self.schedule_time}"
    
    class Meta:
        verbose_name = 'Order Schedule'
        verbose_name_plural = '05 Order Schedules'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='order_schedule_order_idx'),
            models.Index(fields=['schedule_date'], name='ord_sched_date_idx'),
            models.Index(fields=['schedule_time'], name='ord_sched_time_idx'),
            models.Index(fields=['created_at'], name='order_schedule_created_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.schedule_date:
            self.schedule_date = self.order.created_at.date()
        if not self.schedule_time:
            self.schedule_time = self.order.created_at.time()
        super().save(*args, **kwargs)

class OrderDriver(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_drivers')
    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='order_drivers')
    pin_code = models.CharField(max_length=255, verbose_name='Pin Code', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = models.Manager()
    
    def __str__(self):
        if self.order and self.order.user:
            user_name = self.order.user.get_full_name()
        else:
            user_name = "Unknown User"
        if self.driver:
            driver_name = self.driver.get_full_name()
        else:
            driver_name = "Unknown Driver"
        return f"{user_name} - {driver_name}"
    
    class Meta:
        verbose_name = 'Order Driver'
        verbose_name_plural = '05 Order Drivers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='order_driver_order_idx'),
            models.Index(fields=['driver'], name='order_driver_driver_idx'),
            models.Index(fields=['created_at'], name='order_driver_created_idx'),
        ]


class SurgePricing(models.Model):
    """
    Dynamic pricing multiplier for surge pricing
    """
    name = models.CharField(max_length=100, verbose_name='Name')
    multiplier = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.00,
        verbose_name='Multiplier',
        help_text="1.00 = normal, 1.5 = 50% increase, 0.8 = 20% decrease"
    )
    
    start_time = models.TimeField(null=True, blank=True, verbose_name='Start Time')
    end_time = models.TimeField(null=True, blank=True, verbose_name='End Time')
    days_of_week = models.JSONField(default=list, verbose_name='Days of Week', help_text="[0,1,2,3,4] - Monday to Friday")
    
    zone_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='Zone Name')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Latitude')
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Longitude')
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=5.0, verbose_name='Radius (KM)')
    
    min_available_drivers = models.IntegerField(null=True, blank=True, verbose_name='Min Available Drivers')
    max_available_drivers = models.IntegerField(null=True, blank=True, verbose_name='Max Available Drivers')
    
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    priority = models.IntegerField(default=0, verbose_name='Priority', help_text="Which one is checked first")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    objects = models.Manager()
    
    def __str__(self):
        name = self.name or "Unknown"
        multiplier = self.multiplier or 1.00
        return f"{name} - {multiplier}x"
    
    class Meta:
        verbose_name = 'Surge Pricing'
        verbose_name_plural = '06 Surge Pricings'
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['is_active', 'priority'], name='surge_active_priority_idx'),
            models.Index(fields=['latitude', 'longitude'], name='surge_location_idx'),
        ]


class CancelOrder(models.Model):
    
    class CancelReason(models.TextChoices):
        CHANGE_IN_PLANS = 'change_in_plans', 'Change in Plans'
        WAITING_FOR_LONG_TIME = 'waiting_for_long_time', 'Waiting for Long Time'
        DRIVER_DENIED_TO_GO_TO_DESTINATION = 'driver_denied_to_go_to_destination', 'Driver Denied to Go to Destination'
        DRIVER_DENIED_TO_COME_TO_PICKUP = 'driver_denied_to_come_to_pickup', 'Driver Denied to Come to Pickup'
        WRONG_ADDRESS_SHOWN = 'wrong_address_shown', 'Wrong Address Shown'
        THE_PRICE_IS_NOT_REASONABLE = 'the_price_is_not_reasonable', 'The Price is Not Reasonable'
        EMERGENCY_SITUATION = 'emergency_situation', 'Emergency Situation'
        OTHER = 'other', 'Other'
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='cancel_orders')
    driver = models.ForeignKey(OrderDriver, on_delete=models.CASCADE, related_name='cancel_orders')
    reason = models.CharField(max_length=255, choices=CancelReason.choices, default=CancelReason.OTHER)
    other_reason = models.TextField(verbose_name='Other Reason', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = models.Manager()
    
    def __str__(self):
        if self.order and self.order.user:
            user_name = self.order.user.get_full_name()
        else:
            user_name = "Unknown User"
        reason = self.reason or "Unknown"
        return f"{user_name} - {reason}"
    
    class Meta:
        verbose_name = 'Cancel Order'
        verbose_name_plural = '07 Cancel Orders'
        ordering = ['-created_at']


class OrderPaymentSplit(models.Model):
    """
    Split fare payment for co-riders
    """
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class SplitType(models.TextChoices):
        EVEN = 'even', 'Even Split'
        CUSTOM = 'custom', 'Custom Split'
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payment_splits',
        verbose_name='Order'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='payment_splits',
        verbose_name='Co-Rider',
        help_text='User who needs to pay their share'
    )
    
    # Split Information
    split_type = models.CharField(
        max_length=20,
        choices=SplitType.choices,
        default=SplitType.EVEN,
        verbose_name='Split Type',
        help_text='Even split or custom amount'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Amount',
        help_text='Amount this user needs to pay'
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Percentage',
        help_text='Percentage of total fare (for custom splits)'
    )
    
    # Payment Status
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name='Payment Status'
    )
    
    # Invitation
    invitation_token = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Invitation Token',
        help_text='Unique token for split fare invitation link'
    )
    invited_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Invited At'
    )
    invitation_accepted = models.BooleanField(
        default=False,
        verbose_name='Invitation Accepted',
        help_text='Whether co-rider accepted the split fare invitation'
    )
    
    # Payment Confirmation
    payment_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Payment Confirmed At'
    )
    payment_failed_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name='Payment Failed Reason',
        help_text='Reason if payment failed'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    objects = models.Manager()
    
    def __str__(self):
        if self.order and self.order.user:
            order_user = self.order.user.get_full_name()
        else:
            order_user = "Unknown"
        if self.user:
            co_rider = self.user.get_full_name()
        else:
            co_rider = "Unknown"
        return f"{order_user} - {co_rider} - {self.amount} ({self.payment_status})"
    
    def generate_invitation_token(self):
        """
        Generate unique invitation token for split fare link
        """
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(32))
        while OrderPaymentSplit.objects.filter(invitation_token=token).exists():
            token = ''.join(secrets.choice(alphabet) for _ in range(32))
        return token
    
    def save(self, *args, **kwargs):
        """
        Generate invitation token if not set
        """
        if not self.invitation_token:
            self.invitation_token = self.generate_invitation_token()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Order Payment Split'
        verbose_name_plural = '08 Order Payment Splits'
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['order'], name='payment_split_order_idx'),
            models.Index(fields=['user'], name='payment_split_user_idx'),
            models.Index(fields=['payment_status'], name='payment_split_status_idx'),
            models.Index(fields=['invitation_token'], name='payment_split_token_idx'),
            models.Index(fields=['order', 'payment_status'], name='payment_split_order_status_idx'),
        ]
        

class PromoCode(models.Model):
    """
    Promo code model - can be user-specific or general
    """
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED_AMOUNT = 'fixed_amount', 'Fixed Amount'
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Promo Code',
        help_text='Unique promo code (e.g., SAVE20, WELCOME50)'
    )
    
    # Discount Information
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
        verbose_name='Discount Type'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Discount Value',
        help_text='Percentage (e.g., 20 for 20%) or Fixed Amount (e.g., 10.00)'
    )
    
    # User-specific or General
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='promo_codes',
        null=True,
        blank=True,
        verbose_name='User',
        help_text='If set, this promo code is only for this specific user. If null, it\'s general.'
    )
    
    # Usage Limits
    max_uses = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Max Uses',
        help_text='Maximum number of times this code can be used. Null = unlimited.'
    )
    current_uses = models.IntegerField(
        default=0,
        verbose_name='Current Uses',
        help_text='Number of times this code has been used'
    )
    
    # Validity
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Valid From',
        help_text='Start date/time for promo code validity'
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Valid Until',
        help_text='End date/time for promo code validity'
    )
    
    # Minimum Order Amount
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Minimum Order Amount',
        help_text='Minimum order amount required to use this promo code'
    )
    
    # Maximum Discount Amount (for percentage discounts)
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Maximum Discount Amount',
        help_text='Maximum discount amount (for percentage discounts)'
    )
    
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name='Description',
        help_text='Description of the promo code'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    objects = models.Manager()
    
    def __str__(self):
        user_info = f" - {self.user.get_full_name()}" if self.user else " - General"
        return f"{self.code}{user_info}"
    
    def is_valid(self):
        """
        Check if promo code is valid (active, not expired, not exceeded max uses)
        """
        from django.utils import timezone
        
        if not self.is_active:
            return False
        
        now = timezone.now()
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        
        return True
    
    def can_be_used_by_user(self, user):
        """
        Check if this promo code can be used by specific user
        """
        # If user-specific, check if it's for this user
        if self.user:
            return self.user == user
        
        # General promo code can be used by anyone
        return True
    
    def calculate_discount(self, order_amount):
        """
        Calculate discount amount based on order amount
        """
        from decimal import Decimal
        
        if not self.is_valid():
            return Decimal('0.00')
        
        # Check minimum order amount
        if self.min_order_amount and order_amount < self.min_order_amount:
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = (order_amount * self.discount_value) / 100
            
            # Apply maximum discount limit if set
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:  # fixed_amount
            discount = self.discount_value
        
        return round(discount, 2)
    
    class Meta:
        verbose_name = 'Promo Code'
        verbose_name_plural = '09 Promo Codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code'], name='promo_code_code_idx'),
            models.Index(fields=['user'], name='promo_code_user_idx'),
            models.Index(fields=['is_active'], name='promo_code_active_idx'),
            models.Index(fields=['valid_from', 'valid_until'], name='promo_code_validity_idx'),
        ]


class OrderPromoCode(models.Model):
    """
    Promo code applied to an order
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='applied_promo_codes',
        verbose_name='Order'
    )
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_applications',
        verbose_name='Promo Code'
    )
    
    # Discount Information
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Discount Amount',
        help_text='Actual discount amount applied to this order'
    )
    order_amount_before_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Order Amount Before Discount',
        help_text='Order amount before applying discount'
    )
    order_amount_after_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Order Amount After Discount',
        help_text='Order amount after applying discount'
    )
    
    # Applied by
    applied_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='applied_promo_codes',
        verbose_name='Applied By',
        help_text='User who applied this promo code to the order'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    objects = models.Manager()
    
    def __str__(self):
        if self.order:
            order_code = self.order.order_code or "No Code"
        else:
            order_code = "Unknown"
        if self.promo_code:
            promo = self.promo_code.code
        else:
            promo = "Unknown"
        return f"{order_code} - {promo} - {self.discount_amount}"
    
    class Meta:
        verbose_name = 'Order Promo Code'
        verbose_name_plural = '10 Order Promo Codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='order_promo_order_idx'),
            models.Index(fields=['promo_code'], name='order_promo_code_idx'),
            models.Index(fields=['applied_by'], name='order_promo_applied_by_idx'),
        ]