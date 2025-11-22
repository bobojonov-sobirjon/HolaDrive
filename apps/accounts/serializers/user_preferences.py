from rest_framework import serializers
from ..models import UserPreferences


class UserPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for user preferences
    """
    
    class Meta:
        model = UserPreferences
        fields = (
            'id', 'user', 'chatting_preference', 'temperature_preference',
            'music_preference', 'volume_level', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        """
        Create preferences for the authenticated user.
        If preferences already exist for this user, update them instead of creating new ones.
        This ensures only one preferences entry exists per user.
        """
        user = self.context['request'].user
        
        try:
            preferences = UserPreferences.objects.get(user=user)
            for key, value in validated_data.items():
                setattr(preferences, key, value)
            preferences.save()
            return preferences
        except UserPreferences.DoesNotExist:
            validated_data['user'] = user
            return UserPreferences.objects.create(**validated_data)

