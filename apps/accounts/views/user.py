from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from asgiref.sync import sync_to_async

from ..serializers import UserDetailSerializer
from ..models import CustomUser


class UserDetailView(AsyncAPIView):
    """
    User details endpoint
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Get authenticated user details",
        responses={
            200: openapi.Response(description="User details retrieved successfully"),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    async def get(self, request):
        """
        Get current user details with optimized query - ASYNC VERSION
        """
        # Optimize query: prefetch groups to avoid N+1 queries (async)
        user = await CustomUser.objects.prefetch_related('groups').aget(pk=request.user.pk)
        serializer = UserDetailSerializer(user, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'User details retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Update authenticated user details. Avatar can be uploaded as a file using multipart/form-data.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Phone number (max 15 characters)',
                    example='+1234567890'
                ),
                'date_of_birth': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATE,
                    description='Date of birth (YYYY-MM-DD)',
                    example='1990-01-01'
                ),
                'gender': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['male', 'female', 'other'],
                    description='Gender',
                    example='male'
                ),
                'avatar': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Avatar image file (use multipart/form-data for file upload)'
                ),
                'address': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Address',
                    example='123 Main Street, City, Country'
                ),
                'longitude': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    format=openapi.FORMAT_DECIMAL,
                    description='Longitude coordinate',
                    example=69.2401
                ),
                'latitude': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    format=openapi.FORMAT_DECIMAL,
                    description='Latitude coordinate',
                    example=41.2995
                ),
                'tax_number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Tax Number (GST/HST), max 15 characters',
                    example='123456789'
                ),
            }
        ),
        responses={
            200: openapi.Response(description="User details updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
        },
        consumes=['multipart/form-data', 'application/json']
    )
    async def put(self, request):
        """
        Update current user details - ASYNC VERSION
        """
        serializer = UserDetailSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            await sync_to_async(serializer.save)()
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'User details updated successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_200_OK
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

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Partially update authenticated user details. Avatar can be uploaded as a file using multipart/form-data.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Phone number (max 15 characters)',
                    example='+1234567890'
                ),
                'date_of_birth': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATE,
                    description='Date of birth (YYYY-MM-DD)',
                    example='1990-01-01'
                ),
                'gender': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['male', 'female', 'other'],
                    description='Gender',
                    example='male'
                ),
                'avatar': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Avatar image file (use multipart/form-data for file upload)'
                ),
                'address': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Address',
                    example='123 Main Street, City, Country'
                ),
                'longitude': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    format=openapi.FORMAT_DECIMAL,
                    description='Longitude coordinate',
                    example=69.2401
                ),
                'latitude': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    format=openapi.FORMAT_DECIMAL,
                    description='Latitude coordinate',
                    example=41.2995
                ),
                'tax_number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Tax Number (GST/HST), max 15 characters',
                    example='123456789'
                ),
            }
        ),
        responses={
            200: openapi.Response(description="User details updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
        },
        consumes=['multipart/form-data', 'application/json']
    )
    async def patch(self, request): 
        """
        Partially update current user details - ASYNC VERSION
        """
        serializer = UserDetailSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            await sync_to_async(serializer.save)()
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'User details updated successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_200_OK
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