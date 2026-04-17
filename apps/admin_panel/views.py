from asgiref.sync import sync_to_async
from django.contrib.auth.models import Group
from django.db.models import Q
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

from .serializers import (
    AdminPanelDriverListSerializer,
    AdminPanelRiderListSerializer,
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
