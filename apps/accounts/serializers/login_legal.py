from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import LoginLegalDocument

SLUG_BY_DOCUMENT_TYPE = {
    LoginLegalDocument.DocumentType.PRIVACY_POLICY: 'privacy-policy',
    LoginLegalDocument.DocumentType.TERMS_OF_SERVICE: 'terms-of-service',
}


class LoginLegalDocumentSerializer(serializers.ModelSerializer):
    open_url = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = LoginLegalDocument
        fields = (
            'id',
            'document_type',
            'title',
            'content_format',
            'open_url',
            'content',
            'updated_at',
        )
        read_only_fields = fields

    def get_open_url(self, obj: LoginLegalDocument) -> str | None:
        request = self.context.get('request')
        if obj.content_format == LoginLegalDocument.ContentFormat.PDF:
            if not obj.pdf_file:
                return None
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        path = f'/api/v1/accounts/legal-documents/{SLUG_BY_DOCUMENT_TYPE.get(obj.document_type, obj.document_type)}/view/'
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_content(self, obj: LoginLegalDocument) -> str | None:
        if obj.content_format != LoginLegalDocument.ContentFormat.HTML:
            return None
        return obj.html_content or ''
