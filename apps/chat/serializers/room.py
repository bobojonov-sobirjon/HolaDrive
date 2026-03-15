from rest_framework import serializers
from apps.chat.models import ChatRoom, ChatMessage
from apps.accounts.serializers.user import UserDetailSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserDetailSerializer(read_only=True)
    sender_type = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ('id', 'room', 'sender', 'sender_type', 'message', 'created_at')
        read_only_fields = ('id', 'sender', 'created_at')

    def get_sender_type(self, obj):
        """Initiator = request.user (who is viewing), receiver = the other party. For frontend styling."""
        request = self.context.get('request')
        if not request or not request.user:
            return 'receiver'
        return 'initiator' if obj.sender_id == request.user.id else 'receiver'


class ChatRoomSerializer(serializers.ModelSerializer):
    initiator = UserDetailSerializer(read_only=True)
    receiver = UserDetailSerializer(read_only=True)

    class Meta:
        model = ChatRoom
        fields = ('id', 'order', 'initiator', 'receiver', 'status', 'created_at', 'updated_at')
        read_only_fields = fields
