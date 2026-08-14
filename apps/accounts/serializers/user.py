from django.db.models import Avg, Count
from rest_framework import serializers
from ..models import CustomUser
from ..services import validate_canadian_tax_number, validate_phone_number


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for user details
    """
    full_name = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'full_name', 'phone_number',
            'date_of_birth', 'gender', 'avatar', 'address',
            'longitude', 'latitude', 'tax_number', 'tvq_number', 'id_identification',
            'is_verified', 'is_active',
            'rating', 'rating_count',
            'groups', 'created_at', 'updated_at', 'last_login'
        )
        read_only_fields = (
            'id', 'email', 'username', 'id_identification', 'is_verified',
            'rating', 'rating_count', 'created_at', 'updated_at', 'last_login',
        )

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_groups(self, obj):
        """
        Get user groups with optimized query.
        Uses prefetch_related cache if available to avoid additional queries.
        """
        return [{'id': group.id, 'name': group.name} for group in obj.groups.all()]

    def _profile_rating_stats(self, obj):
        """
        Driver: average of approved TripRating (rider → driver).
        Rider: average of DriverRiderRating (driver → rider).
        Others: 0 / 0.
        """
        cached = getattr(obj, '_profile_rating_stats_cache', None)
        if cached is not None:
            return cached

        group_names = {g.name for g in obj.groups.all()}
        average = 0.0
        count = 0

        if 'Driver' in group_names:
            from apps.order.models import TripRating

            agg = TripRating.objects.filter(driver=obj, status='approved').aggregate(
                avg=Avg('rating'),
                count=Count('id'),
            )
            count = int(agg['count'] or 0)
            if agg['avg'] is not None:
                average = round(float(agg['avg']), 2)
        elif 'Rider' in group_names:
            from apps.order.models import DriverRiderRating

            agg = DriverRiderRating.objects.filter(rider=obj).aggregate(
                avg=Avg('rating'),
                count=Count('id'),
            )
            count = int(agg['count'] or 0)
            if agg['avg'] is not None:
                average = round(float(agg['avg']), 2)

        cached = {'rating': average, 'rating_count': count}
        obj._profile_rating_stats_cache = cached
        return cached

    def get_rating(self, obj):
        return self._profile_rating_stats(obj)['rating']

    def get_rating_count(self, obj):
        return self._profile_rating_stats(obj)['rating_count']

    def validate_phone_number(self, value):
        if not value:
            return value
        try:
            normalized = validate_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        from ..services import phone_already_taken

        user = self.instance
        if phone_already_taken(normalized, exclude_user_id=user.pk if user else None):
            raise serializers.ValidationError(
                'This phone number is already linked to another account.'
            )
        return normalized

    def validate_tax_number(self, value):
        if not value:
            return value
        try:
            return validate_canadian_tax_number(value, field_label='GST/HST number')
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_tvq_number(self, value):
        if not value:
            return value
        try:
            return validate_canadian_tax_number(value, field_label='TVQ number')
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

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

    def update(self, instance, validated_data):
        """
        Support updating full_name from API payload by splitting it into
        first_name/last_name on the CustomUser model.
        """
        full_name = (self.initial_data.get('full_name') or '').strip()
        if full_name:
            name_parts = full_name.split(None, 1)
            instance.first_name = name_parts[0]
            instance.last_name = name_parts[1] if len(name_parts) > 1 else ''

        return super().update(instance, validated_data)


class AvatarUpdateRequestSerializer(serializers.Serializer):
    """Request body for avatar update (multipart/form-data)."""
    avatar = serializers.ImageField(required=True, help_text='Profile picture file')

