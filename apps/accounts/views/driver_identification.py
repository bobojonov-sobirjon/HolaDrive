from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from asgiref.sync import sync_to_async
from django.db.models import Q
from drf_spectacular.utils import extend_schema

from ..serializers import (
    DriverIdentificationSerializer,
    DriverIdentificationUploadDocumentSerializer,
    DriverIdentificationUploadRequestSerializer,
    DriverIdentificationUserStatusSerializer,
)
from ..models import DriverIdentification, DriverIdentificationUploadDocument


class DriverIdentificationUploadView(AsyncAPIView):
    """
    Upload driver identification document endpoint - POST
    
    Allows authenticated users to upload documents for driver identifications.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=['Driver Identification'], summary='Upload document', description='Upload a document for a driver identification type. If already uploaded for this type, it will be updated.', request=DriverIdentificationUploadRequestSerializer)
    async def post(self, request):
        """
        Upload document for driver identification - ASYNC VERSION
        """
        document_file = request.FILES.get('document_file')
        driver_identification_id = request.data.get('driver_identification_id')
        
        if not document_file:
            return Response(
                {
                    'message': 'document_file is required',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not driver_identification_id:
            return Response(
                {
                    'message': 'driver_identification_id is required',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            driver_identification_id = int(driver_identification_id)
        except (ValueError, TypeError):
            return Response(
                {
                    'message': 'driver_identification_id must be a valid integer',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if driver identification exists and is active
        try:
            driver_identification = await DriverIdentification.objects.aget(
                id=driver_identification_id,
                is_active=True
            )
        except DriverIdentification.DoesNotExist:
            return Response(
                {
                    'message': 'Driver identification not found or is not active',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create or update upload document
        serializer = DriverIdentificationUploadDocumentSerializer(
            data={
                'driver_identification': driver_identification.id,
                'document_file': document_file
            },
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            upload = await sync_to_async(serializer.save)()
            # Refresh serializer with the saved instance to get proper representation
            serializer = DriverIdentificationUploadDocumentSerializer(
                upload,
                context={'request': request}
            )
            serializer_data = await sync_to_async(lambda: serializer.data)()
            
            return Response(
                {
                    'message': 'Document uploaded successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_201_CREATED
            )
        
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class DriverIdentificationUserStatusView(AsyncAPIView):
    """
    Get user's driver identification status endpoint - GET
    
    Returns all active driver identifications with user's upload status.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Driver Identification'], summary='User identification status', description="Get user's driver identification status. For each type: is_upload_user, document_file, driver_identification_upload_id.")
    async def get(self, request):
        """
        Get user's identification status - ASYNC VERSION
        """
        user = request.user
        
        # Get all active driver identifications
        def get_active_identifications():
            return list(DriverIdentification.objects.filter(is_active=True).order_by('id'))
        active_identifications = await sync_to_async(get_active_identifications)()
        
        # Get user's uploads
        def get_user_uploads():
            return list(DriverIdentificationUploadDocument.objects.filter(
                user=user
            ).select_related('driver_identification'))
        user_uploads = await sync_to_async(get_user_uploads)()
        
        # Create a dictionary for quick lookup
        uploads_dict = {upload.driver_identification_id: upload for upload in user_uploads}
        
        # Build response data
        response_data = []
        for identification in active_identifications:
            upload = uploads_dict.get(identification.id)
            
            if upload:
                document_file = request.build_absolute_uri(upload.document_file.url) if upload.document_file else ""
                response_data.append({
                    'driver_identification_id': identification.id,
                    'driver_identification_name': identification.name,
                    'driver_identification_title': identification.title,
                    'driver_identification_upload_id': upload.id,
                    'is_upload_user': True,
                    'document_file': document_file
                })
            else:
                response_data.append({
                    'driver_identification_id': identification.id,
                    'driver_identification_name': identification.name,
                    'driver_identification_title': identification.title,
                    'driver_identification_upload_id': None,
                    'is_upload_user': False,
                    'document_file': ""
                })
        
        return Response(
            {
                'message': 'Identification status retrieved successfully',
                'status': 'success',
                'data': response_data
            },
            status=status.HTTP_200_OK
        )


class DriverIdentificationListView(AsyncAPIView):
    """
    Get all active driver identifications endpoint - GET
    
    Returns all active driver identification types.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Driver Identification'], summary='List identifications', description='Get all active driver identifications. Each includes identification_faq (question, link, file).')
    async def get(self, request):
        """
        Get all active driver identifications - ASYNC VERSION
        """
        def get_identifications():
            return list(DriverIdentification.objects.filter(is_active=True)
                       .prefetch_related('items', 'identification_faq').order_by('id'))
        identifications = await sync_to_async(get_identifications)()
        
        serializer = DriverIdentificationSerializer(
            identifications,
            many=True,
            context={'request': request}
        )
        serializer_data = await sync_to_async(lambda: serializer.data)()
        
        return Response(
            {
                'message': 'Driver identifications retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )
