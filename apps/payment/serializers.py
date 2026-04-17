from rest_framework import serializers

from .models import SavedCard


class SavedCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedCard
        fields = (
            'id',
            'holder_role',
            'brand',
            'last4',
            'exp_month',
            'exp_year',
            'funding',
            'is_default',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class SavedCardCreateSerializer(serializers.Serializer):
    payment_method_id = serializers.CharField(
        max_length=255,
        help_text='Stripe PaymentMethod id (pm_…) from mobile SDK after card confirmation.',
    )


class SavedCardUpdateSerializer(serializers.Serializer):
    is_default = serializers.BooleanField()
