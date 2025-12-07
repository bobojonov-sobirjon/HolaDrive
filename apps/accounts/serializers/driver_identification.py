from rest_framework import serializers
from ..models import DriverIdentification


class DriverIdentificationSerializer(serializers.ModelSerializer):
    """
    Serializer for driver identification documents
    """
    class Meta:
        model = DriverIdentification
        fields = (
            'id', 'user', 
            'proof_of_work_eligibility',
            'profile_photo',
            'drivers_license',
            'background_check',
            'driver_abstract',
            'livery_vehicle_registration',
            'vehicle_insurance',
            'city_tndl',
            'elvis_vehicle_inspection',
            'terms_and_conditions', 'legal_agreements',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def _get_image_url(self, image_field):
        """
        Return full URL for the image field
        """
        if image_field:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image_field.url)
            return image_field.url
        return None
    
    def create(self, validated_data):
        """
        Create identification for the authenticated user
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return DriverIdentification.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        """
        Update identification documents
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

