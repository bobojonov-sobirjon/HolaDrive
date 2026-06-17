from __future__ import annotations

from rest_framework import serializers

from apps.notification.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            'id',
            'notification_type',
            'title',
            'message',
            'status',
            'related_object_type',
            'related_object_id',
            'data',
            'read_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

