from rest_framework import serializers
from ..models import OrderPreferences, Order


class OrderPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderPreferences
    """
    order_id = serializers.IntegerField(write_only=True, required=True)
    chatting_preference = serializers.ChoiceField(
        choices=OrderPreferences.ChattingPreference.choices,
        help_text="Chatting preference: no_communication (No Communication), casual (Casual), friendly (Friendly)"
    )
    temperature_preference = serializers.ChoiceField(
        choices=OrderPreferences.TemperaturePreference.choices,
        help_text="Temperature preference: warm (25°C and above), comfortable (22-24°C), cool (18-21°C), cold (below 18°C)"
    )
    music_preference = serializers.ChoiceField(
        choices=OrderPreferences.MusicPreference.choices,
        help_text="Music preference: pop, rock, jazz, classical, hip_hop, electronic, country, no_music"
    )
    volume_level = serializers.ChoiceField(
        choices=OrderPreferences.VolumeLevel.choices,
        help_text="Volume level: low, medium, high, mute"
    )
    pet_preference = serializers.ChoiceField(
        choices=OrderPreferences.PetPreferences.choices,
        help_text="Pet preference: yes, no"
    )
    kids_chair_preference = serializers.ChoiceField(
        choices=OrderPreferences.KidsChairPreferences.choices,
        help_text="Kids chair preference: yes, no"
    )
    wheelchair_preference = serializers.ChoiceField(
        choices=OrderPreferences.WheelchairPreferences.choices,
        help_text="Wheelchair preference: yes, no"
    )
    gender_preference = serializers.ChoiceField(
        choices=OrderPreferences.GenderPreferences.choices,
        help_text="Gender preference: male, female, other"
    )
    favorite_driver_preference = serializers.ChoiceField(
        choices=OrderPreferences.FavoriteDriverPreferences.choices,
        help_text="Favorite driver preference: yes, no"
    )
    
    class Meta:
        model = OrderPreferences
        fields = [
            'id',
            'order_id',
            'order',
            'chatting_preference',
            'temperature_preference',
            'music_preference',
            'volume_level',
            'pet_preference',
            'kids_chair_preference',
            'wheelchair_preference',
            'gender_preference',
            'favorite_driver_preference',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'order', 'created_at', 'updated_at']
    
    def validate_order_id(self, value):
        """
        Validate that order exists and belongs to the user
        """
        user = self.context['request'].user
        try:
            order = Order.objects.get(id=value, user=user)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found or you don't have permission to access it.")
        return value
    
    def create(self, validated_data):
        """
        Create OrderPreferences
        """
        order_id = validated_data.pop('order_id')
        order = Order.objects.get(id=order_id)
        
        # Check if preferences already exist for this order
        preferences, created = OrderPreferences.objects.get_or_create(
            order=order,
            defaults=validated_data
        )
        
        if not created:
            # Update existing preferences
            for key, value in validated_data.items():
                setattr(preferences, key, value)
            preferences.save()
        
        return preferences

