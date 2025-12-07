from rest_framework import serializers
from ..models import OrderSchedule, Order


class OrderScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderSchedule
    """
    order_id = serializers.IntegerField(write_only=True, required=True)
    schedule_type = serializers.ChoiceField(
        choices=OrderSchedule.ScheduleType.choices,
        help_text="Schedule type: pickup_at (Pickup At), drop_off_by (Drop Off By)"
    )
    schedule_time_type = serializers.ChoiceField(
        choices=OrderSchedule.ScheduleTime.choices,
        help_text="Schedule time type: today (Today), tomorrow (Tomorrow), select_date (Select Date)"
    )
    
    class Meta:
        model = OrderSchedule
        fields = [
            'id',
            'order_id',
            'order',
            'schedule_type',
            'schedule_date',
            'schedule_time',
            'schedule_time_type',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'order', 'created_at', 'updated_at']
    
    def validate_order_id(self, value):
        """
        Validate that order exists and belongs to the user
        """
        user = self.context['request'].user
        try:
            # Optimize query: use select_related to avoid N+1 queries
            order = Order.objects.select_related('user').get(id=value, user=user)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found or you don't have permission to access it.")
        return value
    
    def create(self, validated_data):
        """
        Create OrderSchedule
        """
        order_id = validated_data.pop('order_id')
        # Optimize query: use select_related to avoid N+1 queries
        order = Order.objects.select_related('user').get(id=order_id)
        
        schedule = OrderSchedule.objects.create(
            order=order,
            **validated_data
        )
        
        return schedule

