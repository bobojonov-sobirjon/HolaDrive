from rest_framework import serializers


class ContactLinkRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        if bool(email) == bool(phone):
            raise serializers.ValidationError('Provide either email or phone_number (not both).')
        attrs['email'] = email or None
        attrs['phone_number'] = phone or None
        return attrs


class ContactLinkConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        if bool(email) == bool(phone):
            raise serializers.ValidationError('Provide either email or phone_number (not both).')
        attrs['email'] = email or None
        attrs['phone_number'] = phone or None
        attrs['code'] = (attrs.get('code') or '').strip()
        return attrs
