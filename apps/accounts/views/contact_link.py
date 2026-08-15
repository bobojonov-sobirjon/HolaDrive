from asgiref.sync import sync_to_async
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.views import AsyncAPIView

from ..contact_link import ContactLinkError, confirm_contact_link, request_contact_link
from ..driver_readiness import build_driver_readiness
from ..models import CustomUser
from ..serializers.contact_link import ContactLinkConfirmSerializer, ContactLinkRequestSerializer
from ..serializers.user import UserDetailSerializer


class ContactLinkRequestView(AsyncAPIView):
    """
    POST /api/v1/accounts/me/contact/request/
    Send OTP to a new email or phone to link it to the current account.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['User'],
        summary='Request link email or phone (OTP)',
        description=(
            'Send a verification code to **either** a new `email` **or** `phone_number` '
            '(any country, E.164). After the user enters the code, call '
            '`POST /me/contact/confirm/` to attach it to this account.\n\n'
            'Fails if the contact is already used by another account.'
        ),
        request=ContactLinkRequestSerializer,
        examples=[
            OpenApiExample('Link phone', value={'phone_number': '+998901234567'}, request_only=True),
            OpenApiExample('Link email', value={'email': 'driver@example.com'}, request_only=True),
        ],
    )
    async def post(self, request):
        ser = ContactLinkRequestSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        vd = ser.validated_data

        def _run():
            u = CustomUser.objects.get(pk=request.user.pk)
            return request_contact_link(
                user=u,
                email=vd.get('email'),
                phone_number=vd.get('phone_number'),
            )

        try:
            data = await sync_to_async(_run)()
        except ContactLinkError as exc:
            errors = {exc.field: [str(exc)]} if exc.field else {'non_field_errors': [str(exc)]}
            return Response(
                {
                    'message': str(exc),
                    'status': 'error',
                    'code': exc.code,
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'message': 'Verification code sent',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class ContactLinkConfirmView(AsyncAPIView):
    """
    POST /api/v1/accounts/me/contact/confirm/
    Confirm OTP and attach email or phone to the account.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['User'],
        summary='Confirm link email or phone (OTP)',
        description='Verify the code from `/me/contact/request/` and save email or phone on the user.',
        request=ContactLinkConfirmSerializer,
        examples=[
            OpenApiExample(
                'Confirm phone',
                value={'phone_number': '+998901234567', 'code': '1234'},
                request_only=True,
            ),
            OpenApiExample(
                'Confirm email',
                value={'email': 'driver@example.com', 'code': '1234'},
                request_only=True,
            ),
        ],
    )
    async def post(self, request):
        ser = ContactLinkConfirmSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        vd = ser.validated_data

        def _run():
            u = CustomUser.objects.get(pk=request.user.pk)
            return confirm_contact_link(
                user=u,
                code=vd['code'],
                email=vd.get('email'),
                phone_number=vd.get('phone_number'),
            )

        try:
            user = await sync_to_async(_run)()
        except ContactLinkError as exc:
            errors = {exc.field: [str(exc)]} if exc.field else {'non_field_errors': [str(exc)]}
            return Response(
                {
                    'message': str(exc),
                    'status': 'error',
                    'code': exc.code,
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = await CustomUser.objects.prefetch_related('groups').aget(pk=user.pk)
        payload = await sync_to_async(lambda: UserDetailSerializer(user, context={'request': request}).data)()
        return Response(
            {
                'message': 'Contact linked successfully',
                'status': 'success',
                'data': payload,
            },
            status=status.HTTP_200_OK,
        )


class DriverReadinessView(AsyncAPIView):
    """
    GET /api/v1/accounts/driver/readiness/
    Each onboarding step as true/false + ready_for_rides.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Driver Preferences'],
        summary='Driver readiness checklist',
        description=(
            'Returns true/false for each driver setup step:\n'
            '- `profile`, `profile_photo`, `identification`, `registration_terms`, '
            '`preferences`, `vehicle`, `pin`, `bank_account`\n'
            '- `ready_for_rides` is true only when all **required** steps pass '
            '(profile, identification approved, preferences, vehicle, bank_account).\n'
            '- When a step is false, use `incomplete_actions[step]` for navigation.\n'
            '- For profile: `details.profile.missing_fields` + `details.profile.actions` '
            'list exactly which fields to fill and which API/screen to open.'
        ),
    )
    async def get(self, request):
        def _run():
            u = CustomUser.objects.prefetch_related('groups').get(pk=request.user.pk)
            return build_driver_readiness(u)

        data = await sync_to_async(_run)()
        if not data.get('is_driver'):
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                    'data': data,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                'message': 'Driver readiness retrieved',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )
