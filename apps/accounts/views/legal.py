from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from asgiref.sync import sync_to_async
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.common.views import AsyncAPIView
from ..models import LegalPage
from ..serializers.legal import LegalPageSerializer


class LegalPageListView(AsyncAPIView):
    """
    GET list of legal pages (Privacy Policy, Terms of Service, etc.)
    Public endpoint - no auth required.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Legal'],
        operation_description="Get list of legal pages (Privacy Policy, Terms of Service). Returns name and link for each.",
        responses={
            200: openapi.Response(description="Legal pages list"),
        }
    )
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
