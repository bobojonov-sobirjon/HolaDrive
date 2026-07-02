from rest_framework import serializers

from apps.voice_call.models import CallRecording, SupportAgentDuty, VoiceCallSession


class TripCallInitiateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()


class SupportCallInitiateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=False, allow_null=True)


class CallActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class SupportDutySerializer(serializers.Serializer):
    is_on_duty = serializers.BooleanField()


class CallRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRecording
        fields = (
            'recording_url',
            'recording_status',
            'transcript_text',
            'transcript_status',
            'created_at',
            'updated_at',
        )


class VoiceCallUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class VoiceCallSessionSerializer(serializers.ModelSerializer):
    caller = serializers.SerializerMethodField()
    callee = serializers.SerializerMethodField()
    recording = CallRecordingSerializer(read_only=True, allow_null=True)
    order_code = serializers.SerializerMethodField()
    agora = serializers.SerializerMethodField()

    class Meta:
        model = VoiceCallSession
        fields = (
            'id',
            'call_type',
            'status',
            'order_id',
            'order_code',
            'support_room_id',
            'initiator_role',
            'agora_channel_name',
            'agora_app_id',
            'ring_started_at',
            'answered_at',
            'ended_at',
            'duration_seconds',
            'end_reason',
            'operator_note',
            'caller',
            'callee',
            'recording',
            'agora',
            'created_at',
            'updated_at',
        )

    def get_order_code(self, obj):
        return getattr(obj.order, 'order_code', None)

    def get_caller(self, obj):
        u = obj.caller
        return {'id': u.id, 'full_name': u.get_full_name(), 'email': u.email}

    def get_callee(self, obj):
        if not obj.callee_id:
            return None
        u = obj.callee
        return {'id': u.id, 'full_name': u.get_full_name(), 'email': u.email}

    def get_agora(self, obj):
        return self.context.get('agora')


class VoiceCallSessionListSerializer(VoiceCallSessionSerializer):
    class Meta(VoiceCallSessionSerializer.Meta):
        fields = (
            'id',
            'call_type',
            'status',
            'order_id',
            'order_code',
            'support_room_id',
            'initiator_role',
            'ring_started_at',
            'answered_at',
            'ended_at',
            'duration_seconds',
            'caller',
            'callee',
            'created_at',
        )


class SupportAgentDutySerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source='admin.email', read_only=True)

    class Meta:
        model = SupportAgentDuty
        fields = ('admin_id', 'admin_email', 'is_on_duty', 'updated_at')
        read_only_fields = fields
