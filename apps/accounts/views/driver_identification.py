from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from asgiref.sync import sync_to_async
from django.db.models import Q

from ..serializers import (
    DriverIdentificationSerializer,
    DriverIdentificationUploadDocumentSerializer,
    DriverIdentificationUserStatusSerializer
)
from ..models import DriverIdentification, DriverIdentificationUploadDocument


class DriverIdentificationUploadView(AsyncAPIView):
    """
    Upload driver identification document endpoint - POST
    
    Allows authenticated users to upload documents for driver identifications.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Upload a document for a driver identification type.
        
        This endpoint allows authenticated users to upload a document file for a specific 
        driver identification type. If the user has already uploaded a document for this 
        identification type, it will be updated.
        
        **Request Body:**
        - `document_file` (file, required): The document file to upload (image file)
        - `driver_identification_id` (integer, required): ID of the driver identification type
        
        **Authentication Required:** Yes (JWT Token)
        
        **Example Request:**
        ```
        POST /api/accounts/driver/identification/upload/
        Content-Type: multipart/form-data
        
        document_file: [file]
        driver_identification_id: 1
        ```
        """,
        manual_parameters=[
            openapi.Parameter(
                'document_file',
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description='The document file to upload (image file)'
            ),
            openapi.Parameter(
                'driver_identification_id',
                openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='ID of the driver identification type'
            ),
        ],
        responses={
            201: openapi.Response(
                description="Document uploaded successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example='Document uploaded successfully'),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example='success'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                'driver_identification_name': openapi.Schema(type=openapi.TYPE_STRING, example='Driver License'),
                                'driver_identification_title': openapi.Schema(type=openapi.TYPE_STRING, example='Take a photo of your Driver\'s License'),
                                'document_file': openapi.Schema(type=openapi.TYPE_STRING, example='http://example.com/media/driver_documents/driver_license.jpg'),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Driver identification not found"),
            401: openapi.Response(description="Unauthorized"),
        }
    )
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

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Get user's driver identification status.
        
        Returns all active driver identifications along with the user's upload status.
        For each identification:
        - If user has uploaded: `is_upload_user` = true, `document_file` = file URL, `driver_identification_upload_id` = upload ID
        - If user has not uploaded: `is_upload_user` = false, `document_file` = empty, `driver_identification_upload_id` = null
        
        **Authentication Required:** Yes (JWT Token)
        
        **Example Response:**
        ```json
        {
            "message": "Identification status retrieved successfully",
            "status": "success",
            "data": [
                {
                    "driver_identification_id": 1,
                    "driver_identification_name": "Driver License",
                    "driver_identification_title": "Take a photo of your Driver's License",
                    "driver_identification_upload_id": 5,
                    "is_upload_user": true,
                    "document_file": "http://example.com/media/driver_documents/driver_license.jpg"
                },
                {
                    "driver_identification_id": 2,
                    "driver_identification_name": "Profile Photo",
                    "driver_identification_title": "Take a photo of your Profile Photo",
                    "driver_identification_upload_id": null,
                    "is_upload_user": false,
                    "document_file": ""
                }
            ]
        }
        ```
        """,
        responses={
            200: openapi.Response(
                description="Identification status retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'driver_identification_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'driver_identification_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'driver_identification_title': openapi.Schema(type=openapi.TYPE_STRING),
                                    'driver_identification_upload_id': openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
                                    'is_upload_user': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'document_file': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
        }
    )
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

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Get all active driver identifications.
        
        Returns a list of all active driver identification types that can be used for document uploads.
        Only identifications with `is_active=True` are returned.
        
        **Authentication Required:** Yes (JWT Token)
        
        **Example Response:**
        ```json
        {
            "message": "Driver identifications retrieved successfully",
            "status": "success",
            "data": [
                {
                    "id": 1,
                    "name": "Driver License",
                    "image": "http://example.com/media/driver_identification_icons/license.png",
                    "title": "Take a photo of your Driver's License",
                    "description": "Make sure your Driver's License is not expired...",
                    "is_active": true,
                    "items": [],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        ```
        """,
        responses={
            200: openapi.Response(
                description="Driver identifications retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'image': openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
                                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'items': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'item': openapi.Schema(type=openapi.TYPE_STRING),
                                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            }
                                        )
                                    ),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    async def get(self, request):
        """
        Get all active driver identifications - ASYNC VERSION
        """
        def get_identifications():
            return list(DriverIdentification.objects.filter(is_active=True)
                       .prefetch_related('items').order_by('id'))
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
