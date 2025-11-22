from rest_framework import serializers
from apps.chat.models import Message
from apps.accounts.serializers.user import UserDetailSerializer


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for message detail
    """
    sender = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = (
            'id', 'conversation', 'sender', 'message', 'attachment',
            'is_read_by_support', 'is_read_by_user', 'is_from_support',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'sender', 'is_read_by_support', 'is_read_by_user',
            'is_from_support', 'created_at', 'updated_at'
        )
    
    def to_representation(self, instance):
        """
        Return attachment as full URL
        """
        representation = super().to_representation(instance)
        if instance.attachment:
            request = self.context.get('request')
            if request:
                representation['attachment'] = request.build_absolute_uri(instance.attachment.url)
            else:
                representation['attachment'] = instance.attachment.url
        else:
            representation['attachment'] = None
        return representation


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new message
    """
    class Meta:
        model = Message
        fields = ('conversation', 'message', 'attachment')
        extra_kwargs = {
            'conversation': {'required': True},
            'message': {'required': True},
            'attachment': {'required': False, 'allow_null': True}
        }
    
    def validate_conversation(self, value):
        """
        Validate that user has access to this conversation
        """
        request = self.context['request']
        user = request.user
        
        if value.user != user:
            if not (user.is_staff or user.is_superuser):
                raise serializers.ValidationError("You don't have access to this conversation.")
        
        return value
    
    def create(self, validated_data):
        """
        Create message with current user as sender
        """
        request = self.context['request']
        user = request.user
        
        is_from_support = user.is_staff or user.is_superuser
        
        if is_from_support:
            raise serializers.ValidationError(
                "Support can only send messages from admin panel. Please use admin panel to reply."
            )
        
        validated_data['sender'] = user
        validated_data['is_from_support'] = is_from_support
        validated_data['is_read_by_support'] = is_from_support
        validated_data['is_read_by_user'] = not is_from_support
        
        return super().create(validated_data)

