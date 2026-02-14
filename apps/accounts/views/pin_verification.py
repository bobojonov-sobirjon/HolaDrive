from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from ..serializers import PinVerificationForUserSerializer
from ..models import PinVerificationForUser

class PinVerificationForUserView(AsyncAPIView):
    """
    PIN verification endpoint - POST and GET
    Creates or updates PIN for the authenticated user (only one PIN per user)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['PIN Verification'], summary='Create/update PIN', description='Create or update 4-digit PIN for the authenticated user. Request: pin (required).')
    async def post(self, request):
        """
        Create or update PIN for the authenticated user - ASYNC VERSION
        Creates if doesn't exist, updates if exists
        """
        user = request.user
        
        # Check if PIN already exists (async)
        pin_verification = await PinVerificationForUser.objects.filter(user=user).afirst()
        
        serializer = PinVerificationForUserSerializer(
            pin_verification,
            data=request.data,
            context={'request': request},
            partial=pin_verification is not None
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            if pin_verification:
                # Update existing PIN
                await sync_to_async(serializer.save)()
                serializer_data = await sync_to_async(lambda: serializer.data)()
                return Response(
                    {
                        'message': 'PIN updated successfully',
                        'status': 'success',
                        'data': serializer_data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                # Create new PIN
                pin_verification = await sync_to_async(serializer.save)()
                serializer_data = await sync_to_async(lambda: serializer.data)()
                return Response(
                    {
                        'message': 'PIN created successfully',
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

    @extend_schema(tags=['PIN Verification'], summary='Get PIN', description='Get PIN for the authenticated user.')
    async def get(self, request):
        """
        Get PIN for the authenticated user - ASYNC VERSION
        Filtered by user (authenticated user)
        """
        user = request.user
        
        pin_verification = await PinVerificationForUser.objects.filter(user=user).afirst()
        
        if not pin_verification:
            return Response(
                {
                    'message': 'PIN not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PinVerificationForUserSerializer(pin_verification, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'PIN retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )
