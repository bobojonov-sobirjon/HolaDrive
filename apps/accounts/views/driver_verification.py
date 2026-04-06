from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import OpenApiResponse, extend_schema

from ..serializers.driver_verification import DriverVerificationSerializer
from ..models import DriverVerification


class DriverVerificationBaseView(AsyncAPIView):
    """Base: authenticated; helpers for Driver-only endpoints."""

    permission_classes = [IsAuthenticated]

    async def check_driver_permission(self, request):
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


class DriverVerificationCompletedIdentificationView(DriverVerificationBaseView):
    """
    GET/POST /api/v1/accounts/driver/identification/completed/
    GET: list this driver's DriverVerification rows (0 or 1).
    POST: ensure row exists with status NOT_SUBMITTED.
    """

    @extend_schema(
        tags=['Completed Identification'],
        summary='List my verification (identification completion)',
        description=(
            'Returns all **`DriverVerification`** records for **`request.user`** in this flow. '
            'Because verification is one-to-one with the user, the list is typically **empty** until '
            'you call the POST endpoint, or contains **one** object.\n\n'
            '**Role:** Driver (JWT).'
        ),
        responses={
            200: OpenApiResponse(
                response=DriverVerificationSerializer(many=True),
                description='Verification rows for the current driver.',
            ),
        },
    )
    async def get(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        def load():
            return list(
                DriverVerification.objects.filter(user=user).order_by('-updated_at'),
            )

        rows = await sync_to_async(load)()
        serializer = DriverVerificationSerializer(rows, many=True)
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Completed identification list retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Completed Identification'],
        summary='Mark identification checklist finished',
        description=(
            'Creates or updates **`DriverVerification`** for **`request.user`** with '
            '**`status=not_submitted`**. Use when the driver has finished the in-app identification '
            'steps before staff review.\n\n'
            '**Role:** Driver (JWT). No request body.'
        ),
        request=None,
        responses={200: DriverVerificationSerializer},
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        def upsert():
            verification, _ = DriverVerification.objects.update_or_create(
                user=user,
                defaults={'status': DriverVerification.Status.NOT_SUBMITTED},
            )
            return verification

        verification = await sync_to_async(upsert)()
        serializer = DriverVerificationSerializer(verification)
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Identification completion recorded successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DriverVerificationCompletedIdentificationDetailView(DriverVerificationBaseView):
    """
    GET /api/v1/accounts/driver/identification/completed/<id>/
    """

    @extend_schema(
        tags=['Completed Identification'],
        summary='Get verification by id (identification completion)',
        description=(
            'Returns one **`DriverVerification`** record when **`id`** belongs to **`request.user`**. '
            'Otherwise **404**.\n\n'
            '**Role:** Driver (JWT).'
        ),
        responses={
            200: DriverVerificationSerializer,
            404: OpenApiResponse(description='Not found or not your record.'),
        },
    )
    async def get(self, request, pk):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

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

        serializer = DriverVerificationSerializer(verification)
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Completed identification detail retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )
