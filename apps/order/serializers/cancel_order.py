from rest_framework import serializers
from ..models import CancelOrder, Order


class OrderCancelSerializer(serializers.Serializer):
    RIDER_CANCEL_REASONS = [
        ('change_in_plans', 'Change in Plans'),
        ('waiting_for_long_time', 'Waiting for Long Time'),
        ('driver_denied_to_go_to_destination', 'Driver Denied to Go to Destination'),
        ('driver_denied_to_come_to_pickup', 'Driver Denied to Come to Pickup'),
        ('wrong_address_shown', 'Wrong Address Shown'),
        ('the_price_is_not_reasonable', 'The Price is Not Reasonable'),
        ('emergency_situation', 'Emergency Situation'),
        ('other', 'Other'),
    ]
    
    reason = serializers.ChoiceField(
        choices=RIDER_CANCEL_REASONS,
        required=True,
        help_text="Cancel reason. Available options: change_in_plans, waiting_for_long_time, driver_denied_to_go_to_destination, driver_denied_to_come_to_pickup, wrong_address_shown, the_price_is_not_reasonable, emergency_situation, other"
    )
    other_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Additional reason text (required if reason is 'other')"
    )
    
    def validate(self, data):
        if data.get('reason') == CancelOrder.CancelReason.OTHER and not data.get('other_reason'):
            raise serializers.ValidationError({
                'other_reason': 'Please provide a reason when selecting "other"'
            })
        return data


class DriverCancelSerializer(serializers.Serializer):
    DRIVER_CANCEL_REASONS = [
        ('rider_not_at_pickup', 'Rider Not at Pickup Location'),
        ('rider_asked_to_cancel', 'Rider Asked to Cancel'),
        ('vehicle_issue', 'Vehicle Issue'),
        ('safety_concern', 'Safety Concern'),
        ('emergency_situation', 'Emergency Situation'),
        ('other', 'Other'),
    ]
    
    order_id = serializers.IntegerField(required=True, help_text="ID of the order to cancel")
    reason = serializers.ChoiceField(
        choices=DRIVER_CANCEL_REASONS,
        required=True,
        help_text="Cancel reason. Available options: rider_not_at_pickup, rider_asked_to_cancel, vehicle_issue, safety_concern, emergency_situation, other"
    )
    other_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Additional reason text (required if reason is 'other')"
    )
    
    def validate_order_id(self, value):
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        return value
    
    def validate(self, data):
        if data.get('reason') == 'other' and not data.get('other_reason'):
            raise serializers.ValidationError({
                'other_reason': 'Please provide a reason when selecting "other"'
            })
        return data
