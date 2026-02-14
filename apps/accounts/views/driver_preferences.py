from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

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

    @extend_schema(tags=['Driver Preferences'], summary='Get preferences', description='Get current driver ride preferences (trip type, max pickup distance, working hours, notification intensity). Role: Driver.')
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

    @extend_schema(tags=['Driver Preferences'], summary='Create/update preferences', description='Create or update driver preferences. Role: Driver.')
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

    @extend_schema(tags=['Driver Preferences'], summary='Full update preferences', description='Update driver preferences (full update). Role: Driver.')
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

    @extend_schema(tags=['Driver Preferences'], summary='Partial update preferences', description='Update driver preferences (partial update). Role: Driver.')
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

