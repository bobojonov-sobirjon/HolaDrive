from rest_framework import serializers

from ..models import DriverVerification


class DriverVerificationSerializer(serializers.ModelSerializer):
    """Serializer for driver verification status."""

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
