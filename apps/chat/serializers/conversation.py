from rest_framework import serializers
from apps.chat.models import Conversation
from apps.chat.utils import get_support_user
from apps.accounts.serializers.user import UserDetailSerializer


class ConversationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new conversation
    Receiver is always support user (admin@admin.com)
    """
    user_type = serializers.ChoiceField(
        choices=Conversation.UserType.choices,
        help_text='Type of user: rider or driver'
    )
    
    class Meta:
        model = Conversation
        fields = ('subject', 'user_type')
        extra_kwargs = {
            'subject': {'required': False, 'allow_blank': True}
        }
    
    def create(self, validated_data):
        """
        Create conversation with current user as sender
        Receiver is always support user (admin@admin.com)
        """
        user = self.context['request'].user
        validated_data['user'] = user
        
        get_support_user()
        
        return super().create(validated_data)


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Serializer for conversation list (with summary info)
    """
    user = UserDetailSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = (
            'id', 'user', 'user_type', 'status', 'subject',
            'unread_count_support', 'unread_count_user', 'unread_count',
            'last_message_at', 'last_message', 'created_at'
        )
        read_only_fields = (
            'id', 'user', 'unread_count_support', 'unread_count_user',
            'last_message_at', 'created_at'
        )
    
    def get_last_message(self, obj):
        """
        Get last message preview
        """
        try:
            if hasattr(obj, '_prefetched_objects_cache') and 'messages' in obj._prefetched_objects_cache:
                messages = list(obj._prefetched_objects_cache['messages'])
                last_message = messages[0] if messages else None
            else:
                last_message = obj.messages.order_by('-created_at').first()
        except (AttributeError, IndexError, TypeError):
            try:
                last_message = obj.messages.order_by('-created_at').first()
            except:
                last_message = None
        
        if last_message:
            return {
                'id': last_message.id,
                'message': last_message.message[:100] + '...' if len(last_message.message) > 100 else last_message.message,
                'sender': last_message.sender.get_full_name() if last_message.sender else None,
                'is_from_support': last_message.is_from_support,
                'created_at': last_message.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        """
        Get unread count based on user type
        """
        request = self.context.get('request')
        if not request or not request.user:
            return 0
        
        if request.user.is_staff or request.user.is_superuser:
            return obj.unread_count_support
        
        return obj.unread_count_user


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for conversation detail
    """
    user = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = Conversation
        fields = (
            'id', 'user', 'user_type', 'status', 'subject',
            'unread_count_support', 'unread_count_user',
            'last_message_at', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'user', 'unread_count_support', 'unread_count_user',
            'last_message_at', 'created_at', 'updated_at'
        )

