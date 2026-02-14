from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from ..serializers import (
    DriverVerificationSerializer,
    DriverIdentificationSerializer,
)
from ..models import (
    DriverVerification,
    DriverIdentification,
    DriverIdentificationUploadDocument,
)

class DriverVerificationBaseView(AsyncAPIView):
    """
    Base class with helper to ensure user is a Driver.
    """

    permission_classes = [IsAuthenticated]

    async def check_driver_permission(self, request):
        """
        Allow only users in Driver group.
        """
        user = request.user
        groups = await sync_to_async(list)(user.groups.all())
        group_names = [g.name for g in groups]
        if 'Driver' not in group_names:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

class DriverVerificationDetailView(DriverVerificationBaseView):
    """
    GET /api/accounts/driver/verification/<id>/

    Returns driver verification details plus DriverIdentification
    and DriverIdentificationItems for the current user.
    """

    @extend_schema(tags=['Driver Verification'], summary='Get verification detail', description='Get detailed driver verification (verification + identifications). Role: Driver.')
    async def get(self, request, pk):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        # Get verification (ensure it belongs to current user)
        try:
            verification = await DriverVerification.objects.select_related('user').aget(
                pk=pk,
                user=user,
            )
        except DriverVerification.DoesNotExist:
            return Response(
                {
                    'message': 'Driver verification not found',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Serialize verification
        ver_serializer = DriverVerificationSerializer(verification)
        ver_data = await sync_to_async(lambda: ver_serializer.data)()

        # Get all active identifications with items
        identifications = await sync_to_async(list)(
            DriverIdentification.objects.filter(is_active=True)
            .prefetch_related('items')
            .order_by('id')
        )
        ident_serializer = DriverIdentificationSerializer(
            identifications,
            many=True,
            context={'request': request},
        )
        ident_data = await sync_to_async(lambda: ident_serializer.data)()

        return Response(
            {
                'message': 'Driver verification detail retrieved successfully',
                'status': 'success',
                'data': {
                    'verification': ver_data,
                    'identifications': ident_data,
                },
            },
            status=status.HTTP_200_OK,
        )

class DriverVerificationMeView(DriverVerificationBaseView):
    """
    GET /api/accounts/driver/verification/

    Returns verification info for the authenticated driver (if exists),
    or a default NOT_SUBMITTED object.
    """

    @extend_schema(tags=['Driver Verification'], summary='My verification', description='Get verification status for the authenticated driver (or NOT_SUBMITTED). Role: Driver.')
    async def get(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        def get_verification():
            return DriverVerification.objects.filter(user=user).first()

        verification = await sync_to_async(get_verification)()

        if not verification:
            # Create lightweight representation with NOT_SUBMITTED
            data = {
                'id': None,
                'status': DriverVerification.Status.NOT_SUBMITTED,
                'status_display': DriverVerification.Status.NOT_SUBMITTED.label,
                'estimated_review_hours': 0,
                'comment': None,
                'reviewer': None,
                'reviewed_at': None,
                'created_at': None,
                'updated_at': None,
            }
        else:
            serializer = DriverVerificationSerializer(verification)
            data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Driver verification status retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

class DriverVerificationSubmitView(DriverVerificationBaseView):
    """
    POST /api/accounts/driver/verification/submit/

    Checks that the driver has uploaded documents for all active
    DriverIdentification types. If everything is complete,
    creates or updates DriverVerification with status = IN_REVIEW.
    """

    @extend_schema(tags=['Driver Verification'], summary='Submit for review', description='Submit driver verification. All required documents must be uploaded. Sets status IN_REVIEW. Role: Driver.')
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        # 1) Get all active identifications
        active_identifications = await sync_to_async(list)(
            DriverIdentification.objects.filter(is_active=True)
            .values('id', 'name', 'title')
        )
        active_ids = {item['id'] for item in active_identifications}

        # 2) Get uploads for this user
        user_uploads = await sync_to_async(list)(
            DriverIdentificationUploadDocument.objects.filter(user=user)
            .values_list('driver_identification_id', flat=True)
        )
        uploaded_ids = set(user_uploads)

        # 3) Find missing identifications
        missing = [
            item for item in active_identifications
            if item['id'] not in uploaded_ids
        ]

        if missing:
            return Response(
                {
                    'message': 'Some required documents are missing',
                    'status': 'error',
                    'missing_documents': missing,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) Create or update DriverVerification
        def get_or_create_verification():
            obj, created = DriverVerification.objects.get_or_create(
                user=user,
                defaults={'status': DriverVerification.Status.IN_REVIEW},
            )
            if not created and obj.status != DriverVerification.Status.IN_REVIEW:
                obj.status = DriverVerification.Status.IN_REVIEW
                obj.comment = ''
                obj.save(update_fields=['status', 'comment', 'updated_at'])
            return obj

        verification = await sync_to_async(get_or_create_verification)()

        serializer = DriverVerificationSerializer(verification)
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Submitted for review',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

class DriverVerificationSubmitView(DriverVerificationBaseView):
    """
    POST /api/accounts/driver/verification/submit/

    Checks that the driver has uploaded documents for all active
    DriverIdentification types. If everything is complete,
    creates or updates DriverVerification with status = IN_REVIEW.
    """

    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        # 1) All active identifications
        active_identifications = await sync_to_async(list)(
            DriverIdentification.objects.filter(is_active=True)
            .values('id', 'name')
        )
        active_map = {item['id']: item['name'] for item in active_identifications}

        if not active_map:
            return Response(
                {
                    'message': 'No active driver identifications configured',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) User uploads for active identifications
        user_uploads = await sync_to_async(list)(
            DriverIdentificationUploadDocument.objects.filter(
                user=user,
                driver_identification_id__in=list(active_map.keys()),
            ).values_list('driver_identification_id', flat=True)
        )
        uploaded_ids = set(user_uploads)

        missing = [
            {'id': ident_id, 'name': ident_name}
            for ident_id, ident_name in active_map.items()
            if ident_id not in uploaded_ids
        ]

        if missing:
            return Response(
                {
                    'message': 'Some required documents are missing',
                    'status': 'error',
                    'missing_documents': missing,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) Create or update DriverVerification
        def get_or_create_verification():
            verification, created = DriverVerification.objects.get_or_create(
                user=user,
                defaults={
                    'status': DriverVerification.Status.IN_REVIEW,
                },
            )
            if not created and verification.status != DriverVerification.Status.IN_REVIEW:
                verification.status = DriverVerification.Status.IN_REVIEW
                verification.comment = ''
                verification.save(update_fields=['status', 'comment', 'updated_at'])
            return verification

        verification = await sync_to_async(get_or_create_verification)()
        serializer = DriverVerificationSerializer(verification)
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Driver verification submitted successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

