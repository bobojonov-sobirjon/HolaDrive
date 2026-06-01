from rest_framework import serializers

from .services.stripe_connect_common import is_stripe_live_mode
from .services.stripe_connect_setup import (
    ConnectProfileInput,
    validate_live_connect_profile_fields,
    validate_live_identity_fields,
)


class StripeConnectProfileFieldsSerializer(serializers.Serializer):
    """US address + phone for Stripe Connect (clears Restricted requirements)."""

    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
        help_text='E.164 or US phone. Live: required if user profile has no phone_number.',
    )
    address_line1 = serializers.CharField(required=False, allow_blank=True, max_length=200)
    address_line2 = serializers.CharField(required=False, allow_blank=True, max_length=200)
    city = serializers.CharField(required=False, allow_blank=True, max_length=100)
    state = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2,
        help_text='US state code, e.g. CA',
    )
    postal_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    country = serializers.CharField(required=False, allow_blank=True, max_length=2, default='US')

    def _profile_from_attrs(self, attrs: dict) -> ConnectProfileInput:
        return ConnectProfileInput(
            phone=attrs.get('phone') or None,
            address_line1=attrs.get('address_line1') or None,
            address_line2=attrs.get('address_line2') or None,
            city=attrs.get('city') or None,
            state=attrs.get('state') or None,
            postal_code=attrs.get('postal_code') or None,
            country=attrs.get('country') or 'US',
        )

    def validate_state(self, value):
        raw = (value or '').strip().upper()
        if not raw:
            return raw
        if len(raw) != 2:
            raise serializers.ValidationError('Use 2-letter US state code (e.g. CA).')
        return raw

    def validate_country(self, value):
        raw = (value or 'US').strip().upper()
        return raw[:2] if raw else 'US'


class StripeConnectBankWriteSerializer(StripeConnectProfileFieldsSerializer):
    routing_number = serializers.CharField(max_length=9)
    account_number = serializers.CharField(max_length=34)
    account_holder_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    account_holder_type = serializers.ChoiceField(
        choices=['individual', 'company'], required=False, default='individual'
    )
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
        if not is_stripe_live_mode() and len(digits) not in (4, 9):
            raise serializers.ValidationError('SSN must be 4 or 9 digits in test mode.')
        return digits

    def validate(self, attrs):
        user = self.context.get('user')
        try:
            validate_live_identity_fields(
                dob_year=attrs.get('dob_year'),
                dob_month=attrs.get('dob_month'),
                dob_day=attrs.get('dob_day'),
                ssn_last4=attrs.get('ssn_last4') or None,
            )
            if user is not None:
                validate_live_connect_profile_fields(user, self._profile_from_attrs(attrs))
        except ValueError as exc:
            raise serializers.ValidationError({'non_field_errors': [str(exc)]}) from exc
        return attrs


class StripeConnectCompleteSetupSerializer(StripeConnectProfileFieldsSerializer):
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
        if not is_stripe_live_mode() and len(digits) not in (4, 9):
            raise serializers.ValidationError('SSN must be 4 or 9 digits in test mode.')
        return digits

    def validate(self, attrs):
        user = self.context.get('user')
        try:
            validate_live_identity_fields(
                dob_year=attrs.get('dob_year'),
                dob_month=attrs.get('dob_month'),
                dob_day=attrs.get('dob_day'),
                ssn_last4=attrs.get('ssn_last4') or None,
            )
            if user is not None:
                validate_live_connect_profile_fields(user, self._profile_from_attrs(attrs))
        except ValueError as exc:
            raise serializers.ValidationError({'non_field_errors': [str(exc)]}) from exc
        return attrs


class StripeConnectBankDeleteSerializer(serializers.Serializer):
    bank_account_id = serializers.CharField(required=False, allow_blank=True, max_length=64)
