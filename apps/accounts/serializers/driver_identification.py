from rest_framework import serializers

from apps.accounts.models import DriverIdentificationLegalType, DriverIdentificationTermsType


class IdentificationUploadSubmitSerializer(serializers.Serializer):
    """
    multipart/form-data for driver identification file upload (Swagger UI form).
    """

    upload_type_id = serializers.IntegerField(
        min_value=1,
        help_text='ID of the upload identification step (DriverIdentificationUploadType).',
    )
    file = serializers.FileField(
        help_text='File to upload (image or document).',
    )


class IdentificationLegalTypeActionSerializer(serializers.Serializer):
    """Body for legal agreements accept/decline (same shape as registration terms)."""

    legal_type_id = serializers.IntegerField(
        min_value=1,
        help_text='Primary key of an active **legal** driver identification configuration.',
    )

    def validate_legal_type_id(self, value):
        try:
            obj = DriverIdentificationLegalType.objects.get(pk=value)
        except DriverIdentificationLegalType.DoesNotExist:
            raise serializers.ValidationError('Legal identification type not found.') from None
        if not obj.is_active:
            raise serializers.ValidationError('Legal identification type is not active.')
        if obj.display_type != 'legal':
            raise serializers.ValidationError('Invalid legal identification configuration.')
        return value


class IdentificationTermsTypeActionSerializer(serializers.Serializer):
    """Body for terms accept/decline (per agreement item under the hood)."""

    terms_type_id = serializers.IntegerField(
        min_value=1,
        help_text='Primary key of an active **terms** driver identification configuration.',
    )

    def validate_terms_type_id(self, value):
        try:
            obj = DriverIdentificationTermsType.objects.get(pk=value)
        except DriverIdentificationTermsType.DoesNotExist:
            raise serializers.ValidationError('Terms identification type not found.') from None
        if not obj.is_active:
            raise serializers.ValidationError('Terms identification type is not active.')
        if obj.display_type != 'terms':
            raise serializers.ValidationError('Invalid terms identification configuration.')
        return value
