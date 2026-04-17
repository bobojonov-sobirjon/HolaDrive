from rest_framework import serializers

from apps.accounts.models import (
    CustomUser,
    DriverVerification,
    DriverIdentificationRegistrationAgreementsUserAccepted,
    DriverIdentificationUploadType,
    DriverIdentificationUploadTypeItem,
    DriverIdentificationUploadTypeQuestionAnswer,
    DriverIdentificationLegalType,
    DriverIdentificationRegistrationType,
    DriverIdentificationTermsType,
)


class AdminPanelDriverListSerializer(serializers.ModelSerializer):
    verification_activation = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    driver_preferences = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    upload_identifications = serializers.SerializerMethodField()
    legal_agreements = serializers.SerializerMethodField()
    registration_agreements = serializers.SerializerMethodField()
    terms_acceptance = serializers.SerializerMethodField()
    device_tokens = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    driver_verification = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'date_of_birth',
            'address',
            'tax_number',
            'avatar',
            'id_identification',
            'is_verified',
            'is_active',
            'is_online',
            'created_at',
            'updated_at',
            'verification_activation',
            'driver_verification',
            'groups',
            'driver_preferences',
            'vehicle',
            'upload_identifications',
            'legal_agreements',
            'registration_agreements',
            'terms_acceptance',
            'device_tokens',
        )

    def get_full_name(self, obj):
        return obj.get_full_name()

    def _build_absolute_url(self, relative_or_absolute_url):
        if not relative_or_absolute_url:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(relative_or_absolute_url)
        return relative_or_absolute_url

    def _agreement_file_url(self, agreement_type_obj):
        if not agreement_type_obj:
            return None
        agreement_item = agreement_type_obj.agreement_items.exclude(file='').exclude(file__isnull=True).first()
        if not agreement_item or not agreement_item.file:
            return None
        return self._build_absolute_url(agreement_item.file.url)

    def get_avatar(self, obj):
        avatar = getattr(obj, 'avatar', None)
        if avatar and hasattr(avatar, 'url'):
            return avatar.url
        return None

    def get_verification_activation(self, obj):
        dv = getattr(obj, 'driver_verification', None)
        if not dv:
            return DriverVerification.Status.NOT_SUBMITTED
        return dv.status

    def get_groups(self, obj):
        return [group.name for group in obj.groups.all()]

    def get_driver_verification(self, obj):
        dv = getattr(obj, 'driver_verification', None)
        if not dv:
            return {
                'status': DriverVerification.Status.NOT_SUBMITTED,
                'status_display': 'Not submitted',
                'comment': None,
                'estimated_review_hours': None,
                'reviewed_at': None,
                'reviewer': None,
            }
        reviewer = getattr(dv, 'reviewer', None)
        return {
            'status': dv.status,
            'status_display': dv.get_status_display(),
            'comment': dv.comment,
            'estimated_review_hours': dv.estimated_review_hours,
            'reviewed_at': dv.reviewed_at,
            'reviewer': reviewer.email if reviewer else None,
        }

    def get_driver_preferences(self, obj):
        pref = obj.driver_preferences.first()
        if not pref:
            return None
        return {
            'trip_type_preference': pref.trip_type_preference,
            'maximum_pickup_distance': pref.maximum_pickup_distance,
            'preferred_working_hours': pref.preferred_working_hours,
            'notification_intensity': pref.notification_intensity,
        }

    def get_vehicle(self, obj):
        vehicle = obj.vehicle_details.first()
        if not vehicle:
            return None
        return {
            'brand': vehicle.brand,
            'model': vehicle.model,
            'year_of_manufacture': vehicle.year_of_manufacture,
            'vin': vehicle.vin,
            'plate_number': vehicle.plate_number,
            'color': vehicle.color,
            'vehicle_condition': vehicle.vehicle_condition,
            'default_ride_type': vehicle.default_ride_type.name if vehicle.default_ride_type else None,
            'supported_ride_types': [ride_type.name for ride_type in vehicle.supported_ride_types.all()],
            'images': [self._build_absolute_url(img.image.url) for img in vehicle.images.all() if img.image],
        }

    def get_upload_identifications(self, obj):
        rows = obj.driver_upload_type_acceptances.all()
        return {
            'total': rows.count(),
            'accepted': rows.filter(is_accepted=True).count(),
            'items': [
                {
                    'id': row.id,
                    'title': row.driver_identification_upload_type.title,
                    'is_accepted': row.is_accepted,
                    'created_at': row.created_at,
                    'file_url': self._build_absolute_url(row.file.url) if row.file else None,
                }
                for row in rows
            ],
        }

    def get_legal_agreements(self, obj):
        rows = obj.driver_legal_agreement_acceptances.all()
        return {
            'total': rows.count(),
            'accepted': rows.filter(is_accepted=True).count(),
            'items': [
                {
                    'id': row.id,
                    'title': row.driver_identification_legal_agreements.title,
                    'is_accepted': row.is_accepted,
                    'updated_at': row.updated_at,
                    'file_url': self._agreement_file_url(row.driver_identification_legal_agreements),
                }
                for row in rows
            ],
        }

    def get_registration_agreements(self, obj):
        rows = obj.driver_registration_agreement_acceptances.all()
        return {
            'total': rows.count(),
            'accepted': rows.filter(is_accepted=True).count(),
            'items': [
                {
                    'id': row.id,
                    'title': row.driver_identification_registration_agreements.title,
                    'is_accepted': row.is_accepted,
                    'updated_at': row.updated_at,
                    'file_url': self._agreement_file_url(row.driver_identification_registration_agreements),
                }
                for row in rows
            ],
        }

    def get_terms_acceptance(self, obj):
        rows = obj.driver_terms_acceptances.all()
        return {
            'total': rows.count(),
            'accepted': rows.filter(is_accepted=True).count(),
            'items': [
                {
                    'id': row.id,
                    'title': row.driver_identification_terms.title,
                    'is_accepted': row.is_accepted,
                    'updated_at': row.updated_at,
                    'file_url': self._agreement_file_url(row.driver_identification_terms),
                }
                for row in rows
            ],
        }

    def get_device_tokens(self, obj):
        return [
            {
                'id': token.id,
                'mobile': token.mobile,
                'token': token.token,
                'created_at': token.created_at,
                'updated_at': token.updated_at,
            }
            for token in obj.device_tokens.all()
        ]


class AdminPanelRiderListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    rider_preferences = serializers.SerializerMethodField()
    invitation_users = serializers.SerializerMethodField()
    pin_verification = serializers.SerializerMethodField()
    registration_agreements = serializers.SerializerMethodField()
    device_tokens = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'date_of_birth',
            'address',
            'tax_number',
            'avatar',
            'id_identification',
            'is_verified',
            'is_active',
            'created_at',
            'updated_at',
            'groups',
            'rider_preferences',
            'invitation_users',
            'pin_verification',
            'registration_agreements',
            'device_tokens',
        )

    def _build_absolute_url(self, relative_or_absolute_url):
        if not relative_or_absolute_url:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(relative_or_absolute_url)
        return relative_or_absolute_url

    def _registration_agreement_file_url(self, agreement_type_obj):
        if not agreement_type_obj:
            return None
        agreement_item = agreement_type_obj.agreement_items.exclude(file='').exclude(file__isnull=True).first()
        if not agreement_item or not agreement_item.file:
            return None
        return self._build_absolute_url(agreement_item.file.url)

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_avatar(self, obj):
        avatar = getattr(obj, 'avatar', None)
        if avatar and hasattr(avatar, 'url'):
            return avatar.url
        return None

    def get_groups(self, obj):
        return [group.name for group in obj.groups.all()]

    def get_rider_preferences(self, obj):
        pref = obj.user_preferences.first()
        if not pref:
            return None
        return {
            'chatting_preference': pref.chatting_preference,
            'temperature_preference': pref.temperature_preference,
            'music_preference': pref.music_preference,
            'volume_level': pref.volume_level,
        }

    def get_invitation_users(self, obj):
        rows = obj.sent_invitations.select_related('receiver').all()
        return {
            'total': rows.count(),
            'active': rows.filter(is_active=True).count(),
            'items': [
                {
                    'id': row.id,
                    'receiver_email': row.receiver.email if row.receiver else None,
                    'is_active': row.is_active,
                    'created_at': row.created_at,
                }
                for row in rows
            ],
        }

    def get_pin_verification(self, obj):
        pin_row = getattr(obj, 'pin_verification', None)
        if not pin_row:
            return None
        return {
            'pin': pin_row.pin,
            'created_at': pin_row.created_at,
            'updated_at': pin_row.updated_at,
        }

    def get_registration_agreements(self, obj):
        rows = DriverIdentificationRegistrationAgreementsUserAccepted.objects.filter(user=obj).select_related(
            'driver_identification_registration_agreements'
        )
        return {
            'total': rows.count(),
            'accepted': rows.filter(is_accepted=True).count(),
            'items': [
                {
                    'id': row.id,
                    'title': row.driver_identification_registration_agreements.title,
                    'is_accepted': row.is_accepted,
                    'updated_at': row.updated_at,
                    'file_url': self._registration_agreement_file_url(
                        row.driver_identification_registration_agreements
                    ),
                }
                for row in rows
            ],
        }

    def get_device_tokens(self, obj):
        return [
            {
                'id': token.id,
                'mobile': token.mobile,
                'token': token.token,
                'created_at': token.created_at,
                'updated_at': token.updated_at,
            }
            for token in obj.device_tokens.all()
        ]


class AdminPanelDriverVerificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    reviewer_email = serializers.EmailField(source='reviewer.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DriverVerification
        fields = (
            'id',
            'user',
            'user_email',
            'status',
            'status_display',
            'reviewer',
            'reviewer_email',
            'comment',
            'estimated_review_hours',
            'created_at',
            'updated_at',
            'reviewed_at',
        )


class AdminPanelDriverVerificationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverVerification
        fields = ('user', 'status', 'comment', 'estimated_review_hours')


class AdminPanelUploadQuestionSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DriverIdentificationUploadTypeQuestionAnswer
        fields = ('id', 'question', 'file_url', 'created_at')

    def get_file_url(self, obj):
        request = self.context.get('request')
        if not obj.file:
            return None
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class AdminPanelUploadItemSerializer(serializers.ModelSerializer):
    question_answers = AdminPanelUploadQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = DriverIdentificationUploadTypeItem
        fields = ('id', 'item', 'created_at', 'question_answers')


class AdminPanelUploadTypeSerializer(serializers.ModelSerializer):
    icon_url = serializers.SerializerMethodField()
    items = AdminPanelUploadItemSerializer(many=True, read_only=True)

    class Meta:
        model = DriverIdentificationUploadType
        fields = ('id', 'title', 'description', 'display_type', 'is_active', 'icon_url', 'created_at', 'updated_at', 'items')

    def get_icon_url(self, obj):
        request = self.context.get('request')
        if not obj.icon:
            return None
        if request:
            return request.build_absolute_uri(obj.icon.url)
        return obj.icon.url


class AdminPanelUploadTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverIdentificationUploadType
        fields = ('title', 'description', 'is_active')


class AdminPanelAgreementItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    content = serializers.CharField()
    file_url = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class _AdminPanelAgreementTypeBaseSerializer(serializers.ModelSerializer):
    agreement_items_data = serializers.SerializerMethodField()

    class Meta:
        fields = ('id', 'title', 'description', 'display_type', 'is_active', 'created_at', 'updated_at', 'agreement_items_data')

    def get_agreement_items_data(self, obj):
        request = self.context.get('request')
        rows = obj.agreement_items.all().order_by('-created_at')
        result = []
        for row in rows:
            file_url = None
            if row.file:
                file_url = request.build_absolute_uri(row.file.url) if request else row.file.url
            result.append({
                'id': row.id,
                'title': row.title,
                'content': row.content,
                'file_url': file_url,
                'created_at': row.created_at,
            })
        return result


class AdminPanelLegalTypeSerializer(_AdminPanelAgreementTypeBaseSerializer):
    class Meta(_AdminPanelAgreementTypeBaseSerializer.Meta):
        model = DriverIdentificationLegalType


class AdminPanelRegistrationTypeSerializer(_AdminPanelAgreementTypeBaseSerializer):
    class Meta(_AdminPanelAgreementTypeBaseSerializer.Meta):
        model = DriverIdentificationRegistrationType


class AdminPanelTermsTypeSerializer(_AdminPanelAgreementTypeBaseSerializer):
    class Meta(_AdminPanelAgreementTypeBaseSerializer.Meta):
        model = DriverIdentificationTermsType


class AdminPanelLegalTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverIdentificationLegalType
        fields = ('title', 'description', 'is_active')


class AdminPanelRegistrationTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverIdentificationRegistrationType
        fields = ('title', 'description', 'is_active')


class AdminPanelTermsTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverIdentificationTermsType
        fields = ('title', 'description', 'is_active')
