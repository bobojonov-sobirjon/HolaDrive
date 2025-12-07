from rest_framework import serializers
from ..models import VehicleDetails, VehicleImages


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
    Serializer for vehicle details
    """
    images = VehicleImageSerializer(many=True, read_only=True)
    # images_data ni serializer'da validate qilmaymiz, view'da handle qilamiz
    # Multipart/form-data da multiple files to'g'ri ishlamaydi, shuning uchun view'da handle qilamiz
    
    class Meta:
        model = VehicleDetails
        fields = (
            'id', 'user', 'brand', 'model', 'year_of_manufacture', 'vin',
            'images', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
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

