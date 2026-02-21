from rest_framework import serializers
from ..models import (
    DriverIdentification,
    DriverIdentificationItems,
    DriverIdentificationFAQ,
    DriverIdentificationUploadDocument,
    DriverVerification,
    DriverAgreement,
)



class DriverIdentificationItemsSerializer(serializers.ModelSerializer):
    """
    Serializer for driver identification items
    """
    class Meta:
        model = DriverIdentificationItems
        fields = ('id', 'item', 'created_at')
        read_only_fields = ('id', 'created_at')


class DriverIdentificationFAQSerializer(serializers.ModelSerializer):
    """
    Serializer for driver identification FAQ (question, link, file).
    """
    class Meta:
        model = DriverIdentificationFAQ
        fields = ('id', 'question', 'link', 'file', 'order', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            if instance.file:
                representation['file'] = request.build_absolute_uri(instance.file.url)
            else:
                representation['file'] = None
        return representation


class DriverIdentificationSerializer(serializers.ModelSerializer):
    """
    Serializer for driver identification types.
    identification_faq: alohida data, har bir identification uchun FAQ ro'yxati.
    """
    items = DriverIdentificationItemsSerializer(many=True, read_only=True)
    identification_faq = serializers.SerializerMethodField()
    display_type_display = serializers.CharField(source='get_display_type_display', read_only=True)

    class Meta:
        model = DriverIdentification
        fields = (
            'id', 'name', 'display_type', 'display_type_display', 'image', 'title', 'description',
            'is_active', 'items', 'identification_faq', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_identification_faq(self, instance):
        faqs = instance.identification_faq.all()
        serializer = DriverIdentificationFAQSerializer(
            faqs,
            many=True,
            context=self.context
        )
        return serializer.data

    def to_representation(self, instance):
        """
        Override to include full URL for image field
        """
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.image:
            representation['image'] = request.build_absolute_uri(instance.image.url)
        return representation


class DriverIdentificationUploadRequestSerializer(serializers.Serializer):
    """Request body for upload document (multipart/form-data). Shown in Swagger."""
    document_file = serializers.FileField(required=True, help_text='Document file to upload')
    driver_identification_id = serializers.IntegerField(required=True, help_text='Driver identification type ID')


class DriverIdentificationUploadDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for driver identification upload documents
    """
    driver_identification_name = serializers.CharField(
        source='driver_identification.name',
        read_only=True
    )
    driver_identification_title = serializers.CharField(
        source='driver_identification.title',
        read_only=True
    )
    driver_identification_display_type = serializers.CharField(
        source='driver_identification.display_type',
        read_only=True
    )
    driver_identification_display_type_display = serializers.CharField(
        source='driver_identification.get_display_type_display',
        read_only=True
    )
    document_file = serializers.FileField(required=True)
    
    class Meta:
        model = DriverIdentificationUploadDocument
        fields = (
            'id', 'user', 'driver_identification', 'driver_identification_name',
            'driver_identification_title', 'driver_identification_display_type',
            'driver_identification_display_type_display', 'document_file', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def to_representation(self, instance):
        """
        Override to include full URL for document_file
        """
        representation = super().to_representation(instance)
        if instance.document_file:
            request = self.context.get('request')
            if request:
                representation['document_file'] = request.build_absolute_uri(instance.document_file.url)
        return representation
    
    def create(self, validated_data):
        """
        Create upload document for the authenticated user
        """
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Check if upload already exists, if yes, update it
        driver_identification = validated_data['driver_identification']
        document_file = validated_data['document_file']
        
        try:
            upload = DriverIdentificationUploadDocument.objects.get(
                user=user,
                driver_identification=driver_identification
            )
            upload.document_file = document_file
            upload.save()
            return upload
        except DriverIdentificationUploadDocument.DoesNotExist:
            return DriverIdentificationUploadDocument.objects.create(
                user=user,
                driver_identification=driver_identification,
                document_file=document_file
            )


class DriverIdentificationUserStatusSerializer(serializers.Serializer):
    """
    Serializer for user's identification status
    """
    driver_identification_id = serializers.IntegerField()
    driver_identification_name = serializers.CharField()
    driver_identification_title = serializers.CharField()
    driver_identification_display_type = serializers.CharField()
    driver_identification_display_type_display = serializers.CharField()
    driver_identification_upload_id = serializers.IntegerField(allow_null=True)
    is_upload_user = serializers.BooleanField()
    document_file = serializers.CharField(allow_null=True, allow_blank=True)


class DriverVerificationSerializer(serializers.ModelSerializer):
    """
    Serializer for driver verification status
    """

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DriverVerification
        fields = (
            'id',
            'status',
            'status_display',
            'estimated_review_hours',
            'comment',
            'reviewer',
            'reviewed_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class DriverAgreementSerializer(serializers.ModelSerializer):
    """
    Serializer for driver agreements
    """
    class Meta:
        model = DriverAgreement
        fields = ('id', 'name', 'file', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')