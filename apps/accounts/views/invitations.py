from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers import InvitationGenerateSerializer, InvitationUsersSerializer
from ..models import InvitationGenerate, InvitationUsers


class InvitationGenerateView(APIView):
    """
    Invitation generation endpoint - POST only
    Creates an invitation code for the authenticated user (only once)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Invitations'],
        operation_description="""
        Generate invitation code for the authenticated user.
        
        **Important:** This endpoint can only be called once per user.
        If an invitation code already exists for the user, it will return the existing code.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        responses={
            200: openapi.Response(
                description="Invitation code retrieved successfully (if already exists)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Invitation code retrieved successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'invite_code': openapi.Schema(type=openapi.TYPE_STRING, example="ABC123XYZ9"),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            201: openapi.Response(
                description="Invitation code created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Invitation code created successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'invite_code': openapi.Schema(type=openapi.TYPE_STRING, example="ABC123XYZ9"),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
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
        Generate invitation code for the authenticated user
        Only creates once - if already exists, returns existing code
        """
        user = request.user
        
        # Check if invitation code already exists
        invitation = InvitationGenerate.objects.filter(user=user).first()
        
        if invitation:
            # Return existing invitation code
            serializer = InvitationGenerateSerializer(invitation)
            return Response(
                {
                    'message': 'Invitation code retrieved successfully',
                    'status': 'success',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        # Create new invitation code
        invitation = InvitationGenerate.objects.create(user=user)
        serializer = InvitationGenerateSerializer(invitation)
        
        return Response(
            {
                'message': 'Invitation code created successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class InvitationGetView(APIView):
    """
    Get invitation code for the authenticated user - GET
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Invitations'],
        operation_description="""
        Get invitation code for the authenticated user.
        
        Returns the invitation code that belongs to the authenticated user.
        If no invitation code exists, returns a 404 error.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        responses={
            200: openapi.Response(
                description="Invitation code retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Invitation code retrieved successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'invite_code': openapi.Schema(type=openapi.TYPE_STRING, example="ABC123XYZ9"),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            404: openapi.Response(
                description="Invitation code not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Invitation code not found"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
        }
    )
    def get(self, request):
        """
        Get invitation code for the authenticated user
        """
        user = request.user
        
        invitation = InvitationGenerate.objects.filter(user=user).first()
        
        if not invitation:
            return Response(
                {
                    'message': 'Invitation code not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InvitationGenerateSerializer(invitation)
        return Response(
            {
                'message': 'Invitation code retrieved successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )


class InvitedUsersView(APIView):
    """
    Get all users invited by the authenticated user - GET
    Returns list of users who used the authenticated user's invitation code
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Invitations'],
        operation_description="""
        Get all users invited by the authenticated user.
        
        Returns a list of all users who have used the authenticated user's invitation code.
        Filtered by sender (the authenticated user).
        
        **Authentication Required:** Yes (JWT Token)
        """,
        responses={
            200: openapi.Response(
                description="Invited users retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Invited users retrieved successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'sender': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'sender_email': openapi.Schema(type=openapi.TYPE_STRING),
                                    'sender_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'receiver': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'receiver_email': openapi.Schema(type=openapi.TYPE_STRING),
                                    'receiver_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                }
                            )
                        ),
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
        }
    )
    def get(self, request):
        """
        Get all users invited by the authenticated user
        Filtered by sender (the authenticated user)
        """
        user = request.user
        
        # Get all invitations where the authenticated user is the sender
        invited_users = InvitationUsers.objects.filter(
            sender=user
        ).select_related('sender', 'receiver').order_by('-created_at')
        
        serializer = InvitationUsersSerializer(invited_users, many=True)
        
        return Response(
            {
                'message': 'Invited users retrieved successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
