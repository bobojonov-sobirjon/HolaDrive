from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from apps.accounts.models import (
    CustomUser,
    DriverIdentificationAgreementsItems,
    DriverVerification,
    LoginLegalDocument,
    DriverIdentificationRegistrationAgreementsUserAccepted,
    DriverIdentificationUploadType,
    DriverIdentificationUploadTypeItem,
    DriverIdentificationUploadTypeQuestionAnswer,
    DriverIdentificationLegalType,
    DriverIdentificationRegistrationType,
    DriverIdentificationTermsType,
)
from apps.accounts.serializers.user import UserDetailSerializer
from apps.payment.models import SavedCard
from apps.order.models import (
    Order,
    RideType,
    OrderItem,
    AdditionalPassenger,
    OrderPreferences,
    UserOrderPreferences,
    OrderDriver,
    OrderSchedule,
    SurgePricing,
    CancelOrder,
    OrderPaymentSplit,
    PromoCode,
    OrderPromoCode,
    RatingFeedbackTag,
    TripRating,
    DriverRiderRating,
    DriverCashout,
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
    online_status = serializers.SerializerMethodField()
    current_location = serializers.SerializerMethodField()

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
            'online_status',
            'current_location',
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
            return self._build_absolute_url(avatar.url)
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

    def get_online_status(self, obj):
        is_online = bool(getattr(obj, 'is_online', False))
        return {
            'is_online': is_online,
            'status': 'online' if is_online else 'offline',
        }

    def get_current_location(self, obj):
        lat = getattr(obj, 'latitude', None)
        lng = getattr(obj, 'longitude', None)
        return {
            'latitude': str(lat) if lat is not None else None,
            'longitude': str(lng) if lng is not None else None,
            'updated_at': obj.updated_at,
            'has_location': lat is not None and lng is not None,
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

    def get_avatar(self, obj):
        avatar = getattr(obj, 'avatar', None)
        if avatar and hasattr(avatar, 'url'):
            return self._build_absolute_url(avatar.url)
        return None

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_groups(self, obj):
        return [group.name for group in obj.groups.all()]

    def get_rider_preferences(self, obj):
        pref = getattr(obj, 'order_preferences_template', None)
        if not pref:
            return None
        return {
            'chatting_preference': pref.chatting_preference,
            'temperature_preference': pref.temperature_preference,
            'music_preference': pref.music_preference,
            'volume_level': pref.volume_level,
            'pet_preference': pref.pet_preference,
            'kids_chair_preference': pref.kids_chair_preference,
            'wheelchair_preference': pref.wheelchair_preference,
            'gender_preference': pref.gender_preference,
            'favorite_driver_preference': pref.favorite_driver_preference,
        }

    def get_invitation_users(self, obj):
        rows = getattr(obj, 'invitation_users_received', None)
        if not rows:
            return []
        return [
            {
                'id': r.id,
                'sender_id': r.sender_id,
                'receiver_id': r.receiver_id,
                'is_active': r.is_active,
                'created_at': r.created_at,
            }
            for r in rows.all()
        ]

    def get_pin_verification(self, obj):
        pin = getattr(obj, 'pin_verification', None)
        if not pin:
            return None
        return {
            'id': pin.id,
            'pin': pin.pin,
            'created_at': pin.created_at,
        }

    def get_registration_agreements(self, obj):
        # Keep backwards compatible shape (empty if not configured)
        return None

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


class AdminPanelSavedCardSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = SavedCard
        fields = (
            'id',
            'user',
            'holder_role',
            'brand',
            'last4',
            'exp_month',
            'exp_year',
            'funding',
            'nickname',
            'is_default',
            'is_active',
            'created_at',
            'updated_at',
            'stripe_payment_method_id',
            'stripe_customer_id',
        )

    def get_user(self, obj):
        u = getattr(obj, 'user', None)
        if not u:
            return None
        return {
            'id': u.id,
            'email': u.email,
            'full_name': u.get_full_name(),
            'phone_number': u.phone_number,
        }


# ---------------------------------------------------------------------------
# Admin Panel — Orders domain (list/detail/CRUD serializers)
# Keep these serializers simple: model fields + minimal nesting. For Order itself
# we reuse apps.order.serializers.order.OrderDetailSerializer in views.
# ---------------------------------------------------------------------------


class AdminOrderBaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'


class AdminRideTypeSerializer(serializers.ModelSerializer):
    """Admin CRUD for ride types (tariffs shown in rider app price estimate)."""

    class Meta:
        model = RideType
        fields = (
            'id',
            'name',
            'name_large',
            'base_price',
            'price_per_km',
            'capacity',
            'icon',
            'is_premium',
            'is_ev',
            'is_active',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {
            'name': {'required': False, 'allow_null': True, 'allow_blank': True},
            'name_large': {'required': False, 'allow_null': True, 'allow_blank': True},
            'base_price': {'required': True},
            'price_per_km': {'required': True},
            'capacity': {'required': False, 'allow_null': True},
            'icon': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def validate_base_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Base price cannot be negative.')
        return value

    def validate_price_per_km(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Price per km cannot be negative.')
        return value

    def validate_capacity(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError('Capacity must be at least 1.')
        return value


class AdminSurgePricingSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = SurgePricing


class AdminOrderItemSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = OrderItem


class AdminAdditionalPassengerSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = AdditionalPassenger


class AdminOrderPreferencesSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = OrderPreferences


class AdminUserOrderPreferencesSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = UserOrderPreferences


class AdminOrderDriverSerializer(AdminOrderBaseModelSerializer):
    driver_obj = serializers.SerializerMethodField()

    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = OrderDriver
        fields = '__all__'

    def get_driver_obj(self, obj):
        request = self.context.get('request')
        driver = getattr(obj, 'driver', None)
        if not driver:
            return None
        return UserDetailSerializer(driver, context={'request': request}).data


class AdminOrderScheduleSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = OrderSchedule


class AdminCancelOrderSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = CancelOrder


class AdminOrderPaymentSplitSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = OrderPaymentSplit


class AdminPromoCodeSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = PromoCode


class AdminOrderPromoCodeSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = OrderPromoCode


class AdminRatingFeedbackTagSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = RatingFeedbackTag


class AdminTripRatingSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = TripRating


class AdminDriverRiderRatingSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = DriverRiderRating


class AdminDriverCashoutSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = DriverCashout


class AdminOrderSerializer(AdminOrderBaseModelSerializer):
    class Meta(AdminOrderBaseModelSerializer.Meta):
        model = Order


class AdminOrderFullSerializer(serializers.Serializer):
    """
    Admin order payload with all related objects split into dedicated keys.
    This keeps admin-panel frontend simple and avoids "hidden" data inside nested serializers.
    """

    def to_representation(self, instance: Order):
        request = self.context.get('request')

        def _many(model_ser, rows):
            return model_ser(rows, many=True, context={'request': request}).data

        def _one(model_ser, obj):
            if not obj:
                return None
            return model_ser(obj, context={'request': request}).data

        # OrderItems with embedded RideType object (instead of only ride_type_id).
        order_items = list(getattr(instance, 'order_items', []).all()) if hasattr(instance, 'order_items') else []
        ride_types_map = {}
        for it in order_items:
            rt = getattr(it, 'ride_type', None)
            if rt:
                ride_types_map[rt.id] = rt

        order_items_out = []
        for it in order_items:
            it_data = AdminOrderItemSerializer(it, context={'request': request}).data
            rt = getattr(it, 'ride_type', None)
            it_data['ride_type_obj'] = _one(AdminRideTypeSerializer, rt) if rt else None
            order_items_out.append(it_data)

        # Preferences: per-order preferences (order_preferences) and user template (order_preferences_template).
        order_preferences_rows = list(getattr(instance, 'order_preferences', []).all()) if hasattr(instance, 'order_preferences') else []
        user_template = getattr(getattr(instance, 'user', None), 'order_preferences_template', None)

        # Ratings: trip_rating and driver_rider_rating (both one-to-one) + include their feedback tags.
        trip_rating = getattr(instance, 'trip_rating', None)
        driver_rider_rating = getattr(instance, 'driver_rider_rating', None)

        def _rating_with_tags(obj, base_ser):
            if not obj:
                return None
            data = base_ser(obj, context={'request': request}).data
            tags = list(getattr(obj, 'feedback_tags', []).all()) if hasattr(obj, 'feedback_tags') else []
            data['feedback_tags'] = _many(AdminRatingFeedbackTagSerializer, tags)
            return data

        # Promo applications (OrderPromoCode)
        applied_promos = list(getattr(instance, 'applied_promo_codes', []).all()) if hasattr(instance, 'applied_promo_codes') else []
        applied_promos_out = []
        for ap in applied_promos:
            ap_data = AdminOrderPromoCodeSerializer(ap, context={'request': request}).data
            ap_data['promo_code_obj'] = _one(AdminPromoCodeSerializer, getattr(ap, 'promo_code', None))
            applied_promos_out.append(ap_data)

        # Driver cashouts are linked to driver (not order) — return for this order driver if exists.
        driver = None
        order_drivers = list(getattr(instance, 'order_drivers', []).all()) if hasattr(instance, 'order_drivers') else []
        if order_drivers:
            driver = getattr(order_drivers[0], 'driver', None)

        return {
            'order': AdminOrderSerializer(instance, context={'request': request}).data,
            'user': UserDetailSerializer(getattr(instance, 'user', None), context={'request': request}).data if getattr(instance, 'user', None) else None,
            'saved_card': _one(AdminPanelSavedCardSerializer, getattr(instance, 'saved_card', None)),
            'stripe_trip_payment': {
                'stripe_trip_payment_intent_id': getattr(instance, 'stripe_trip_payment_intent_id', ''),
                'stripe_trip_payment_status': getattr(instance, 'stripe_trip_payment_status', ''),
                'stripe_trip_payment_amount_cents': getattr(instance, 'stripe_trip_payment_amount_cents', None),
                'stripe_trip_payment_currency': getattr(instance, 'stripe_trip_payment_currency', ''),
                'stripe_trip_payment_error': getattr(instance, 'stripe_trip_payment_error', ''),
            },
            'ride_types': _many(AdminRideTypeSerializer, list(ride_types_map.values())),
            'order_items': order_items_out,
            'order_preferences': _many(AdminOrderPreferencesSerializer, order_preferences_rows),
            'user_order_preferences': _one(AdminUserOrderPreferencesSerializer, user_template),
            'additional_passengers': _many(AdminAdditionalPassengerSerializer, list(getattr(instance, 'additional_passengers', []).all()) if hasattr(instance, 'additional_passengers') else []),
            'order_schedules': _many(AdminOrderScheduleSerializer, list(getattr(instance, 'order_schedules', []).all()) if hasattr(instance, 'order_schedules') else []),
            'order_drivers': _many(AdminOrderDriverSerializer, order_drivers),
            'cancel_orders': _many(AdminCancelOrderSerializer, list(getattr(instance, 'cancel_orders', []).all()) if hasattr(instance, 'cancel_orders') else []),
            'applied_promo_codes': applied_promos_out,
            'trip_rating': _rating_with_tags(trip_rating, AdminTripRatingSerializer),
            'driver_rider_rating': _rating_with_tags(driver_rider_rating, AdminDriverRiderRatingSerializer),
        }

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
        fields = ('title', 'description', 'is_active', 'icon')


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


class AdminPanelAgreementItemWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    content = serializers.CharField(allow_blank=True, required=False, default='')


class _AdminPanelAgreementTypeWriteSerializer(serializers.ModelSerializer):
    """Create/update identification types with nested agreement HTML items."""

    agreement_items = AdminPanelAgreementItemWriteSerializer(many=True, required=False)
    agreement_item_type = None

    def _replace_agreement_items(self, instance, items_data):
        ct = ContentType.objects.get_for_model(self.Meta.model)
        instance.agreement_items.filter(item_type=self.agreement_item_type).delete()
        for item in items_data:
            DriverIdentificationAgreementsItems.objects.create(
                title=item['title'],
                content=item.get('content', ''),
                item_type=self.agreement_item_type,
                content_type=ct,
                object_id=instance.pk,
            )

    def create(self, validated_data):
        items_data = validated_data.pop('agreement_items', [])
        instance = super().create(validated_data)
        if items_data:
            self._replace_agreement_items(instance, items_data)
        return instance

    def update(self, instance, validated_data):
        items_data = validated_data.pop('agreement_items', None)
        instance = super().update(instance, validated_data)
        if items_data is not None:
            self._replace_agreement_items(instance, items_data)
        return instance


class AdminPanelLegalTypeWriteSerializer(_AdminPanelAgreementTypeWriteSerializer):
    agreement_item_type = 'legal'

    class Meta:
        model = DriverIdentificationLegalType
        fields = ('title', 'description', 'is_active', 'agreement_items')


class AdminPanelRegistrationTypeWriteSerializer(_AdminPanelAgreementTypeWriteSerializer):
    agreement_item_type = 'registration'

    class Meta:
        model = DriverIdentificationRegistrationType
        fields = ('title', 'description', 'is_active', 'agreement_items')


class AdminPanelTermsTypeWriteSerializer(_AdminPanelAgreementTypeWriteSerializer):
    agreement_item_type = 'terms'

    class Meta:
        model = DriverIdentificationTermsType
        fields = ('title', 'description', 'is_active', 'agreement_items')


class AdminLoginLegalDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    content_format_display = serializers.CharField(source='get_content_format_display', read_only=True)
    pdf_file_url = serializers.SerializerMethodField()
    open_url = serializers.SerializerMethodField()

    class Meta:
        model = LoginLegalDocument
        fields = (
            'id',
            'document_type',
            'document_type_display',
            'title',
            'content_format',
            'content_format_display',
            'html_content',
            'pdf_file',
            'pdf_file_url',
            'open_url',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'document_type_display', 'content_format_display', 'pdf_file_url', 'open_url')

    def _public_slug(self, document_type: str) -> str:
        from apps.accounts.serializers.login_legal import SLUG_BY_DOCUMENT_TYPE

        return SLUG_BY_DOCUMENT_TYPE.get(document_type, document_type)

    def get_pdf_file_url(self, obj: LoginLegalDocument) -> str | None:
        if not obj.pdf_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return obj.pdf_file.url

    def get_open_url(self, obj: LoginLegalDocument) -> str | None:
        request = self.context.get('request')
        if obj.content_format == LoginLegalDocument.ContentFormat.PDF:
            return self.get_pdf_file_url(obj)
        path = f'/api/v1/accounts/legal-documents/{self._public_slug(obj.document_type)}/view/'
        if request:
            return request.build_absolute_uri(path)
        return path

    def validate(self, attrs):
        content_format = attrs.get(
            'content_format',
            getattr(self.instance, 'content_format', LoginLegalDocument.ContentFormat.HTML),
        )
        html_content = attrs.get('html_content', getattr(self.instance, 'html_content', '') or '')
        pdf_file = attrs.get('pdf_file', getattr(self.instance, 'pdf_file', None))

        if content_format == LoginLegalDocument.ContentFormat.PDF:
            if not pdf_file and not (self.instance and self.instance.pdf_file):
                raise serializers.ValidationError(
                    {'pdf_file': ['PDF file is required when content format is PDF.']}
                )
        elif content_format == LoginLegalDocument.ContentFormat.HTML:
            if not str(html_content).strip():
                raise serializers.ValidationError(
                    {'html_content': ['HTML content is required when content format is HTML.']}
                )
        return attrs
