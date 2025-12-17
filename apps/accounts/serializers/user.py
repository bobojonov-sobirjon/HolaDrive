from rest_framework import serializers
from ..models import CustomUser


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for user details
    """
    full_name = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'full_name', 'phone_number',
            'date_of_birth', 'gender', 'avatar', 'address',
            'longitude', 'latitude', 'tax_number', 'id_identification', 'is_verified', 'is_active',
            'groups', 'created_at', 'updated_at', 'last_login'
        )
        read_only_fields = ('id', 'email', 'username', 'id_identification', 'is_verified', 'created_at', 'updated_at', 'last_login')

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_groups(self, obj):
        """
        Get user groups with optimized query.
        Uses prefetch_related cache if available to avoid additional queries.
        """
        return [{'id': group.id, 'name': group.name} for group in obj.groups.all()]

    def to_representation(self, instance):
        """
        Return avatar as full URL
        """
        representation = super().to_representation(instance)
        if instance.avatar:
            request = self.context.get('request')
            if request:
                representation['avatar'] = request.build_absolute_uri(instance.avatar.url)
            else:
                representation['avatar'] = instance.avatar.url
        else:
            representation['avatar'] = None
        return representation

