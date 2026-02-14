from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from ..serializers import UserPreferencesSerializer
from ..models import UserPreferences

class UserPreferencesView(AsyncAPIView):
    """
    User preferences endpoint - GET, POST, PUT, PATCH
    
    This endpoint allows authenticated users to manage their ride preferences including:
    - Chatting preferences (no_communication, casual, friendly)
    - Temperature preferences (warm, comfortable, cool, cold)
    - Music preferences (pop, rock, jazz, classical, hip_hop, electronic, country, no_music)
    - Volume level (low, medium, high, mute)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['User Preferences'], summary='Get preferences', description='Get current user ride preferences (chatting, temperature, music, volume).')
    async def get(self, request):
        """
        Get current user's latest preferences with optimized query - ASYNC VERSION
        
        Retrieves the most recently updated preferences for the authenticated user.
        """
        # Optimize query: use select_related to fetch user in same query (async)
        # Since user is already available, we can optimize by using only() to select needed fields
        preferences = await UserPreferences.objects.filter(
            user=request.user
        ).select_related('user').only(
            'id', 'user_id', 'chatting_preference', 'temperature_preference',
            'music_preference', 'volume_level', 'created_at', 'updated_at'
        ).afirst()
        
        if not preferences:
            return Response(
                {
                    'message': 'Preferences not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserPreferencesSerializer(preferences, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Preferences retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(tags=['User Preferences'], summary='Create/update preferences', description='Create or update user preferences.', request=UserPreferencesSerializer)
    async def post(self, request):
        """
        Create or update user preferences - ASYNC VERSION
        
        Creates a new preference entry for the authenticated user.
        If preferences already exist for this user, they will be updated instead of creating a new one.
        This ensures only one preferences entry exists per user.
        """
        # Optimize query: use only() to select needed fields (async)
        existing_preferences = await UserPreferences.objects.filter(
            user=request.user
        ).only('id', 'user_id').afirst()
        is_update = existing_preferences is not None
        
        serializer = UserPreferencesSerializer(
            data=request.data,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            preferences = await sync_to_async(serializer.save)()
            
            # Return 200 if updating, 201 if creating
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

    @extend_schema(tags=['User Preferences'], summary='Full update preferences', description='Update user preferences (full update).', request=UserPreferencesSerializer)
    async def put(self, request):
        """
        Update user preferences (full update) - ASYNC VERSION
        
        Updates all preference fields. All fields must be provided.
        """
        # Optimize query: use select_related and only() for better performance (async)
        preferences = await UserPreferences.objects.filter(
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
        
        serializer = UserPreferencesSerializer(
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

    @extend_schema(tags=['User Preferences'], summary='Partial update preferences', description='Update user preferences (partial update).', request=UserPreferencesSerializer)
    async def patch(self, request):
        """
        Partially update user preferences - ASYNC VERSION
        
        Updates only the provided fields, leaving others unchanged.
        """
        # Optimize query: use select_related for better performance (async)
        preferences = await UserPreferences.objects.filter(
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
        
        serializer = UserPreferencesSerializer(
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

class UserPreferencesDeleteView(AsyncAPIView):
    """
    Delete user preferences endpoint
    
    Deletes the user's latest preferences entry.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['User Preferences'], summary='Delete preferences', description='Delete user preferences.')
    async def delete(self, request):
        """
        Delete user preferences - ASYNC VERSION
        
        Deletes the latest preferences entry for the authenticated user.
        """
        # Optimize query: use only() to select minimal fields needed for deletion (async)
        preferences = await UserPreferences.objects.filter(
            user=request.user
        ).only('id', 'user_id').afirst()
        
        if not preferences:
            return Response(
                {
                    'message': 'Preferences not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        await sync_to_async(preferences.delete)()
        return Response(
            {
                'message': 'Preferences deleted successfully',
                'status': 'success'
            },
            status=status.HTTP_204_NO_CONTENT
        )