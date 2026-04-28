from asgiref.sync import sync_to_async
from django.contrib.auth.models import Group
from django.db.models import Q
from django.db.utils import IntegrityError
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce, TruncDay, TruncMonth
from django.db.models import DecimalField, Value
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import (
    CustomUser,
    DriverVerification,
    DriverIdentificationUploadType,
    DriverIdentificationLegalType,
    DriverIdentificationRegistrationType,
    DriverIdentificationTermsType,
)
from apps.common.views import AsyncAPIView
from apps.order.models import (
    Order,
    RideType,
    OrderItem,
    AdditionalPassenger,
    OrderPreferences,
    UserOrderPreferences,
    OrderDriver,
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

from .serializers import (
    AdminPanelDriverListSerializer,
    AdminPanelRiderListSerializer,
    AdminPanelSavedCardSerializer,
    AdminRideTypeSerializer,
    AdminSurgePricingSerializer,
    AdminOrderItemSerializer,
    AdminAdditionalPassengerSerializer,
    AdminOrderPreferencesSerializer,
    AdminUserOrderPreferencesSerializer,
    AdminOrderDriverSerializer,
    AdminCancelOrderSerializer,
    AdminOrderPaymentSplitSerializer,
    AdminPromoCodeSerializer,
    AdminOrderPromoCodeSerializer,
    AdminRatingFeedbackTagSerializer,
    AdminTripRatingSerializer,
    AdminDriverRiderRatingSerializer,
    AdminDriverCashoutSerializer,
    AdminOrderFullSerializer,
    AdminPanelDriverVerificationSerializer,
    AdminPanelUploadTypeSerializer,
    AdminPanelLegalTypeSerializer,
    AdminPanelRegistrationTypeSerializer,
    AdminPanelTermsTypeSerializer,
    AdminPanelDriverVerificationWriteSerializer,
    AdminPanelUploadTypeWriteSerializer,
    AdminPanelLegalTypeWriteSerializer,
    AdminPanelRegistrationTypeWriteSerializer,
    AdminPanelTermsTypeWriteSerializer,
)
from apps.payment.models import SavedCard


class AdminPanelDriversListView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin Panel'],
        summary='Drivers list for admin panel',
        description='Returns all drivers with profile, verification and related admin panel data.',
        responses=AdminPanelDriverListSerializer(many=True),
    )
    async def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {
                    'message': 'Only superusers can access admin panel APIs.',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        search = (request.query_params.get('search') or '').strip()

        try:
            driver_group = await sync_to_async(Group.objects.get)(name='Driver')
        except Group.DoesNotExist:
            return Response(
                {
                    'message': 'Drivers retrieved successfully',
                    'status': 'success',
                    'data': [],
                },
                status=status.HTTP_200_OK,
            )

        queryset = (
            CustomUser.objects.filter(groups=driver_group)
            .select_related('driver_verification', 'driver_verification__reviewer')
            .prefetch_related(
                'groups',
                'driver_preferences',
                'vehicle_details',
                'vehicle_details__default_ride_type',
                'vehicle_details__supported_ride_types',
                'vehicle_details__images',
                'driver_upload_type_acceptances',
                'driver_upload_type_acceptances__driver_identification_upload_type',
                'driver_legal_agreement_acceptances',
                'driver_legal_agreement_acceptances__driver_identification_legal_agreements',
                'driver_registration_agreement_acceptances',
                'driver_registration_agreement_acceptances__driver_identification_registration_agreements',
                'driver_terms_acceptances',
                'driver_terms_acceptances__driver_identification_terms',
                'device_tokens',
            )
            .order_by('-created_at')
        )

        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(id_identification__icontains=search)
            )

        drivers = await sync_to_async(list)(queryset)
        serializer = AdminPanelDriverListSerializer(drivers, many=True, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Drivers retrieved successfully',
                'status': 'success',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class AdminPanelDriverDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin Panel'],
        summary='Driver detail for admin panel',
        description='Returns full detail for one driver by id.',
        responses=AdminPanelDriverListSerializer,
    )
    async def get(self, request, driver_id):
        if not request.user.is_superuser:
            return Response(
                {
                    'message': 'Only superusers can access admin panel APIs.',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            driver_group = await sync_to_async(Group.objects.get)(name='Driver')
        except Group.DoesNotExist:
            return Response(
                {
                    'message': 'Driver not found.',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = (
            CustomUser.objects.filter(groups=driver_group, id=driver_id)
            .select_related('driver_verification', 'driver_verification__reviewer')
            .prefetch_related(
                'groups',
                'driver_preferences',
                'vehicle_details',
                'vehicle_details__default_ride_type',
                'vehicle_details__supported_ride_types',
                'vehicle_details__images',
                'driver_upload_type_acceptances',
                'driver_upload_type_acceptances__driver_identification_upload_type',
                'driver_legal_agreement_acceptances',
                'driver_legal_agreement_acceptances__driver_identification_legal_agreements',
                'driver_registration_agreement_acceptances',
                'driver_registration_agreement_acceptances__driver_identification_registration_agreements',
                'driver_terms_acceptances',
                'driver_terms_acceptances__driver_identification_terms',
                'device_tokens',
            )
        )

        driver = await sync_to_async(queryset.first)()
        if not driver:
            return Response(
                {
                    'message': 'Driver not found.',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminPanelDriverListSerializer(driver, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Driver retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class AdminPanelRidersListView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin Panel'],
        summary='Riders list for admin panel',
        description='Returns all riders with profile and related admin panel data.',
        responses=AdminPanelRiderListSerializer(many=True),
    )
    async def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {
                    'message': 'Only superusers can access admin panel APIs.',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        search = (request.query_params.get('search') or '').strip()

        try:
            rider_group = await sync_to_async(Group.objects.get)(name='Rider')
        except Group.DoesNotExist:
            return Response(
                {
                    'message': 'Riders retrieved successfully',
                    'status': 'success',
                    'data': [],
                },
                status=status.HTTP_200_OK,
            )

        queryset = (
            CustomUser.objects.filter(groups=rider_group)
            .prefetch_related(
                'groups',
                'user_preferences',
                'sent_invitations',
                'sent_invitations__receiver',
                'device_tokens',
            )
            .order_by('-created_at')
        )

        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(id_identification__icontains=search)
            )

        riders = await sync_to_async(list)(queryset)
        serializer = AdminPanelRiderListSerializer(riders, many=True, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Riders retrieved successfully',
                'status': 'success',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class AdminPanelRiderDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin Panel'],
        summary='Rider detail for admin panel',
        description='Returns full detail for one rider by id.',
        responses=AdminPanelRiderListSerializer,
    )
    async def get(self, request, rider_id):
        if not request.user.is_superuser:
            return Response(
                {
                    'message': 'Only superusers can access admin panel APIs.',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            rider_group = await sync_to_async(Group.objects.get)(name='Rider')
        except Group.DoesNotExist:
            return Response(
                {
                    'message': 'Rider not found.',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = (
            CustomUser.objects.filter(groups=rider_group, id=rider_id)
            .prefetch_related(
                'groups',
                'user_preferences',
                'sent_invitations',
                'sent_invitations__receiver',
                'device_tokens',
            )
        )
        rider = await sync_to_async(queryset.first)()

        if not rider:
            return Response(
                {
                    'message': 'Rider not found.',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminPanelRiderListSerializer(rider, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Rider retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class AdminPanelSavedCardsListView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin Panel'],
        summary='Admin: list all saved cards',
        description=(
            'Returns saved cards across all users (riders and drivers). '
            'Optional filters: `holder_role` (rider|driver), `user_id`, `is_active` (true|false).'
        ),
        responses=AdminPanelSavedCardSerializer(many=True),
    )
    async def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )

        holder_role = (request.query_params.get('holder_role') or '').strip().lower()
        user_id = (request.query_params.get('user_id') or '').strip()
        is_active_q = (request.query_params.get('is_active') or '').strip().lower()

        qs = SavedCard.objects.select_related('user').order_by('-created_at')
        if holder_role in ('rider', 'driver'):
            qs = qs.filter(holder_role=holder_role)
        if user_id.isdigit():
            qs = qs.filter(user_id=int(user_id))
        if is_active_q in ('true', 'false'):
            qs = qs.filter(is_active=(is_active_q == 'true'))

        rows = await sync_to_async(list)(qs)
        ser = AdminPanelSavedCardSerializer(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response(
            {
                'message': 'Saved cards retrieved successfully',
                'status': 'success',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class _AdminPanelCRUDBaseView(AsyncAPIView):
    """
    Minimal reusable CRUD for Admin Panel.
    - List view implements GET(list) + POST(create)
    - Detail view implements GET(detail) + PATCH(update) + DELETE
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    model = None
    serializer_class = None
    tag_name = 'Admin Panel'
    list_summary = 'List'
    detail_summary = 'Detail'
    create_summary = 'Create'
    update_summary = 'Update'
    delete_summary = 'Delete'
    not_found_message = 'Object not found.'

    def _forbidden_response(self):
        return Response(
            {
                'message': 'Only superusers can access admin panel APIs.',
                'status': 'error',
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    def base_queryset(self):
        return self.model.objects.order_by('-id')

    async def _list(self, request):
        qs = self.base_queryset()
        rows = await sync_to_async(list)(qs)
        ser = self.serializer_class(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response(
            {'message': 'Retrieved successfully', 'status': 'success', 'count': len(data), 'data': data},
            status=status.HTTP_200_OK,
        )

    async def _detail(self, request, pk):
        row = await sync_to_async(lambda: self.base_queryset().filter(id=pk).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        ser = self.serializer_class(row, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'Retrieved successfully', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)

    async def _create(self, request):
        ser_in = self.serializer_class(data=request.data, context={'request': request})
        valid = await sync_to_async(lambda: ser_in.is_valid())()
        if not valid:
            errors = await sync_to_async(lambda: ser_in.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        obj = await sync_to_async(ser_in.save)()
        ser = self.serializer_class(obj, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'Created successfully', 'status': 'success', 'data': data}, status=status.HTTP_201_CREATED)

    async def _update(self, request, pk):
        row = await sync_to_async(lambda: self.model.objects.filter(id=pk).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        ser_in = self.serializer_class(row, data=request.data, partial=True, context={'request': request})
        valid = await sync_to_async(lambda: ser_in.is_valid())()
        if not valid:
            errors = await sync_to_async(lambda: ser_in.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        obj = await sync_to_async(ser_in.save)()
        ser = self.serializer_class(obj, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'Updated successfully', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)

    async def _delete(self, request, pk):
        row = await sync_to_async(lambda: self.model.objects.filter(id=pk).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        try:
            await sync_to_async(row.delete)()
        except IntegrityError:
            return Response(
                {'message': 'Cannot delete: object is referenced by other records.', 'status': 'error'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({'message': 'Deleted successfully', 'status': 'success'}, status=status.HTTP_200_OK)


class AdminOrdersListView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=['Admin Panel'], summary='Admin Orders: list (full split objects)', responses=AdminOrderFullSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = (
            Order.objects.select_related('user', 'saved_card')
            .prefetch_related(
                'order_items__ride_type',
                'order_preferences',
                'additional_passengers',
                'order_schedules',
                'order_drivers__driver',
                'cancel_orders',
                'payment_splits',
            )
            .order_by('-created_at')
        )
        rows = await sync_to_async(list)(qs)
        ser = AdminOrderFullSerializer(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'Orders retrieved successfully', 'status': 'success', 'count': len(data), 'data': data}, status=status.HTTP_200_OK)


class AdminOrdersDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=['Admin Panel'], summary='Admin Orders: detail (full split objects)', responses=AdminOrderFullSerializer)
    async def get(self, request, order_id):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = (
            Order.objects.select_related('user', 'saved_card')
            .prefetch_related(
                'order_items__ride_type',
                'order_preferences',
                'additional_passengers',
                'order_schedules',
                'order_drivers__driver',
                'cancel_orders',
                'payment_splits',
            )
            .filter(id=order_id)
        )
        row = await sync_to_async(lambda: qs.first())()
        if not row:
            return Response({'message': 'Order not found.', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        ser = AdminOrderFullSerializer(row, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'Order retrieved successfully', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)


class AdminRideTypesListView(_AdminPanelCRUDBaseView):
    model = RideType
    serializer_class = AdminRideTypeSerializer

    @extend_schema(tags=['Admin Ride Types'], summary='Admin Ride Types: list', responses=AdminRideTypeSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Ride Types'], summary='Admin Ride Types: create', request=AdminRideTypeSerializer, responses=AdminRideTypeSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminRideTypesDetailView(_AdminPanelCRUDBaseView):
    model = RideType
    serializer_class = AdminRideTypeSerializer
    not_found_message = 'Ride type not found.'

    @extend_schema(tags=['Admin Ride Types'], summary='Admin Ride Types: detail', responses=AdminRideTypeSerializer)
    async def get(self, request, ride_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, ride_type_id)

    @extend_schema(tags=['Admin Ride Types'], summary='Admin Ride Types: update', request=AdminRideTypeSerializer, responses=AdminRideTypeSerializer)
    async def patch(self, request, ride_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, ride_type_id)

    @extend_schema(tags=['Admin Ride Types'], summary='Admin Ride Types: delete')
    async def delete(self, request, ride_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, ride_type_id)


class AdminSurgePricingsListView(_AdminPanelCRUDBaseView):
    model = SurgePricing
    serializer_class = AdminSurgePricingSerializer

    @extend_schema(tags=['Admin Surge Pricings'], summary='Admin Surge Pricings: list', responses=AdminSurgePricingSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Surge Pricings'], summary='Admin Surge Pricings: create', request=AdminSurgePricingSerializer, responses=AdminSurgePricingSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminSurgePricingsDetailView(_AdminPanelCRUDBaseView):
    model = SurgePricing
    serializer_class = AdminSurgePricingSerializer
    not_found_message = 'Surge pricing not found.'

    @extend_schema(tags=['Admin Surge Pricings'], summary='Admin Surge Pricings: detail', responses=AdminSurgePricingSerializer)
    async def get(self, request, surge_pricing_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, surge_pricing_id)

    @extend_schema(tags=['Admin Surge Pricings'], summary='Admin Surge Pricings: update', request=AdminSurgePricingSerializer, responses=AdminSurgePricingSerializer)
    async def patch(self, request, surge_pricing_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, surge_pricing_id)

    @extend_schema(tags=['Admin Surge Pricings'], summary='Admin Surge Pricings: delete')
    async def delete(self, request, surge_pricing_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, surge_pricing_id)


# GET-only endpoints (list + detail) for remaining sections for now.
# They still support create/update/delete via CRUD base if needed later.


class AdminOrderItemsListView(_AdminPanelCRUDBaseView):
    model = OrderItem
    serializer_class = AdminOrderItemSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Items: list', responses=AdminOrderItemSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Items: create', request=AdminOrderItemSerializer, responses=AdminOrderItemSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminOrderItemsDetailView(_AdminPanelCRUDBaseView):
    model = OrderItem
    serializer_class = AdminOrderItemSerializer
    not_found_message = 'Order item not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Items: detail', responses=AdminOrderItemSerializer)
    async def get(self, request, order_item_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, order_item_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Items: update', request=AdminOrderItemSerializer, responses=AdminOrderItemSerializer)
    async def patch(self, request, order_item_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, order_item_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Items: delete')
    async def delete(self, request, order_item_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, order_item_id)


class AdminAdditionalPassengersListView(_AdminPanelCRUDBaseView):
    model = AdditionalPassenger
    serializer_class = AdminAdditionalPassengerSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Additional Passengers: list', responses=AdminAdditionalPassengerSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Additional Passengers: create', request=AdminAdditionalPassengerSerializer, responses=AdminAdditionalPassengerSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminAdditionalPassengersDetailView(_AdminPanelCRUDBaseView):
    model = AdditionalPassenger
    serializer_class = AdminAdditionalPassengerSerializer
    not_found_message = 'Additional passenger not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Additional Passengers: detail', responses=AdminAdditionalPassengerSerializer)
    async def get(self, request, additional_passenger_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, additional_passenger_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Additional Passengers: update', request=AdminAdditionalPassengerSerializer, responses=AdminAdditionalPassengerSerializer)
    async def patch(self, request, additional_passenger_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, additional_passenger_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Additional Passengers: delete')
    async def delete(self, request, additional_passenger_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, additional_passenger_id)


class AdminOrderPreferencesListView(_AdminPanelCRUDBaseView):
    model = OrderPreferences
    serializer_class = AdminOrderPreferencesSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences: list', responses=AdminOrderPreferencesSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences: create', request=AdminOrderPreferencesSerializer, responses=AdminOrderPreferencesSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminOrderPreferencesDetailView(_AdminPanelCRUDBaseView):
    model = OrderPreferences
    serializer_class = AdminOrderPreferencesSerializer
    not_found_message = 'Order preferences not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences: detail', responses=AdminOrderPreferencesSerializer)
    async def get(self, request, order_preferences_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, order_preferences_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences: update', request=AdminOrderPreferencesSerializer, responses=AdminOrderPreferencesSerializer)
    async def patch(self, request, order_preferences_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, order_preferences_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences: delete')
    async def delete(self, request, order_preferences_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, order_preferences_id)


class AdminUserOrderPreferencesListView(_AdminPanelCRUDBaseView):
    model = UserOrderPreferences
    serializer_class = AdminUserOrderPreferencesSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences Admin (user templates): list', responses=AdminUserOrderPreferencesSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences Admin (user templates): create', request=AdminUserOrderPreferencesSerializer, responses=AdminUserOrderPreferencesSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminUserOrderPreferencesDetailView(_AdminPanelCRUDBaseView):
    model = UserOrderPreferences
    serializer_class = AdminUserOrderPreferencesSerializer
    not_found_message = 'User order preferences not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences Admin (user templates): detail', responses=AdminUserOrderPreferencesSerializer)
    async def get(self, request, user_order_preferences_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, user_order_preferences_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences Admin (user templates): update', request=AdminUserOrderPreferencesSerializer, responses=AdminUserOrderPreferencesSerializer)
    async def patch(self, request, user_order_preferences_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, user_order_preferences_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Preferences Admin (user templates): delete')
    async def delete(self, request, user_order_preferences_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, user_order_preferences_id)


class AdminOrderDriversListView(_AdminPanelCRUDBaseView):
    model = OrderDriver
    serializer_class = AdminOrderDriverSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Drivers: list', responses=AdminOrderDriverSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Drivers: create', request=AdminOrderDriverSerializer, responses=AdminOrderDriverSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminOrderDriversDetailView(_AdminPanelCRUDBaseView):
    model = OrderDriver
    serializer_class = AdminOrderDriverSerializer
    not_found_message = 'Order driver not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Drivers: detail', responses=AdminOrderDriverSerializer)
    async def get(self, request, order_driver_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, order_driver_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Drivers: update', request=AdminOrderDriverSerializer, responses=AdminOrderDriverSerializer)
    async def patch(self, request, order_driver_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, order_driver_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Drivers: delete')
    async def delete(self, request, order_driver_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, order_driver_id)


class AdminCancelOrdersListView(_AdminPanelCRUDBaseView):
    model = CancelOrder
    serializer_class = AdminCancelOrderSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Cancel Orders: list', responses=AdminCancelOrderSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Cancel Orders: create', request=AdminCancelOrderSerializer, responses=AdminCancelOrderSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminCancelOrdersDetailView(_AdminPanelCRUDBaseView):
    model = CancelOrder
    serializer_class = AdminCancelOrderSerializer
    not_found_message = 'Cancel order not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Cancel Orders: detail', responses=AdminCancelOrderSerializer)
    async def get(self, request, cancel_order_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, cancel_order_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Cancel Orders: update', request=AdminCancelOrderSerializer, responses=AdminCancelOrderSerializer)
    async def patch(self, request, cancel_order_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, cancel_order_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Cancel Orders: delete')
    async def delete(self, request, cancel_order_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, cancel_order_id)


class AdminOrderPaymentSplitsListView(_AdminPanelCRUDBaseView):
    model = OrderPaymentSplit
    serializer_class = AdminOrderPaymentSplitSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Payment Status (splits): list', responses=AdminOrderPaymentSplitSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Payment Status (splits): create', request=AdminOrderPaymentSplitSerializer, responses=AdminOrderPaymentSplitSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminOrderPaymentSplitsDetailView(_AdminPanelCRUDBaseView):
    model = OrderPaymentSplit
    serializer_class = AdminOrderPaymentSplitSerializer
    not_found_message = 'Order payment split not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Payment Status (splits): detail', responses=AdminOrderPaymentSplitSerializer)
    async def get(self, request, payment_split_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, payment_split_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Payment Status (splits): update', request=AdminOrderPaymentSplitSerializer, responses=AdminOrderPaymentSplitSerializer)
    async def patch(self, request, payment_split_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, payment_split_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Payment Status (splits): delete')
    async def delete(self, request, payment_split_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, payment_split_id)


class AdminPromoCodesListView(_AdminPanelCRUDBaseView):
    model = PromoCode
    serializer_class = AdminPromoCodeSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Promo Codes: list', responses=AdminPromoCodeSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Promo Codes: create', request=AdminPromoCodeSerializer, responses=AdminPromoCodeSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminPromoCodesDetailView(_AdminPanelCRUDBaseView):
    model = PromoCode
    serializer_class = AdminPromoCodeSerializer
    not_found_message = 'Promo code not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Promo Codes: detail', responses=AdminPromoCodeSerializer)
    async def get(self, request, promo_code_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, promo_code_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Promo Codes: update', request=AdminPromoCodeSerializer, responses=AdminPromoCodeSerializer)
    async def patch(self, request, promo_code_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, promo_code_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Promo Codes: delete')
    async def delete(self, request, promo_code_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, promo_code_id)


class AdminOrderPromoCodesListView(_AdminPanelCRUDBaseView):
    model = OrderPromoCode
    serializer_class = AdminOrderPromoCodeSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Promo Codes: list', responses=AdminOrderPromoCodeSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Promo Codes: create', request=AdminOrderPromoCodeSerializer, responses=AdminOrderPromoCodeSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminOrderPromoCodesDetailView(_AdminPanelCRUDBaseView):
    model = OrderPromoCode
    serializer_class = AdminOrderPromoCodeSerializer
    not_found_message = 'Order promo code not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Promo Codes: detail', responses=AdminOrderPromoCodeSerializer)
    async def get(self, request, order_promo_code_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, order_promo_code_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Promo Codes: update', request=AdminOrderPromoCodeSerializer, responses=AdminOrderPromoCodeSerializer)
    async def patch(self, request, order_promo_code_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, order_promo_code_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Order Promo Codes: delete')
    async def delete(self, request, order_promo_code_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, order_promo_code_id)


class AdminRatingFeedbackTagsListView(_AdminPanelCRUDBaseView):
    model = RatingFeedbackTag
    serializer_class = AdminRatingFeedbackTagSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Rating Feedback: list', responses=AdminRatingFeedbackTagSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Rating Feedback: create', request=AdminRatingFeedbackTagSerializer, responses=AdminRatingFeedbackTagSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminRatingFeedbackTagsDetailView(_AdminPanelCRUDBaseView):
    model = RatingFeedbackTag
    serializer_class = AdminRatingFeedbackTagSerializer
    not_found_message = 'Rating feedback tag not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Rating Feedback: detail', responses=AdminRatingFeedbackTagSerializer)
    async def get(self, request, rating_feedback_tag_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, rating_feedback_tag_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Rating Feedback: update', request=AdminRatingFeedbackTagSerializer, responses=AdminRatingFeedbackTagSerializer)
    async def patch(self, request, rating_feedback_tag_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, rating_feedback_tag_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Rating Feedback: delete')
    async def delete(self, request, rating_feedback_tag_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, rating_feedback_tag_id)


class AdminTripRatingsListView(_AdminPanelCRUDBaseView):
    model = TripRating
    serializer_class = AdminTripRatingSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Trip Ratings: list', responses=AdminTripRatingSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Trip Ratings: create', request=AdminTripRatingSerializer, responses=AdminTripRatingSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminTripRatingsDetailView(_AdminPanelCRUDBaseView):
    model = TripRating
    serializer_class = AdminTripRatingSerializer
    not_found_message = 'Trip rating not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Trip Ratings: detail', responses=AdminTripRatingSerializer)
    async def get(self, request, trip_rating_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, trip_rating_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Trip Ratings: update', request=AdminTripRatingSerializer, responses=AdminTripRatingSerializer)
    async def patch(self, request, trip_rating_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, trip_rating_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Trip Ratings: delete')
    async def delete(self, request, trip_rating_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, trip_rating_id)


class AdminDriverRiderRatingsListView(_AdminPanelCRUDBaseView):
    model = DriverRiderRating
    serializer_class = AdminDriverRiderRatingSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Rider Ratings: list', responses=AdminDriverRiderRatingSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Rider Ratings: create', request=AdminDriverRiderRatingSerializer, responses=AdminDriverRiderRatingSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminDriverRiderRatingsDetailView(_AdminPanelCRUDBaseView):
    model = DriverRiderRating
    serializer_class = AdminDriverRiderRatingSerializer
    not_found_message = 'Driver rider rating not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Rider Ratings: detail', responses=AdminDriverRiderRatingSerializer)
    async def get(self, request, driver_rider_rating_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, driver_rider_rating_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Rider Ratings: update', request=AdminDriverRiderRatingSerializer, responses=AdminDriverRiderRatingSerializer)
    async def patch(self, request, driver_rider_rating_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, driver_rider_rating_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Rider Ratings: delete')
    async def delete(self, request, driver_rider_rating_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, driver_rider_rating_id)


class AdminDriverCashoutsListView(_AdminPanelCRUDBaseView):
    model = DriverCashout
    serializer_class = AdminDriverCashoutSerializer

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Cashouts: list', responses=AdminDriverCashoutSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._list(request)

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Cashouts: create', request=AdminDriverCashoutSerializer, responses=AdminDriverCashoutSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminDriverCashoutsDetailView(_AdminPanelCRUDBaseView):
    model = DriverCashout
    serializer_class = AdminDriverCashoutSerializer
    not_found_message = 'Driver cashout not found.'

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Cashouts: detail', responses=AdminDriverCashoutSerializer)
    async def get(self, request, driver_cashout_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._detail(request, driver_cashout_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Cashouts: update', request=AdminDriverCashoutSerializer, responses=AdminDriverCashoutSerializer)
    async def patch(self, request, driver_cashout_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, driver_cashout_id)

    @extend_schema(tags=['Admin Panel'], summary='Admin Driver Cashouts: delete')
    async def delete(self, request, driver_cashout_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._delete(request, driver_cashout_id)


class AdminAnalyticsDashboardView(AsyncAPIView):
    """
    Admin analytics dashboard endpoint.
    Returns summary cards + charts (series) + recent orders for the admin panel UI.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin Panel'],
        summary='Admin analytics dashboard',
        description=(
            'Query params:\n'
            '- `date_from` (YYYY-MM-DD) optional\n'
            '- `date_to` (YYYY-MM-DD) optional\n'
            '- `interval` = `day` | `month` (default `month`)\n'
            '- `recent_limit` (default 10)\n'
        ),
    )
    async def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Parse filters
        interval = (request.query_params.get('interval') or 'month').strip().lower()
        if interval not in ('day', 'month'):
            interval = 'month'

        def _parse_date(s):
            try:
                from datetime import datetime

                return datetime.strptime(s, '%Y-%m-%d').date()
            except Exception:
                return None

        date_from = _parse_date((request.query_params.get('date_from') or '').strip())
        date_to = _parse_date((request.query_params.get('date_to') or '').strip())

        now = timezone.now()
        if not date_to:
            date_to = now.date()
        if not date_from:
            # Default: last 30 days for day interval, last 12 months for month interval
            from datetime import timedelta

            if interval == 'day':
                date_from = date_to - timedelta(days=30)
            else:
                date_from = date_to - timedelta(days=365)

        dt_from = timezone.make_aware(timezone.datetime.combine(date_from, timezone.datetime.min.time()))
        dt_to = timezone.make_aware(timezone.datetime.combine(date_to, timezone.datetime.max.time()))

        # Previous period for growth comparison (same length)
        delta = dt_to - dt_from
        prev_to = dt_from - timezone.timedelta(seconds=1)
        prev_from = prev_to - delta

        def _pct_change(current, previous):
            try:
                current = float(current or 0)
                previous = float(previous or 0)
                if previous == 0:
                    return 100.0 if current > 0 else 0.0
                return round(((current - previous) / previous) * 100.0, 2)
            except Exception:
                return 0.0

        # Users: riders/drivers (based on groups)
        users_qs = CustomUser.objects.filter(created_at__range=(dt_from, dt_to)).distinct()
        prev_users_qs = CustomUser.objects.filter(created_at__range=(prev_from, prev_to)).distinct()

        riders_current = await sync_to_async(lambda: users_qs.filter(groups__name='Rider').count())()
        drivers_current = await sync_to_async(lambda: users_qs.filter(groups__name='Driver').count())()
        riders_prev = await sync_to_async(lambda: prev_users_qs.filter(groups__name='Rider').count())()
        drivers_prev = await sync_to_async(lambda: prev_users_qs.filter(groups__name='Driver').count())()

        # Orders & revenue approximation
        orders_qs = Order.objects.filter(created_at__range=(dt_from, dt_to))
        prev_orders_qs = Order.objects.filter(created_at__range=(prev_from, prev_to))

        orders_current = await sync_to_async(orders_qs.count)()
        orders_prev = await sync_to_async(prev_orders_qs.count)()

        completed_current = await sync_to_async(lambda: orders_qs.filter(status=Order.OrderStatus.COMPLETED).count())()
        completed_prev = await sync_to_async(lambda: prev_orders_qs.filter(status=Order.OrderStatus.COMPLETED).count())()

        # Revenue: sum of final stop prices (adjusted -> calculated -> original)
        price_expr = Coalesce(
            'adjusted_price',
            'calculated_price',
            'original_price',
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        def _calc_revenue(d_from, d_to):
            return (
                OrderItem.objects.filter(
                    order__created_at__range=(d_from, d_to),
                    is_final_stop=True,
                ).aggregate(
                    total=Coalesce(
                        Sum(price_expr, output_field=DecimalField(max_digits=14, decimal_places=2)),
                        Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
                    )
                ).get('total')
                or 0
            )

        revenue_current = await sync_to_async(_calc_revenue)(dt_from, dt_to)
        revenue_prev = await sync_to_async(_calc_revenue)(prev_from, prev_to)

        # Monthly target (defaults; can be wired to DB later)
        monthly_target = float(getattr(request, 'ADMIN_MONTHLY_TARGET', 20000) or 20000)
        revenue_target = float(getattr(request, 'ADMIN_MONTHLY_REVENUE_TARGET', 20000) or 20000)
        # Progress: revenue vs target within current calendar month (not filtered range)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        def _calc_month_revenue(start_dt):
            return (
                OrderItem.objects.filter(order__created_at__gte=start_dt, is_final_stop=True)
                .aggregate(
                    total=Coalesce(
                        Sum(price_expr, output_field=DecimalField(max_digits=14, decimal_places=2)),
                        Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
                    )
                )
                .get('total')
                or 0
            )

        month_revenue = await sync_to_async(_calc_month_revenue)(month_start)
        month_revenue = float(month_revenue)
        month_progress_pct = round((month_revenue / revenue_target) * 100.0, 2) if revenue_target else 0.0

        # Charts (time series)
        trunc = TruncDay('created_at') if interval == 'day' else TruncMonth('created_at')
        orders_series_qs = (
            Order.objects.filter(created_at__range=(dt_from, dt_to))
            .annotate(bucket=trunc)
            .values('bucket')
            .annotate(value=Count('id'))
            .order_by('bucket')
        )
        riders_series_qs = (
            CustomUser.objects.filter(created_at__range=(dt_from, dt_to), groups__name='Rider')
            .annotate(bucket=trunc)
            .values('bucket')
            .annotate(value=Count('id'))
            .order_by('bucket')
        )
        drivers_series_qs = (
            CustomUser.objects.filter(created_at__range=(dt_from, dt_to), groups__name='Driver')
            .annotate(bucket=trunc)
            .values('bucket')
            .annotate(value=Count('id'))
            .order_by('bucket')
        )

        orders_series = await sync_to_async(list)(orders_series_qs)
        riders_series = await sync_to_async(list)(riders_series_qs)
        drivers_series = await sync_to_async(list)(drivers_series_qs)

        def _month_start(d):
            return d.replace(day=1)

        def _next_month(d):
            # d is a date with day=1
            if d.month == 12:
                return d.replace(year=d.year + 1, month=1, day=1)
            return d.replace(month=d.month + 1, day=1)

        def _date_range_days(d1, d2):
            # inclusive, dates
            cur = d1
            while cur <= d2:
                yield cur
                cur = cur + timezone.timedelta(days=1)

        def _date_range_months(d1, d2):
            # inclusive month buckets; d1/d2 are dates
            cur = _month_start(d1)
            end = _month_start(d2)
            while cur <= end:
                yield cur
                cur = _next_month(cur)

        def _fill_series(raw_rows):
            """
            raw_rows: list of {bucket: datetime, value: int}
            returns dense list [{x, y}] covering all buckets in [date_from, date_to]
            """
            bucket_map = {}
            for r in raw_rows:
                b = r.get('bucket')
                if b:
                    key = b.date() if hasattr(b, 'date') else b
                    bucket_map[key] = int(r.get('value') or 0)

            if interval == 'day':
                points = []
                for d in _date_range_days(date_from, date_to):
                    points.append({'x': d.strftime('%Y-%m-%d'), 'y': bucket_map.get(d, 0)})
                return points

            points = []
            for d in _date_range_months(date_from, date_to):
                points.append({'x': d.strftime('%Y-%m'), 'y': bucket_map.get(d, 0)})
            return points

        def _fmt_bucket(b):
            if not b:
                return None
            if interval == 'day':
                return b.strftime('%Y-%m-%d')
            return b.strftime('%Y-%m')

        # Recent orders table
        try:
            recent_limit = int(request.query_params.get('recent_limit') or 10)
        except Exception:
            recent_limit = 10
        recent_limit = max(1, min(recent_limit, 50))

        recent_orders_qs = (
            Order.objects.select_related('user')
            .prefetch_related('order_items')
            .order_by('-created_at')[:recent_limit]
        )
        recent_orders = await sync_to_async(list)(recent_orders_qs)
        recent_rows = []
        for o in recent_orders:
            items = list(getattr(o, 'order_items', []).all()) if hasattr(o, 'order_items') else []
            total_price = 0.0
            for it in items:
                total_price += float(getattr(it, 'adjusted_price', None) or getattr(it, 'calculated_price', None) or getattr(it, 'original_price', 0) or 0)
            recent_rows.append(
                {
                    'id': o.id,
                    'order_code': o.order_code,
                    'status': o.status,
                    'created_at': o.created_at,
                    'user_email': getattr(o.user, 'email', None),
                    'total_price': round(total_price, 2),
                }
            )

        data = {
            'filters': {
                'date_from': str(date_from),
                'date_to': str(date_to),
                'interval': interval,
            },
            'kpis': {
                'riders_added': {
                    'current': riders_current,
                    'previous': riders_prev,
                    'change_percent': _pct_change(riders_current, riders_prev),
                },
                'drivers_added': {
                    'current': drivers_current,
                    'previous': drivers_prev,
                    'change_percent': _pct_change(drivers_current, drivers_prev),
                },
                'orders_created': {
                    'current': orders_current,
                    'previous': orders_prev,
                    'change_percent': _pct_change(orders_current, orders_prev),
                },
                'orders_completed': {
                    'current': completed_current,
                    'previous': completed_prev,
                    'change_percent': _pct_change(completed_current, completed_prev),
                },
                'revenue': {
                    'current': float(revenue_current),
                    'previous': float(revenue_prev),
                    'change_percent': _pct_change(revenue_current, revenue_prev),
                },
            },
            'monthly_target': {
                'target': monthly_target,
                'revenue_target': revenue_target,
                'revenue_current_month': month_revenue,
                'progress_percent': month_progress_pct,
            },
            'charts': {
                'orders': _fill_series(orders_series),
                'riders': _fill_series(riders_series),
                'drivers': _fill_series(drivers_series),
            },
            'recent_orders': recent_rows,
        }

        return Response(
            {'message': 'Analytics dashboard retrieved successfully', 'status': 'success', 'data': data},
            status=status.HTTP_200_OK,
        )


class _AdminPanelSuperuserView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def _forbidden_response(self):
        return Response(
            {
                'message': 'Only superusers can access admin panel APIs.',
                'status': 'error',
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class AdminPanelDriverVerificationListView(_AdminPanelSuperuserView):
    @extend_schema(tags=['Admin Panel'], summary='Driver verification list', responses=AdminPanelDriverVerificationSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        qs = DriverVerification.objects.select_related('user', 'reviewer').order_by('-updated_at')
        rows = await sync_to_async(list)(qs)
        data = await sync_to_async(lambda: AdminPanelDriverVerificationSerializer(rows, many=True).data)()
        return Response({'message': 'Driver verifications retrieved successfully', 'status': 'success', 'count': len(data), 'data': data}, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Admin Panel'],
        summary='Create driver verification',
        request=AdminPanelDriverVerificationWriteSerializer,
        responses=AdminPanelDriverVerificationSerializer,
    )
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        serializer = AdminPanelDriverVerificationWriteSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        instance = await sync_to_async(serializer.save)(reviewer=request.user)
        out = AdminPanelDriverVerificationSerializer(instance)
        data = await sync_to_async(lambda: out.data)()
        return Response({'message': 'Driver verification created successfully', 'status': 'success', 'data': data}, status=status.HTTP_201_CREATED)


class AdminPanelDriverVerificationDetailView(_AdminPanelSuperuserView):
    @extend_schema(tags=['Admin Panel'], summary='Driver verification detail', responses=AdminPanelDriverVerificationSerializer)
    async def get(self, request, verification_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        row = await sync_to_async(lambda: DriverVerification.objects.select_related('user', 'reviewer').filter(id=verification_id).first())()
        if not row:
            return Response({'message': 'Driver verification not found.', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        data = await sync_to_async(lambda: AdminPanelDriverVerificationSerializer(row).data)()
        return Response({'message': 'Driver verification retrieved successfully', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Admin Panel'],
        summary='Update driver verification',
        request=AdminPanelDriverVerificationWriteSerializer,
        responses=AdminPanelDriverVerificationSerializer,
    )
    async def patch(self, request, verification_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        row = await sync_to_async(lambda: DriverVerification.objects.filter(id=verification_id).first())()
        if not row:
            return Response({'message': 'Driver verification not found.', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminPanelDriverVerificationWriteSerializer(row, data=request.data, partial=True)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        instance = await sync_to_async(serializer.save)(reviewer=request.user)
        out = AdminPanelDriverVerificationSerializer(instance)
        data = await sync_to_async(lambda: out.data)()
        return Response({'message': 'Driver verification updated successfully', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)

    @extend_schema(tags=['Admin Panel'], summary='Delete driver verification')
    async def delete(self, request, verification_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        row = await sync_to_async(lambda: DriverVerification.objects.filter(id=verification_id).first())()
        if not row:
            return Response({'message': 'Driver verification not found.', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        try:
            await sync_to_async(row.delete)()
        except IntegrityError:
            return Response(
                {'message': 'Cannot delete: object is referenced by other records.', 'status': 'error'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({'message': 'Driver verification deleted successfully', 'status': 'success'}, status=status.HTTP_200_OK)


class _AdminPanelModelListView(_AdminPanelSuperuserView):
    model = None
    serializer_class = None
    not_found_message = 'Object not found.'
    success_list_message = 'Items retrieved successfully'
    success_detail_message = 'Item retrieved successfully'
    write_serializer_class = None
    display_type_value = None

    def get_queryset(self):
        return self.model.objects.order_by('-created_at')

    async def _get_list(self, request):
        qs = self.get_queryset()
        rows = await sync_to_async(list)(qs)
        serializer = self.serializer_class(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response({'message': self.success_list_message, 'status': 'success', 'count': len(data), 'data': data}, status=status.HTTP_200_OK)

    async def _get_detail(self, request, pk):
        row = await sync_to_async(lambda: self.get_queryset().filter(id=pk).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(row, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response({'message': self.success_detail_message, 'status': 'success', 'data': data}, status=status.HTTP_200_OK)

    async def _create(self, request):
        serializer = self.write_serializer_class(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        save_kwargs = {'display_type': self.display_type_value} if self.display_type_value else {}
        instance = await sync_to_async(serializer.save)(**save_kwargs)
        output = self.serializer_class(instance, context={'request': request})
        data = await sync_to_async(lambda: output.data)()
        return Response({'message': 'Created successfully', 'status': 'success', 'data': data}, status=status.HTTP_201_CREATED)

    async def _update(self, request, pk):
        row = await sync_to_async(lambda: self.model.objects.filter(id=pk).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.write_serializer_class(row, data=request.data, partial=True)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        save_kwargs = {'display_type': self.display_type_value} if self.display_type_value else {}
        instance = await sync_to_async(serializer.save)(**save_kwargs)
        output = self.serializer_class(instance, context={'request': request})
        data = await sync_to_async(lambda: output.data)()
        return Response({'message': 'Updated successfully', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)


class AdminPanelUploadTypesListView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationUploadType.objects.prefetch_related('items', 'items__question_answers').order_by('-created_at')

    model = DriverIdentificationUploadType
    serializer_class = AdminPanelUploadTypeSerializer
    write_serializer_class = AdminPanelUploadTypeWriteSerializer
    success_list_message = 'Upload identification types retrieved successfully'
    display_type_value = 'upload'

    @extend_schema(tags=['Admin Panel'], summary='Upload driver identification list', responses=AdminPanelUploadTypeSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_list(request)

    @extend_schema(tags=['Admin Panel'], summary='Create upload identification type', request=AdminPanelUploadTypeWriteSerializer, responses=AdminPanelUploadTypeSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminPanelUploadTypesDetailView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationUploadType.objects.prefetch_related('items', 'items__question_answers').order_by('-created_at')

    model = DriverIdentificationUploadType
    serializer_class = AdminPanelUploadTypeSerializer
    write_serializer_class = AdminPanelUploadTypeWriteSerializer
    not_found_message = 'Upload identification type not found.'
    success_detail_message = 'Upload identification type retrieved successfully'

    @extend_schema(tags=['Admin Panel'], summary='Upload driver identification detail', responses=AdminPanelUploadTypeSerializer)
    async def get(self, request, upload_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_detail(request, upload_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Update upload identification type', request=AdminPanelUploadTypeWriteSerializer, responses=AdminPanelUploadTypeSerializer)
    async def patch(self, request, upload_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, upload_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Delete upload identification type')
    async def delete(self, request, upload_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        row = await sync_to_async(lambda: self.model.objects.filter(id=upload_type_id).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        try:
            await sync_to_async(row.delete)()
        except IntegrityError:
            return Response(
                {'message': 'Cannot delete: object is referenced by other records.', 'status': 'error'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({'message': 'Upload identification type deleted successfully', 'status': 'success'}, status=status.HTTP_200_OK)


class AdminPanelLegalTypesListView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationLegalType.objects.prefetch_related('agreement_items').order_by('-created_at')

    model = DriverIdentificationLegalType
    serializer_class = AdminPanelLegalTypeSerializer
    write_serializer_class = AdminPanelLegalTypeWriteSerializer
    success_list_message = 'Legal identification types retrieved successfully'
    display_type_value = 'legal'

    @extend_schema(tags=['Admin Panel'], summary='Legal driver identification list', responses=AdminPanelLegalTypeSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_list(request)

    @extend_schema(tags=['Admin Panel'], summary='Create legal identification type', request=AdminPanelLegalTypeWriteSerializer, responses=AdminPanelLegalTypeSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminPanelLegalTypesDetailView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationLegalType.objects.prefetch_related('agreement_items').order_by('-created_at')

    model = DriverIdentificationLegalType
    serializer_class = AdminPanelLegalTypeSerializer
    write_serializer_class = AdminPanelLegalTypeWriteSerializer
    not_found_message = 'Legal identification type not found.'
    success_detail_message = 'Legal identification type retrieved successfully'

    @extend_schema(tags=['Admin Panel'], summary='Legal driver identification detail', responses=AdminPanelLegalTypeSerializer)
    async def get(self, request, legal_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_detail(request, legal_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Update legal identification type', request=AdminPanelLegalTypeWriteSerializer, responses=AdminPanelLegalTypeSerializer)
    async def patch(self, request, legal_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, legal_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Delete legal identification type')
    async def delete(self, request, legal_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        row = await sync_to_async(lambda: self.model.objects.filter(id=legal_type_id).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        try:
            await sync_to_async(row.delete)()
        except IntegrityError:
            return Response(
                {'message': 'Cannot delete: object is referenced by other records.', 'status': 'error'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({'message': 'Legal identification type deleted successfully', 'status': 'success'}, status=status.HTTP_200_OK)


class AdminPanelRegistrationTypesListView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationRegistrationType.objects.prefetch_related('agreement_items').order_by('-created_at')

    model = DriverIdentificationRegistrationType
    serializer_class = AdminPanelRegistrationTypeSerializer
    write_serializer_class = AdminPanelRegistrationTypeWriteSerializer
    success_list_message = 'Registration identification types retrieved successfully'
    display_type_value = 'registration'

    @extend_schema(tags=['Admin Panel'], summary='Registration driver identification list', responses=AdminPanelRegistrationTypeSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_list(request)

    @extend_schema(tags=['Admin Panel'], summary='Create registration identification type', request=AdminPanelRegistrationTypeWriteSerializer, responses=AdminPanelRegistrationTypeSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminPanelRegistrationTypesDetailView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationRegistrationType.objects.prefetch_related('agreement_items').order_by('-created_at')

    model = DriverIdentificationRegistrationType
    serializer_class = AdminPanelRegistrationTypeSerializer
    write_serializer_class = AdminPanelRegistrationTypeWriteSerializer
    not_found_message = 'Registration identification type not found.'
    success_detail_message = 'Registration identification type retrieved successfully'

    @extend_schema(tags=['Admin Panel'], summary='Registration driver identification detail', responses=AdminPanelRegistrationTypeSerializer)
    async def get(self, request, registration_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_detail(request, registration_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Update registration identification type', request=AdminPanelRegistrationTypeWriteSerializer, responses=AdminPanelRegistrationTypeSerializer)
    async def patch(self, request, registration_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, registration_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Delete registration identification type')
    async def delete(self, request, registration_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        row = await sync_to_async(lambda: self.model.objects.filter(id=registration_type_id).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        try:
            await sync_to_async(row.delete)()
        except IntegrityError:
            return Response(
                {'message': 'Cannot delete: object is referenced by other records.', 'status': 'error'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({'message': 'Registration identification type deleted successfully', 'status': 'success'}, status=status.HTTP_200_OK)


class AdminPanelTermsTypesListView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationTermsType.objects.prefetch_related('agreement_items').order_by('-created_at')

    model = DriverIdentificationTermsType
    serializer_class = AdminPanelTermsTypeSerializer
    write_serializer_class = AdminPanelTermsTypeWriteSerializer
    success_list_message = 'Terms identification types retrieved successfully'
    display_type_value = 'terms'

    @extend_schema(tags=['Admin Panel'], summary='Terms driver identification list', responses=AdminPanelTermsTypeSerializer(many=True))
    async def get(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_list(request)

    @extend_schema(tags=['Admin Panel'], summary='Create terms identification type', request=AdminPanelTermsTypeWriteSerializer, responses=AdminPanelTermsTypeSerializer)
    async def post(self, request):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._create(request)


class AdminPanelTermsTypesDetailView(_AdminPanelModelListView):
    def get_queryset(self):
        return DriverIdentificationTermsType.objects.prefetch_related('agreement_items').order_by('-created_at')

    model = DriverIdentificationTermsType
    serializer_class = AdminPanelTermsTypeSerializer
    write_serializer_class = AdminPanelTermsTypeWriteSerializer
    not_found_message = 'Terms identification type not found.'
    success_detail_message = 'Terms identification type retrieved successfully'

    @extend_schema(tags=['Admin Panel'], summary='Terms driver identification detail', responses=AdminPanelTermsTypeSerializer)
    async def get(self, request, terms_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._get_detail(request, terms_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Update terms identification type', request=AdminPanelTermsTypeWriteSerializer, responses=AdminPanelTermsTypeSerializer)
    async def patch(self, request, terms_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        return await self._update(request, terms_type_id)

    @extend_schema(tags=['Admin Panel'], summary='Delete terms identification type')
    async def delete(self, request, terms_type_id):
        if not request.user.is_superuser:
            return self._forbidden_response()
        row = await sync_to_async(lambda: self.model.objects.filter(id=terms_type_id).first())()
        if not row:
            return Response({'message': self.not_found_message, 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        try:
            await sync_to_async(row.delete)()
        except IntegrityError:
            return Response(
                {'message': 'Cannot delete: object is referenced by other records.', 'status': 'error'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({'message': 'Terms identification type deleted successfully', 'status': 'success'}, status=status.HTTP_200_OK)
