from rest_framework import serializers
from ..models import VehicleDetails, VehicleImages


def get_ride_type_queryset():
    """Get queryset for active ride types"""
    try:
        from apps.order.models import RideType
        return RideType.objects.filter(is_active=True)
    except ImportError:
        return None


class VehicleImageSerializer(serializers.ModelSerializer):
    """
    Serializer for vehicle images
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleImages
        fields = ('id', 'image', 'image_url', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def get_image_url(self, obj):
        """
        Return full URL for the image
        """
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class VehicleDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for vehicle details with ride type support
    """
    images = VehicleImageSerializer(many=True, read_only=True)
    images_data = serializers.ListField(
        child=serializers.ImageField(allow_null=True),
        required=False,
        write_only=True,
        help_text='Optional list of images (multipart/form-data)',
    )
    supported_ride_types = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=get_ride_type_queryset(),
        required=False,
        allow_empty=True
    )
    supported_ride_types_names = serializers.SerializerMethodField()
    default_ride_type_name = serializers.CharField(
        source='default_ride_type.name',
        read_only=True,
        allow_null=True
    )
    default_ride_type_id = serializers.IntegerField(
        source='default_ride_type.id',
        read_only=True,
        allow_null=True
    )
    suggested_ride_types = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleDetails
        fields = (
            'id', 'user', 'brand', 'model', 'year_of_manufacture', 'vin',
            'vehicle_condition',
            'default_ride_type', 'default_ride_type_name', 'default_ride_type_id',
            'supported_ride_types', 'supported_ride_types_names',
            'suggested_ride_types',
            'images', 'images_data', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at', 'suggested_ride_types')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update queryset for supported_ride_types to only active ride types
        queryset = get_ride_type_queryset()
        if queryset is not None:
            self.fields['supported_ride_types'].queryset = queryset
    
    def get_supported_ride_types_names(self, obj):
        """Return names of supported ride types"""
        if obj.pk:
            return [rt.name or rt.name_large or 'Unknown' for rt in obj.supported_ride_types.all()]
        return []
    
    def get_suggested_ride_types(self, obj):
        """
        Return automatically suggested ride types based on vehicle characteristics.
        This is read-only and shown for reference.
        """
        if not obj.pk:
            # For new vehicles, calculate suggestions based on current data
            # Create a temporary instance to use suggest_ride_types method
            temp_vehicle = VehicleDetails(
                brand=obj.brand if hasattr(obj, 'brand') else '',
                model=obj.model if hasattr(obj, 'model') else '',
                year_of_manufacture=obj.year_of_manufacture if hasattr(obj, 'year_of_manufacture') else 2020,
                vehicle_condition=obj.vehicle_condition if hasattr(obj, 'vehicle_condition') else VehicleDetails.VehicleCondition.GOOD
            )
            suggestions = temp_vehicle.suggest_ride_types()
        else:
            suggestions = obj.suggest_ride_types()
        
        return [
            {
                'id': rt.id,
                'name': rt.name or rt.name_large or 'Unknown',
                'reason': self._get_suggestion_reason(obj, rt)
            }
            for rt in suggestions
        ]
    
    def _get_suggestion_reason(self, vehicle, ride_type):
        """Explain why this ride type was suggested"""
        if ride_type.is_ev and vehicle.is_electric_vehicle():
            return "Electric vehicle detected"
        if ride_type.is_premium:
            if vehicle.year_of_manufacture >= 2020:
                return "Recent model (2020+) with excellent condition"
            return "Premium brand vehicle"
        return "Standard vehicle category"
    
    def validate_year_of_manufacture(self, value):
        """
        Validate that year is 2015 or newer
        """
        if value < 2015:
            raise serializers.ValidationError("Year of manufacture must be 2015 or newer.")
        return value
    
    def validate_vin(self, value):
        """
        Validate VIN format (should be 8-17 characters, standard is 17)
        """
        if not value or len(value) < 8 or len(value) > 17:
            raise serializers.ValidationError("VIN must be between 8 and 17 characters.")
        return value.upper()
    
    def create(self, validated_data):
        """
        Create vehicle details with images
        """
        # images_data ni validated_data dan olib tashlaymiz (view'da handle qilingan)
        images_data = validated_data.pop('images_data', [])
        user = self.context['request'].user
        validated_data['user'] = user
        
        vehicle = VehicleDetails.objects.create(**validated_data)
        
        # Create vehicle images
        if images_data:
            for image in images_data:
                if image:  # None yoki bo'sh bo'lmasligini tekshiramiz
                    VehicleImages.objects.create(vehicle=vehicle, image=image)
        
        return vehicle
    
    def update(self, instance, validated_data):
        """
        Update vehicle details and handle images
        """
        images_data = validated_data.pop('images_data', None)
        
        # Update vehicle fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # If new images are provided, add them (don't delete existing ones)
        if images_data is not None:
            for image in images_data:
                if image:  # None yoki bo'sh bo'lmasligini tekshiramiz
                    VehicleImages.objects.create(vehicle=instance, image=image)
        
        return instance

