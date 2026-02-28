from rest_framework import serializers
from ..models import LegalPage, AcceptanceOfAgreement


class LegalPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalPage
        fields = ('id', 'name', 'link', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class AcceptanceOfAgreementCreateSerializer(serializers.Serializer):
    """Serializer for POST - accept agreements by LegalPage IDs"""
    legal_agreement_data = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        help_text='List of LegalPage IDs to accept'
    )

    def validate_legal_agreement_data(self, value):
        legal_pages = LegalPage.objects.filter(id__in=value, is_active=True)
        found_ids = set(legal_pages.values_list('id', flat=True))
        invalid_ids = set(value) - found_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f'Invalid or inactive LegalPage IDs: {sorted(invalid_ids)}'
            )
        return list(found_ids)


class AcceptanceOfAgreementSerializer(serializers.ModelSerializer):
    """Serializer for response - full object with nested agreement"""
    agreement = LegalPageSerializer(read_only=True)

    class Meta:
        model = AcceptanceOfAgreement
        fields = ('id', 'user', 'agreement', 'is_accepted', 'accepted_at', 'created_at', 'updated_at')
        read_only_fields = fields
