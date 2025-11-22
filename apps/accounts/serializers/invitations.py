from rest_framework import serializers
from ..models import InvitationGenerate, InvitationUsers
from .user import UserDetailSerializer


class InvitationGenerateSerializer(serializers.ModelSerializer):
    """
    Serializer for invitation code generation
    """
    user = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = InvitationGenerate
        fields = ('id', 'user', 'invite_code',)
        read_only_fields = ('id', 'invite_code', 'created_at')


class InvitationUsersSerializer(serializers.ModelSerializer):
    """
    Serializer for invitation users
    """
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    sender_name = serializers.SerializerMethodField()
    receiver_email = serializers.EmailField(source='receiver.email', read_only=True, allow_null=True)
    receiver_name = serializers.SerializerMethodField()
    
    class Meta:
        model = InvitationUsers
        fields = ('id', 'sender', 'sender_email', 'sender_name', 'receiver', 'receiver_email', 'receiver_name', 'is_active', 'created_at')
        read_only_fields = ('id', 'sender', 'receiver', 'is_active', 'created_at')
    
    def get_sender_name(self, obj):
        return obj.sender.get_full_name()
    
    def get_receiver_name(self, obj):
        if obj.receiver:
            return obj.receiver.get_full_name()
        return None

