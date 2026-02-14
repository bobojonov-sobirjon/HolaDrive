from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from ..serializers import UserDetailSerializer
from ..models import CustomUser


class UserDetailView(AsyncAPIView):
    """
    User details endpoint
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=['User'], summary='Get user details', description='Get authenticated user details.')
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

    @extend_schema(tags=['User'], summary='Update user', description='Update authenticated user details. Use multipart/form-data. Avatar: file upload.')
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

    @extend_schema(tags=['User'], summary='Partial update user', description='Partially update authenticated user details. Use multipart/form-data.')
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


class UserAvatarUpdateView(AsyncAPIView):
    """
    Update only the authenticated user's avatar (profile picture).
    Use multipart/form-data with field name: avatar
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=['User'], summary='Update avatar', description='Update profile picture (avatar). Use multipart/form-data, field name: avatar.')
    async def put(self, request):
        return await self._update_avatar(request)

    @extend_schema(tags=['User'], summary='Update avatar (PATCH)', description='Update profile picture (avatar). Use multipart/form-data, field name: avatar.')
    async def patch(self, request):
        return await self._update_avatar(request)

    async def _update_avatar(self, request):
        avatar_file = request.FILES.get('avatar')
        if not avatar_file:
            return Response(
                {
                    'message': 'Validation error',
                    'status': 'error',
                    'errors': {'avatar': ['Avatar image file is required.']}
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        user = request.user
        user.avatar = avatar_file
        await sync_to_async(user.save)()
        serializer = UserDetailSerializer(user, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Avatar updated successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )