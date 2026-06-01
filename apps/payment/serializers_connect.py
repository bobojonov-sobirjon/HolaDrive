from rest_framework import serializers

from .services.stripe_connect_common import is_stripe_live_mode
from .services.stripe_connect_setup import validate_live_identity_fields


class StripeConnectBankWriteSerializer(serializers.Serializer):
    routing_number = serializers.CharField(max_length=9, help_text='US bank routing number (9 digits, ACH).')
    account_number = serializers.CharField(max_length=34, help_text='US bank account number (4–17 digits).')
    account_holder_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=120,
        help_text='Defaults to logged-in user full name.',
    )
    account_holder_type = serializers.ChoiceField(
        choices=['individual', 'company'],
        required=False,
        default='individual',
    )
    accept_agreement = serializers.BooleanField(
        help_text='Must be true — Stripe Connected Account Agreement.',
    )
    dob_year = serializers.IntegerField(
        required=False,
        min_value=1900,
        max_value=2100,
        help_text='Live mode: required. Test mode: server default if omitted.',
    )
    dob_month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    dob_day = serializers.IntegerField(required=False, min_value=1, max_value=31)
    ssn_last4 = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=11,
        help_text='Live: full 9-digit US SSN. Test: optional (server uses test default). Not stored in DB.',
    )

    def validate_ssn_last4(self, value):
        raw = (value or '').strip()
        if not raw:
            return raw
        digits = raw.replace('-', '')
        if not digits.isdigit():
            raise serializers.ValidationError('SSN must contain digits only.')
        if is_stripe_live_mode() and len(digits) != 9:
            raise serializers.ValidationError('US SSN must be 9 digits in live mode.')
        if not is_stripe_live_mode() and len(digits) not in (4, 9):
            raise serializers.ValidationError('SSN must be 4 or 9 digits in test mode.')
        return digits

    def validate(self, attrs):
        try:
            validate_live_identity_fields(
                dob_year=attrs.get('dob_year'),
                dob_month=attrs.get('dob_month'),
                dob_day=attrs.get('dob_day'),
                ssn_last4=attrs.get('ssn_last4') or None,
            )
        except ValueError as exc:
            raise serializers.ValidationError({'non_field_errors': [str(exc)]}) from exc
        return attrs


class StripeConnectCompleteSetupSerializer(serializers.Serializer):
    """Bank already linked — send agreement + identity to Stripe (not stored in DB)."""

    accept_agreement = serializers.BooleanField()
    dob_year = serializers.IntegerField(required=False, min_value=1900, max_value=2100)
    dob_month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    dob_day = serializers.IntegerField(required=False, min_value=1, max_value=31)
    ssn_last4 = serializers.CharField(required=False, allow_blank=True, max_length=11)

    def validate_ssn_last4(self, value):
        raw = (value or '').strip()
        if not raw:
            return raw
        digits = raw.replace('-', '')
        if not digits.isdigit():
            raise serializers.ValidationError('SSN must contain digits only.')
        if is_stripe_live_mode() and len(digits) != 9:
            raise serializers.ValidationError('US SSN must be 9 digits in live mode.')
        return digits

    def validate(self, attrs):
        try:
            validate_live_identity_fields(
                dob_year=attrs.get('dob_year'),
                dob_month=attrs.get('dob_month'),
                dob_day=attrs.get('dob_day'),
                ssn_last4=attrs.get('ssn_last4') or None,
            )
        except ValueError as exc:
            raise serializers.ValidationError({'non_field_errors': [str(exc)]}) from exc
        return attrs


class StripeConnectBankDeleteSerializer(serializers.Serializer):
    bank_account_id = serializers.CharField(required=False, allow_blank=True, max_length=64)
