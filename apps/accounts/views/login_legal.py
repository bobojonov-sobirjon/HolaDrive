from __future__ import annotations

from asgiref.sync import sync_to_async
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import LoginLegalDocument
from apps.accounts.serializers.login_legal import LoginLegalDocumentSerializer
from apps.common.views import AsyncAPIView

DOCUMENT_TYPE_PATHS = {
    'privacy-policy': LoginLegalDocument.DocumentType.PRIVACY_POLICY,
    'terms-of-service': LoginLegalDocument.DocumentType.TERMS_OF_SERVICE,
}


def _document_type_from_slug(slug: str) -> str | None:
    return DOCUMENT_TYPE_PATHS.get((slug or '').strip().lower())


async def _get_active_document(document_type: str) -> LoginLegalDocument | None:
    try:
        return await LoginLegalDocument.objects.aget(
            document_type=document_type,
            is_active=True,
        )
    except LoginLegalDocument.DoesNotExist:
        return None


class LoginLegalDocumentsListView(AsyncAPIView):
    """Login page: Privacy Policy + Terms of Service URLs (read-only, no auth)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Legal (login)'],
        summary='Login legal document links',
        description=(
            'Returns open URLs for Privacy Policy and Terms of Service on the login screen. '
            'No accept/decline. PDF opens file URL; HTML opens in-app/browser view URL.'
        ),
    )
    async def get(self, request):
        rows = await sync_to_async(list)(
            LoginLegalDocument.objects.filter(is_active=True).order_by('document_type')
        )
        ser = LoginLegalDocumentSerializer(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()

        by_type = {row['document_type']: row for row in data}
        return Response(
            {
                'message': 'OK',
                'status': 'success',
                'data': {
                    'privacy_policy': by_type.get(LoginLegalDocument.DocumentType.PRIVACY_POLICY),
                    'terms_of_service': by_type.get(LoginLegalDocument.DocumentType.TERMS_OF_SERVICE),
                    'documents': data,
                },
            },
            status=status.HTTP_200_OK,
        )


class LoginLegalDocumentDetailView(AsyncAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Legal (login)'],
        summary='Get login legal document by slug',
        description='Slug: `privacy-policy` or `terms-of-service`.',
    )
    async def get(self, request, slug: str):
        document_type = _document_type_from_slug(slug)
        if not document_type:
            return Response(
                {'message': 'Invalid document slug', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        doc = await _get_active_document(document_type)
        if not doc:
            return Response(
                {'message': 'Document not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        ser = LoginLegalDocumentSerializer(doc, context={'request': request})
        payload = await sync_to_async(lambda: ser.data)()
        return Response(
            {'message': 'OK', 'status': 'success', 'data': payload},
            status=status.HTTP_200_OK,
        )


class LoginLegalDocumentViewPage(AsyncAPIView):
    """Browser/WebView: render HTML document or redirect to PDF."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Legal (login)'],
        summary='Open login legal document (HTML page or PDF)',
        description='Slug: `privacy-policy` or `terms-of-service`. HTML returns page; PDF redirects to file.',
    )
    async def get(self, request, slug: str):
        document_type = _document_type_from_slug(slug)
        if not document_type:
            return Response(
                {'message': 'Invalid document slug', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        doc = await _get_active_document(document_type)
        if not doc:
            return Response(
                {'message': 'Document not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if doc.content_format == LoginLegalDocument.ContentFormat.PDF:
            if not doc.pdf_file:
                return Response(
                    {'message': 'PDF file is not uploaded', 'status': 'error'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            from django.shortcuts import redirect

            pdf_url = request.build_absolute_uri(doc.pdf_file.url)
            return redirect(pdf_url)

        body = doc.html_content or ''
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{doc.title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px; line-height: 1.5; color: #111; }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""
        return HttpResponse(html, content_type='text/html; charset=utf-8')
