from rest_framework import serializers

from .models import SafetyMessage, SafetyRoom, TripShareLink, TripVoiceRecording


class TripShareCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()


class TripShareLinkSerializer(serializers.ModelSerializer):
    share_url = serializers.CharField(read_only=True)
    deep_link = serializers.CharField(read_only=True)
    public_api_url = serializers.CharField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_code = serializers.SerializerMethodField()
    order_status = serializers.CharField(source='order.status', read_only=True)

    class Meta:
        model = TripShareLink
        fields = (
            'id',
            'token',
            'share_url',
            'deep_link',
            'public_api_url',
            'order_id',
            'order_code',
            'order_status',
            'expires_at',
            'is_active',
            'is_valid',
            'revoked_at',
            'created_at',
        )

    def get_order_code(self, obj):
        return getattr(obj.order, 'order_code', None)


class SafetyRoomOpenSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=False, allow_null=True)


class SafetyMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000)
    order_id = serializers.IntegerField(required=False, allow_null=True)


class SafetyMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True, allow_null=True)
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = SafetyMessage
        fields = (
            'id',
            'room_id',
            'sender_id',
            'sender_name',
            'message_type',
            'message',
            'order_id',
            'created_at',
        )

    def get_sender_name(self, obj):
        if not obj.sender_id:
            return None
        return obj.sender.get_full_name() or obj.sender.email


class SafetyRoomSerializer(serializers.ModelSerializer):
    order_ids = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    agent_id = serializers.IntegerField(source='agent.id', read_only=True)

    class Meta:
        model = SafetyRoom
        fields = (
            'id',
            'user_id',
            'agent_id',
            'order_ids',
            'messages',
            'created_at',
            'updated_at',
        )

    def get_order_ids(self, obj):
        return list(obj.orders.values_list('id', flat=True))

    def get_messages(self, obj):
        qs = obj.messages.select_related('sender').order_by('-created_at')[:30]
        # newest first slice then reverse for chronological
        msgs = list(reversed(list(qs)))
        return SafetyMessageSerializer(msgs, many=True).data


class VoiceRecordingStartSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()


class VoiceRecordingStopSerializer(serializers.Serializer):
    duration_seconds = serializers.IntegerField(required=False, allow_null=True)
    # audio file via request.FILES['audio']


class TripVoiceRecordingSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = TripVoiceRecording
        fields = (
            'id',
            'order_id',
            'user_id',
            'status',
            'audio_url',
            'started_at',
            'ended_at',
            'duration_seconds',
            'created_at',
        )

    def get_audio_url(self, obj):
        if not obj.audio_file:
            return None
        request = self.context.get('request')
        try:
            url = obj.audio_file.url
        except Exception:
            return None
        if request:
            return request.build_absolute_uri(url)
        return url
