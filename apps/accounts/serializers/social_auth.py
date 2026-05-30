from rest_framework import serializers

from apps.accounts.models import UserDeviceToken


class FirebaseSocialSignInSerializer(serializers.Serializer):
    """
    Mobile app signs in with Firebase Auth (Google / Apple / Facebook), then sends the ID token here.
  """

    id_token = serializers.CharField(
        required=True,
        help_text='Firebase Auth ID token from the mobile SDK after social sign-in.',
    )
    role = serializers.ChoiceField(
        choices=[('rider', 'Rider'), ('driver', 'Driver')],
        required=False,
        allow_blank=True,
        help_text='Assign app role on first sign-up only (Rider or Driver group).',
    )
    full_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text='Optional display name (used when creating a new account).',
    )
    device_token = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.ChoiceField(
        required=False,
        choices=UserDeviceToken.DeviceType.choices,
    )

    def validate_id_token(self, value):
        token = (value or '').strip()
        if len(token) < 20:
            raise serializers.ValidationError('Invalid Firebase ID token.')
        return token
