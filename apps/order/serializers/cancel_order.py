from rest_framework import serializers
from ..models import CancelOrder, Order


class OrderCancelSerializer(serializers.Serializer):
    """
    Serializer for canceling an order
    
    Available cancel reasons (reason field):
    - change_in_plans: Change in Plans
    - waiting_for_long_time: Waiting for Long Time
    - driver_denied_to_go_to_destination: Driver Denied to Go to Destination
    - driver_denied_to_come_to_pickup: Driver Denied to Come to Pickup
    - wrong_address_shown: Wrong Address Shown
    - the_price_is_not_reasonable: The Price is Not Reasonable
    - emergency_situation: Emergency Situation
    - other: Other (requires other_reason field)
    """
    reason = serializers.ChoiceField(
        choices=CancelOrder.CancelReason.choices,
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
        """
        Validate that other_reason is provided if reason is 'other'
        """
        if data.get('reason') == CancelOrder.CancelReason.OTHER and not data.get('other_reason'):
            raise serializers.ValidationError({
                'other_reason': 'Please provide a reason when selecting "other"'
            })
        return data

