from rest_framework import serializers
from ..models import OrderChat, OrderChatMessage, Order


class OrderChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    attachment_url = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderChatMessage
        fields = [
            'id',
            'sender',
            'sender_name',
            'sender_type',
            'message',
            'is_read',
            'attachment_url',
            'file_type',
            'file_name',
            'created_at',
        ]
        read_only_fields = ['id', 'sender', 'sender_name', 'sender_type', 'is_read', 'created_at']
    
    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None


class OrderChatSerializer(serializers.ModelSerializer):
    order_code = serializers.CharField(source='order.order_code', read_only=True)
    rider_name = serializers.CharField(source='rider.get_full_name', read_only=True)
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderChat
        fields = [
            'id',
            'order',
            'order_code',
            'rider',
            'rider_name',
            'driver',
            'driver_name',
            'status',
            'last_message_at',
            'unread_count_rider',
            'unread_count_driver',
            'last_message',
            'created_at',
        ]
        read_only_fields = ['id', 'order', 'rider', 'driver', 'created_at']
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'message': last_msg.message[:50] + '...' if len(last_msg.message) > 50 else last_msg.message,
                'sender_type': last_msg.sender_type,
                'created_at': last_msg.created_at.isoformat(),
            }
        return None


class OrderChatSendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    
    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()
