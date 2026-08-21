from rest_framework import serializers
from ..models import PinVerificationForUser


class PinVerificationForUserSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True, min_length=4, max_length=4, help_text='4-digit PIN')
    has_pin = serializers.SerializerMethodField()

    class Meta:
        model = PinVerificationForUser
        fields = ('id', 'pin', 'has_pin', 'created_at', 'updated_at')
        read_only_fields = ('id', 'has_pin', 'created_at', 'updated_at')

    def get_has_pin(self, obj):
        return bool(obj and obj.pin)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must contain only digits.')
        if len(value) != 4:
            raise serializers.ValidationError('PIN must be exactly 4 digits.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        raw = validated_data.pop('pin')
        obj = PinVerificationForUser(user=user)
        obj.set_pin(raw)
        obj.save()
        return obj

    def update(self, instance, validated_data):
        raw = validated_data.get('pin')
        if raw:
            instance.set_pin(raw)
            instance.save(update_fields=['pin', 'updated_at'])
        return instance
