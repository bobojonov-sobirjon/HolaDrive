from rest_framework import serializers
from ..models import PinVerificationForUser
from .user import UserDetailSerializer


class PinVerificationForUserSerializer(serializers.ModelSerializer):
    """
    Serializer for PIN verification
    """
    user = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = PinVerificationForUser
        fields = ('id', 'user', 'pin', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
        extra_kwargs = {
            'pin': {
                'required': True,
                'min_length': 4,
                'max_length': 4,
                'help_text': '4-digit PIN code'
            }
        }
    
    def validate_pin(self, value):
        """
        Validate that PIN is exactly 4 digits
        """
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits.")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits.")
        return value
    
    def create(self, validated_data):
        """
        Create PIN for the authenticated user
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return PinVerificationForUser.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        """
        Update PIN for the authenticated user
        """
        instance.pin = validated_data.get('pin', instance.pin)
        instance.save()
        return instance

