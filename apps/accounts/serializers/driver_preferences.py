from rest_framework import serializers
from ..models import DriverPreferences

# Mobile app may send legacy labels; backend stores canonical choice values.
_TRIP_TYPE_ALIASES = {
    'any_distance': DriverPreferences.TripTypePreference.ANY,
    'any_trip_length': DriverPreferences.TripTypePreference.ANY,
    'any_trip': DriverPreferences.TripTypePreference.ANY,
}
_WORKING_HOURS_ALIASES = {
    'any_time': DriverPreferences.PreferredWorkingHours.ANY,
    'anytime': DriverPreferences.PreferredWorkingHours.ANY,
}


class DriverPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for driver preferences
    """
    
    class Meta:
        model = DriverPreferences
        fields = (
            'id', 'user', 'trip_type_preference', 'maximum_pickup_distance',
            'preferred_working_hours', 'notification_intensity', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def validate_trip_type_preference(self, value):
        raw = (value or '').strip().lower()
        return _TRIP_TYPE_ALIASES.get(raw, value)

    def validate_preferred_working_hours(self, value):
        raw = (value or '').strip().lower()
        return _WORKING_HOURS_ALIASES.get(raw, value)

    def create(self, validated_data):
        """
        Create preferences for the authenticated user.
        If preferences already exist for this user, update them instead of creating new ones.
        This ensures only one preferences entry exists per user.
        """
        user = self.context['request'].user
        
        try:
            preferences = DriverPreferences.objects.get(user=user)
            for key, value in validated_data.items():
                setattr(preferences, key, value)
            preferences.save()
            return preferences
        except DriverPreferences.DoesNotExist:
            validated_data['user'] = user
            return DriverPreferences.objects.create(**validated_data)

