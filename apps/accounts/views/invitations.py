from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from ..serializers import InvitationGenerateSerializer, InvitationUsersSerializer
from ..models import InvitationGenerate, InvitationUsers

class InvitationGenerateView(AsyncAPIView):
    """
    Invitation generation endpoint - POST only
    Creates an invitation code for the authenticated user (only once)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Invitations'], summary='Generate invitation code', description='Generate invitation code for the authenticated user. Only once per user; if exists returns existing code.')
    async def post(self, request):
        """
        Generate invitation code for the authenticated user - ASYNC VERSION
        Only creates once - if already exists, returns existing code
        """
        user = request.user
        
        # Check if invitation code already exists (async)
        invitation = await InvitationGenerate.objects.filter(user=user).afirst()
        
        if invitation:
            # Return existing invitation code
            serializer = InvitationGenerateSerializer(invitation)
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Invitation code retrieved successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_200_OK
            )
        
        # Create new invitation code (async)
        invitation = await sync_to_async(InvitationGenerate.objects.create)(user=user)
        serializer = InvitationGenerateSerializer(invitation)
        serializer_data = await sync_to_async(lambda: serializer.data)()
        
        return Response(
            {
                'message': 'Invitation code created successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_201_CREATED
        )

class InvitationGetView(AsyncAPIView):
    """
    Get invitation code for the authenticated user - GET
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Invitations'], summary='Get invitation code', description='Get invitation code for the authenticated user.')
    async def get(self, request):
        """
        Get invitation code for the authenticated user - ASYNC VERSION
        """
        user = request.user
        
        invitation = await InvitationGenerate.objects.filter(user=user).afirst()
        
        if not invitation:
            return Response(
                {
                    'message': 'Invitation code not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InvitationGenerateSerializer(invitation)
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Invitation code retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

class InvitedUsersView(AsyncAPIView):
    """
    Get all users invited by the authenticated user - GET
    Returns list of users who used the authenticated user's invitation code
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Invitations'], summary='Invited users list', description="Get all users invited by the authenticated user (who used this user's invitation code).")
    async def get(self, request):
        """
        Get all users invited by the authenticated user - ASYNC VERSION
        Filtered by sender (the authenticated user)
        """
        user = request.user
        
        # Get all invitations where the authenticated user is the sender (async)
        invited_users_queryset = InvitationUsers.objects.filter(
            sender=user
        ).select_related('sender', 'receiver').order_by('-created_at')
        
        invited_users = await sync_to_async(list)(invited_users_queryset)
        
        serializer = InvitationUsersSerializer(invited_users, many=True)
        serializer_data = await sync_to_async(lambda: serializer.data)()
        
        return Response(
            {
                'message': 'Invited users retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )
