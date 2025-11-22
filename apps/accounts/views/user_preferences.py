from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers import UserPreferencesSerializer
from ..models import UserPreferences


class UserPreferencesView(APIView):
    """
    User preferences endpoint - GET, POST, PUT, PATCH
    
    This endpoint allows authenticated users to manage their ride preferences including:
    - Chatting preferences (no_communication, casual, friendly)
    - Temperature preferences (warm, comfortable, cool, cold)
    - Music preferences (pop, rock, jazz, classical, hip_hop, electronic, country, no_music)
    - Volume level (low, medium, high, mute)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['User Preferences'],
        operation_description="""
        Get current user's latest preferences.
        
        Returns the most recently updated preferences for the authenticated user.
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
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                'chatting_preference': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    enum=['no_communication', 'casual', 'friendly'],
                                    example='no_communication'
                                ),
                                'temperature_preference': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    enum=['warm', 'comfortable', 'cool', 'cold'],
                                    example='warm'
                                ),
                                'music_preference': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    enum=['pop', 'rock', 'jazz', 'classical', 'hip_hop', 'electronic', 'country', 'no_music'],
                                    example='pop'
                                ),
                                'volume_level': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    enum=['low', 'medium', 'high', 'mute'],
                                    example='low'
                                ),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            404: openapi.Response(
                description="Preferences not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences not found"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
        }
    )
    def get(self, request):
        """
        Get current user's latest preferences with optimized query
        
        Retrieves the most recently updated preferences for the authenticated user.
        """
        # Optimize query: use select_related to fetch user in same query
        # Since user is already available, we can optimize by using only() to select needed fields
        preferences = UserPreferences.objects.filter(
            user=request.user
        ).select_related('user').only(
            'id', 'user_id', 'chatting_preference', 'temperature_preference',
            'music_preference', 'volume_level', 'created_at', 'updated_at'
        ).first()
        
        if not preferences:
            return Response(
                {
                    'message': 'Preferences not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserPreferencesSerializer(preferences, context={'request': request})
        return Response(
            {
                'message': 'Preferences retrieved successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['User Preferences'],
        operation_description="""
        Create or update user preferences.
        
        **Important:** This endpoint ensures only ONE preferences entry exists per user.
        - If preferences don't exist: Creates a new preference entry (returns 201)
        - If preferences already exist: Updates the existing entry instead of creating a new one (returns 200)
        
        This prevents duplicate preferences entries for the same user.
        
        **Request Body:**
        - chatting_preference: One of: 'no_communication', 'casual', 'friendly'
        - temperature_preference: One of: 'warm', 'comfortable', 'cool', 'cold'
        - music_preference: One of: 'pop', 'rock', 'jazz', 'classical', 'hip_hop', 'electronic', 'country', 'no_music'
        - volume_level: One of: 'low', 'medium', 'high', 'mute'
        
        **Authentication Required:** Yes (JWT Token)
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['chatting_preference', 'temperature_preference', 'music_preference', 'volume_level'],
            properties={
                'chatting_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['no_communication', 'casual', 'friendly'],
                    example='no_communication',
                    description='Preferred communication style during rides'
                ),
                'temperature_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['warm', 'comfortable', 'cool', 'cold'],
                    example='warm',
                    description='Preferred temperature range: warm (25°C+), comfortable (22-24°C), cool (18-21°C), cold (<18°C)'
                ),
                'music_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['pop', 'rock', 'jazz', 'classical', 'hip_hop', 'electronic', 'country', 'no_music'],
                    example='pop',
                    description='Preferred music genre'
                ),
                'volume_level': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['low', 'medium', 'high', 'mute'],
                    example='low',
                    description='Preferred music volume level'
                ),
            },
            example={
                'chatting_preference': 'no_communication',
                'temperature_preference': 'warm',
                'music_preference': 'pop',
                'volume_level': 'low'
            }
        ),
        responses={
            200: openapi.Response(
                description="Preferences updated successfully (if preferences already exist)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences updated successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                'chatting_preference': openapi.Schema(type=openapi.TYPE_STRING, example='no_communication'),
                                'temperature_preference': openapi.Schema(type=openapi.TYPE_STRING, example='warm'),
                                'music_preference': openapi.Schema(type=openapi.TYPE_STRING, example='pop'),
                                'volume_level': openapi.Schema(type=openapi.TYPE_STRING, example='low'),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            201: openapi.Response(
                description="Preferences created successfully (if preferences don't exist)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences created successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                'chatting_preference': openapi.Schema(type=openapi.TYPE_STRING, example='no_communication'),
                                'temperature_preference': openapi.Schema(type=openapi.TYPE_STRING, example='warm'),
                                'music_preference': openapi.Schema(type=openapi.TYPE_STRING, example='pop'),
                                'volume_level': openapi.Schema(type=openapi.TYPE_STRING, example='low'),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request - validation errors",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Validation error"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            example={
                                'chatting_preference': ['Invalid choice. Must be one of: no_communication, casual, friendly'],
                                'temperature_preference': ['This field is required.']
                            }
                        ),
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
        }
    )
    def post(self, request):
        """
        Create or update user preferences
        
        Creates a new preference entry for the authenticated user.
        If preferences already exist for this user, they will be updated instead of creating a new one.
        This ensures only one preferences entry exists per user.
        """
        # Optimize query: use only() to select needed fields
        existing_preferences = UserPreferences.objects.filter(
            user=request.user
        ).only('id', 'user_id').first()
        is_update = existing_preferences is not None
        
        serializer = UserPreferencesSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            preferences = serializer.save()
            
            # Return 200 if updating, 201 if creating
            response_status = status.HTTP_200_OK if is_update else status.HTTP_201_CREATED
            message = 'Preferences updated successfully' if is_update else 'Preferences created successfully'
            
            return Response(
                {
                    'message': message,
                    'status': 'success',
                    'data': serializer.data
                },
                status=response_status
            )
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        tags=['User Preferences'],
        operation_description="""
        Update user preferences (full update).
        
        Performs a complete update of the user's latest preferences.
        All fields must be provided in the request body.
        If no preferences exist, returns a 404 error.
        
        **Request Body:** Same as POST endpoint - all fields required.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['chatting_preference', 'temperature_preference', 'music_preference', 'volume_level'],
            properties={
                'chatting_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['no_communication', 'casual', 'friendly'],
                    example='casual'
                ),
                'temperature_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['warm', 'comfortable', 'cool', 'cold'],
                    example='comfortable'
                ),
                'music_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['pop', 'rock', 'jazz', 'classical', 'hip_hop', 'electronic', 'country', 'no_music'],
                    example='rock'
                ),
                'volume_level': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['low', 'medium', 'high', 'mute'],
                    example='medium'
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description="Preferences updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences updated successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(
                description="Preferences not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences not found"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                    }
                )
            ),
        }
    )
    def put(self, request):
        """
        Update user preferences (full update)
        
        Updates all preference fields. All fields must be provided.
        """
        # Optimize query: use select_related and only() for better performance
        preferences = UserPreferences.objects.filter(
            user=request.user
        ).select_related('user').first()
        
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
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Preferences updated successfully',
                    'status': 'success',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        tags=['User Preferences'],
        operation_description="""
        Partially update user preferences.
        
        Updates only the fields provided in the request body.
        Fields not included in the request will remain unchanged.
        If no preferences exist, returns a 404 error.
        
        **Request Body:** Partial update - only include fields you want to change.
        
        **Example Request:**
        ```json
        {
          "temperature_preference": "cool",
          "volume_level": "high"
        }
        ```
        
        **Authentication Required:** Yes (JWT Token)
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'chatting_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['no_communication', 'casual', 'friendly'],
                    description='Optional - only include if updating'
                ),
                'temperature_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['warm', 'comfortable', 'cool', 'cold'],
                    description='Optional - only include if updating'
                ),
                'music_preference': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['pop', 'rock', 'jazz', 'classical', 'hip_hop', 'electronic', 'country', 'no_music'],
                    description='Optional - only include if updating'
                ),
                'volume_level': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['low', 'medium', 'high', 'mute'],
                    description='Optional - only include if updating'
                ),
            },
            example={
                'temperature_preference': 'cool',
                'volume_level': 'high'
            }
        ),
        responses={
            200: openapi.Response(
                description="Preferences updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences updated successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(
                description="Preferences not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences not found"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                    }
                )
            ),
        }
    )
    def patch(self, request):
        """
        Partially update user preferences
        
        Updates only the provided fields, leaving others unchanged.
        """
        # Optimize query: use select_related for better performance
        preferences = UserPreferences.objects.filter(
            user=request.user
        ).select_related('user').first()
        
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
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Preferences updated successfully',
                    'status': 'success',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class UserPreferencesDeleteView(APIView):
    """
    Delete user preferences endpoint
    
    Deletes the user's latest preferences entry.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['User Preferences'],
        operation_description="""
        Delete user preferences.
        
        Deletes the most recently updated preferences for the authenticated user.
        If no preferences exist, returns a 404 error.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        responses={
            204: openapi.Response(
                description="Preferences deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences deleted successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
            404: openapi.Response(
                description="Preferences not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Preferences not found"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                    }
                )
            ),
        }
    )
    def delete(self, request):
        """
        Delete user preferences
        
        Deletes the latest preferences entry for the authenticated user.
        """
        # Optimize query: use only() to select minimal fields needed for deletion
        preferences = UserPreferences.objects.filter(
            user=request.user
        ).only('id', 'user_id').first()
        
        if not preferences:
            return Response(
                {
                    'message': 'Preferences not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        preferences.delete()
        return Response(
            {
                'message': 'Preferences deleted successfully',
                'status': 'success'
            },
            status=status.HTTP_204_NO_CONTENT
        )