from rest_framework import serializers


class RegistrationTermsActionSerializer(serializers.Serializer):
    """
    Body for accepting or declining registration terms configuration.
    """

    registration_type_id = serializers.IntegerField(
        min_value=1,
        help_text=(
            'Primary key of the driver identification **registration** configuration '
            '(Driver Identification Registration Type) shown in the list endpoint.'
        ),
    )

    def validate_registration_type_id(self, value):
        from ..models import DriverIdentificationRegistrationType

        try:
            obj = DriverIdentificationRegistrationType.objects.get(pk=value)
        except DriverIdentificationRegistrationType.DoesNotExist:
            raise serializers.ValidationError('Registration type not found.') from None
        if not obj.is_active:
            raise serializers.ValidationError('Registration type is not active.')
        if obj.display_type != 'registration':
            raise serializers.ValidationError('Invalid registration type configuration.')
        return value
