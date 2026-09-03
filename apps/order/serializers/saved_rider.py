from rest_framework import serializers

from apps.order.models import SavedRider
from apps.order.services.guest_rider import normalize_guest_fields, upsert_saved_rider


class SavedRiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedRider
        fields = ['id', 'full_name', 'email', 'phone_number', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate(self, attrs):
        full_name = attrs.get('full_name', getattr(self.instance, 'full_name', None))
        email = attrs.get('email', getattr(self.instance, 'email', '') if self.instance else '')
        phone = attrs.get('phone_number', getattr(self.instance, 'phone_number', None))
        name, email_clean, phone_clean = normalize_guest_fields(
            full_name=full_name,
            email=email,
            phone_number=phone,
        )
        attrs['full_name'] = name
        attrs['email'] = email_clean
        attrs['phone_number'] = phone_clean
        return attrs

    def create(self, validated_data):
        owner = self.context['request'].user
        return upsert_saved_rider(
            owner,
            full_name=validated_data['full_name'],
            email=validated_data.get('email') or '',
            phone_number=validated_data['phone_number'],
        )

    def update(self, instance, validated_data):
        owner = instance.owner
        phone = validated_data.get('phone_number', instance.phone_number)
        clash = (
            SavedRider.objects.filter(owner=owner, phone_number=phone)
            .exclude(pk=instance.pk)
            .exists()
        )
        if clash:
            raise serializers.ValidationError(
                {'phone_number': 'You already saved a rider with this phone number.'}
            )
        return super().update(instance, validated_data)


class GuestRiderInputSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=32)
