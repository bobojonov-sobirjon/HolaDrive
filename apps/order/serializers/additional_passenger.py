from rest_framework import serializers
from ..models import AdditionalPassenger, Order


class AdditionalPassengerSerializer(serializers.ModelSerializer):
    """
    Serializer for AdditionalPassenger
    """
    order_id = serializers.IntegerField(write_only=True, required=True)
    
    class Meta:
        model = AdditionalPassenger
        fields = [
            'id',
            'order_id',
            'order',
            'full_name',
            'phone_number',
            'email',
            'created_at'
        ]
        read_only_fields = ['id', 'order', 'created_at']
    
    def validate_order_id(self, value):
        """
        Validate that order exists and belongs to the user
        """
        user = self.context['request'].user
        try:
            order = Order.objects.get(id=value, user=user)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found or you don't have permission to access it.")
        return value
    
    def create(self, validated_data):
        """
        Create AdditionalPassenger
        """
        order_id = validated_data.pop('order_id')
        order = Order.objects.get(id=order_id)
        
        passenger = AdditionalPassenger.objects.create(
            order=order,
            **validated_data
        )
        
        return passenger

