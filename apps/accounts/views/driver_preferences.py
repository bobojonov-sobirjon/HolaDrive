from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from asgiref.sync import sync_to_async

from ..serializers import DriverPreferencesSerializer
from ..models import DriverPreferences


class DriverPreferencesView(AsyncAPIView):
    """
    Driver preferences endpoint - GET, POST, PUT, PATCH
    
    This endpoint allows authenticated drivers to manage their ride preferences including:
    - Trip type preference (short, medium, long, any)
    - Maximum pickup distance (1-20 km)
    - Preferred working hours (morning, afternoon, evening, night, any)
    - Notification intensity (minimal, moderate, high)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Driver Preferences'],
        operation_description="""
        Get current driver's latest preferences.
        
        Returns the most recently updated preferences for the authenticated driver.
        If no preferences exist, returns a 404 error.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        responses={
            200: openapi.Response(
                description="Preferences retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences retrieved successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            404: openapi.Response(description="Preferences not found"),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
        }
    )
    async def get(self, request):
        """
        Get current driver's latest preferences - ASYNC VERSION
        """
        preferences = await DriverPreferences.objects.filter(
            user=request.user
        ).select_related('user').afirst()
        
        if not preferences:
            return Response(
                {
                    'message': 'Preferences not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DriverPreferencesSerializer(preferences, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Preferences retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['Driver Preferences'],
        operation_description="""
        Create or update driver preferences.
        
        **Important:** This endpoint ensures only ONE preferences entry exists per driver.
        - If preferences don't exist: Creates a new preference entry (returns 201)
        - If preferences already exist: Updates the existing entry instead of creating a new one (returns 200)
        
        **Authentication Required:** Yes (JWT Token)
        """,
        request_body=DriverPreferencesSerializer,
        responses={
            200: openapi.Response(description="Preferences updated successfully"),
            201: openapi.Response(description="Preferences created successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    async def post(self, request):
        """
        Create or update driver preferences - ASYNC VERSION
        """
        existing_preferences = await DriverPreferences.objects.filter(
            user=request.user
        ).only('id', 'user_id').afirst()
        is_update = existing_preferences is not None
        
        serializer = DriverPreferencesSerializer(
            data=request.data,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            preferences = await sync_to_async(serializer.save)()
            
            response_status = status.HTTP_200_OK if is_update else status.HTTP_201_CREATED
            message = 'Preferences updated successfully' if is_update else 'Preferences created successfully'
            
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': message,
                    'status': 'success',
                    'data': serializer_data
                },
                status=response_status
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
        tags=['Driver Preferences'],
        operation_description="""
        Update driver preferences (full update).
        
        Performs a complete update of the driver's latest preferences.
        All fields must be provided in the request body.
        If no preferences exist, returns a 404 error.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        request_body=DriverPreferencesSerializer,
        responses={
            200: openapi.Response(description="Preferences updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Preferences not found"),
        }
    )
    async def put(self, request):
        """
        Update driver preferences (full update) - ASYNC VERSION
        """
        preferences = await DriverPreferences.objects.filter(
            user=request.user
        ).select_related('user').afirst()
        
        if not preferences:
            return Response(
                {
                    'message': 'Preferences not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DriverPreferencesSerializer(
            preferences,
            data=request.data,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            await sync_to_async(serializer.save)()
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Preferences updated successfully',
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
        tags=['Driver Preferences'],
        operation_description="""
        Partially update driver preferences.
        
        Updates only the fields provided in the request body.
        Fields not included in the request will remain unchanged.
        If no preferences exist, returns a 404 error.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        request_body=DriverPreferencesSerializer,
        responses={
            200: openapi.Response(description="Preferences updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Preferences not found"),
        }
    )
    async def patch(self, request):
        """
        Partially update driver preferences - ASYNC VERSION
        """
        preferences = await DriverPreferences.objects.filter(
            user=request.user
        ).select_related('user').afirst()
        
        if not preferences:
            return Response(
                {
                    'message': 'Preferences not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DriverPreferencesSerializer(
            preferences,
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
                    'message': 'Preferences updated successfully',
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

