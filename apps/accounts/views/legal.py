from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from apps.common.views import AsyncAPIView
from ..models import LegalPage, AcceptanceOfAgreement
from ..serializers.legal import (
    LegalPageSerializer,
    AcceptanceOfAgreementSerializer,
    AcceptanceOfAgreementCreateSerializer,
)


class LegalPageListView(AsyncAPIView):
    """
    GET list of legal pages (Privacy Policy, Terms of Service, etc.)
    Public endpoint - no auth required.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=['Legal'], summary='Legal pages list', description='Get list of legal pages (Privacy Policy, Terms of Service). Returns name and link for each.')
    async def get(self, request):
        def _get_list():
            return list(LegalPage.objects.filter(is_active=True).order_by('name'))
        items = await sync_to_async(_get_list)()
        serializer = LegalPageSerializer(items, many=True)
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Legal pages retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK
        )


class AcceptanceOfAgreementCreateView(AsyncAPIView):
    """
    POST - Accept agreements. Body: { "legal_agreement_data": [1, 2, 3] }
    Creates AcceptanceOfAgreement for each LegalPage ID with request.user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Acceptance of Agreement'],
        summary='Accept agreements',
        description='Accept multiple legal agreements by LegalPage IDs. User is taken from request.',
        request=AcceptanceOfAgreementCreateSerializer,
        responses={201: AcceptanceOfAgreementSerializer(many=True)},
    )
    async def post(self, request):
        serializer = AcceptanceOfAgreementCreateSerializer(data=request.data)
        is_valid = await sync_to_async(serializer.is_valid)()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        def create_acceptances():
            ids = serializer.validated_data['legal_agreement_data']
            user = request.user
            result = []
            for agreement_id in ids:
                agreement = LegalPage.objects.get(id=agreement_id)
                obj = AcceptanceOfAgreement.accept_agreement(user=user, agreement=agreement)
                result.append(obj)
            return result

        acceptances = await sync_to_async(create_acceptances)()
        response_serializer = AcceptanceOfAgreementSerializer(
            acceptances, many=True, context={'request': request}
        )
        data = await sync_to_async(lambda: response_serializer.data)()
        return Response(
            {
                'message': 'Agreements accepted successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_201_CREATED
        )


class AcceptanceOfAgreementListView(AsyncAPIView):
    """
    GET - List all AcceptanceOfAgreement for request.user
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Acceptance of Agreement'],
        summary='List my acceptances',
        description='Get all agreement acceptances for the authenticated user.',
        responses={200: AcceptanceOfAgreementSerializer(many=True)},
    )
    async def get(self, request):
        def get_list():
            return list(
                AcceptanceOfAgreement.objects.filter(user=request.user)
                .select_related('agreement')
                .order_by('-created_at')
            )

        items = await sync_to_async(get_list)()
        serializer = AcceptanceOfAgreementSerializer(items, many=True, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Acceptances retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK
        )


class AcceptanceOfAgreementDetailView(AsyncAPIView):
    """
    GET - Get single AcceptanceOfAgreement by ID, only if it belongs to request.user
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Acceptance of Agreement'],
        summary='Get acceptance by ID',
        description='Get a single agreement acceptance by ID. Only returns if it belongs to the authenticated user.',
        responses={200: AcceptanceOfAgreementSerializer, 404: None},
    )
    async def get(self, request, pk):
        def get_object():
            try:
                return AcceptanceOfAgreement.objects.select_related('agreement').get(
                    pk=pk, user=request.user
                )
            except AcceptanceOfAgreement.DoesNotExist:
                return None

        obj = await sync_to_async(get_object)()
        if obj is None:
            return Response(
                {'message': 'Not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AcceptanceOfAgreementSerializer(obj, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Acceptance retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK
        )
