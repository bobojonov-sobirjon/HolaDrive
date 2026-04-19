from rest_framework import serializers


class OrderPinVerifySerializer(serializers.Serializer):
    """Body: order_id + 4-digit PIN (driver or rider verification)."""

    order_id = serializers.IntegerField(min_value=1)
    pin = serializers.CharField(min_length=4, max_length=4)

    def validate_pin(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError('PIN must contain only digits.')
        if len(value) != 4:
            raise serializers.ValidationError('PIN must be exactly 4 digits.')
        return value
