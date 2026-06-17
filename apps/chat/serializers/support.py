from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers.user import UserDetailSerializer
from apps.chat.models import SupportRoom, SupportMessage


class SupportRoomOpenSerializer(serializers.Serializer):
    """
    Open (or reuse) support room. If order_id is provided, it will be linked to the room,
    and a system message will be created to indicate context switching.
    """

    order_id = serializers.IntegerField(required=False, allow_null=True)


class SupportRoomSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    admin = UserDetailSerializer(read_only=True)
    order_ids = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()

    class Meta:
        model = SupportRoom
        fields = ('id', 'user', 'admin', 'order_ids', 'messages', 'created_at', 'updated_at')
        read_only_fields = fields

    def get_order_ids(self, obj):
        try:
            return list(obj.orders.values_list('id', flat=True).order_by('id'))
        except Exception:
            return []

    def get_messages(self, obj):
        """
        Optional inline messages list for room detail screens.
        Enabled only when serializer context includes `include_messages=True`.
        """
        if not self.context.get('include_messages'):
            return None
        limit = int(self.context.get('messages_limit') or 200)
        qs = (
            SupportMessage.objects.filter(room=obj)
            .select_related('sender')
            .order_by('created_at')
        )
        rows = list(qs[:limit])
        ser = SupportMessageSerializer(rows, many=True, context=self.context)
        return ser.data


class SupportMessageSerializer(serializers.ModelSerializer):
    sender = UserDetailSerializer(read_only=True)
    sender_type = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ('id', 'room', 'sender', 'sender_type', 'message_type', 'message', 'order', 'created_at')
        read_only_fields = fields

    def get_sender_type(self, obj):
        """
        For frontend alignment:
          - initiator: request.user (who is viewing)
          - receiver: the other party
          - system: system message
        """
        if getattr(obj, 'message_type', None) == SupportMessage.MessageType.SYSTEM:
            return 'system'
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return 'receiver'
        return 'initiator' if obj.sender_id == request.user.id else 'receiver'


class SupportMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    order_id = serializers.IntegerField(required=False, allow_null=True)

