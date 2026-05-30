import logging
import os

from asgiref.sync import sync_to_async
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.firebase import verify_firebase_id_token
from apps.common.throttles import LoginRateThrottle
from apps.common.views import AsyncAPIView

from ..serializers.social_auth import FirebaseSocialSignInSerializer
from ..firebase_social_auth import SocialAuthError, get_or_create_user_from_firebase

logger = logging.getLogger(__name__)


def _user_payload(user) -> dict:
    groups = list(user.groups.values('id', 'name'))
    return {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'full_name': user.get_full_name(),
        'is_verified': user.is_verified,
        'firebase_uid': user.firebase_uid,
        'groups': groups,
    }


class FirebaseSocialSignInView(AsyncAPIView):
    """
    Base view: verify Firebase ID token and return JWT pair.
    Subclasses set `provider` to google | apple | facebook.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    provider: str = ''

    async def post(self, request):
        serializer = FirebaseSocialSignInSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = await sync_to_async(lambda: serializer.validated_data)()
        id_token = data['id_token']
        role = (data.get('role') or '').strip() or None
        full_name = (data.get('full_name') or '').strip() or None
        device_token = (data.get('device_token') or '').strip()
        device_type = data.get('device_type')

        try:
            claims = await sync_to_async(verify_firebase_id_token)(id_token)
        except RuntimeError:
            return Response(
                {
                    'message': 'Firebase is not configured on the server',
                    'status': 'error',
                    'errors': {'firebase': ['Missing or invalid FIREBASE_* environment variables']},
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValueError as exc:
            return Response(
                {'message': str(exc), 'status': 'error', 'errors': {'id_token': [str(exc)]}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user, is_new_user = await sync_to_async(get_or_create_user_from_firebase)(
                claims,
                expected_provider=self.provider,
                role=role,
                device_token=device_token,
                device_type=device_type,
                full_name=full_name,
            )
        except SocialAuthError as exc:
            status_code = status.HTTP_409_CONFLICT if exc.code == 'email_linked_other_firebase' else status.HTTP_400_BAD_REQUEST
            return Response(
                {
                    'message': str(exc),
                    'status': 'error',
                    'errors': {exc.code: [str(exc)]},
                },
                status=status_code,
            )

        if not user.is_active:
            return Response(
                {
                    'message': 'Account is disabled',
                    'status': 'error',
                    'errors': {'account': ['This account has been deactivated.']},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = await sync_to_async(RefreshToken.for_user)(user)
        project_id = os.getenv('FIREBASE_PROJECT_ID')

        return Response(
            {
                'message': 'Signed in successfully' if not is_new_user else 'Account created and signed in',
                'status': 'success',
                'data': {
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'is_new_user': is_new_user,
                    'provider': self.provider,
                    'firebase_project_id': project_id,
                    'user': await sync_to_async(_user_payload)(user),
                },
            },
            status=status.HTTP_200_OK,
        )


class GoogleSignInView(FirebaseSocialSignInView):
    provider = 'google'

    @extend_schema(
        tags=['Authentication'],
        summary='Sign in with Google (Firebase)',
        description=(
            '**Flow:** Mobile app signs in with Google through **Firebase Authentication**, '
            'then sends the Firebase **ID token** (`id_token`) to this endpoint.\n\n'
            'The server verifies the token with Firebase Admin SDK and returns **JWT** '
            '`access_token` / `refresh_token` (same as `verify-code`).\n\n'
            'On first sign-in, creates a user with `is_verified=true`. '
            'Optional `role`: `rider` or `driver` (assigns Rider/Driver group).'
        ),
        request=FirebaseSocialSignInSerializer,
        examples=[
            OpenApiExample(
                'Google sign-in',
                value={
                    'id_token': '<firebase_id_token_from_google>',
                    'role': 'rider',
                    'device_token': 'fcm-token',
                    'device_type': 'android',
                },
                request_only=True,
            ),
        ],
    )
    async def post(self, request):
        return await super().post(request)


class AppleSignInView(FirebaseSocialSignInView):
    provider = 'apple'

    @extend_schema(
        tags=['Authentication'],
        summary='Sign in with Apple (Firebase)',
        description=(
            'Same as Google: use Firebase Auth **Sign in with Apple** on the client, '
            'then POST the Firebase **ID token** here. '
            'Apple may hide email on repeat logins — account is keyed by Firebase `uid`.'
        ),
        request=FirebaseSocialSignInSerializer,
    )
    async def post(self, request):
        return await super().post(request)


class FacebookSignInView(FirebaseSocialSignInView):
    provider = 'facebook'

    @extend_schema(
        tags=['Authentication'],
        summary='Sign in with Facebook (Firebase)',
        description=(
            'Same as Google: use Firebase Auth **Facebook** on the client, '
            'then POST the Firebase **ID token** here.'
        ),
        request=FirebaseSocialSignInSerializer,
    )
    async def post(self, request):
        return await super().post(request)
