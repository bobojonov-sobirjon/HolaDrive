from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers import PinVerificationForUserSerializer
from ..models import PinVerificationForUser


class PinVerificationForUserView(APIView):
    """
    PIN verification endpoint - POST and GET
    Creates or updates PIN for the authenticated user (only one PIN per user)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['PIN Verification'],
        operation_description="""
        Create or update PIN for the authenticated user.
        
        **Important:** This endpoint creates a PIN if it doesn't exist, or updates it if it already exists.
        PIN cannot be deleted, only changed.
        
        **Request Body:**
        - pin: 4-digit PIN code (required)
        
        **Authentication Required:** Yes (JWT Token)
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['pin'],
            properties={
                'pin': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    minLength=4,
                    maxLength=4,
                    example='1234',
                    description='4-digit PIN code'
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description="PIN updated successfully (if PIN already exists)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="PIN updated successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                                'pin': openapi.Schema(type=openapi.TYPE_STRING, example="1234"),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            201: openapi.Response(
                description="PIN created successfully (if PIN doesn't exist)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="PIN created successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                                'pin': openapi.Schema(type=openapi.TYPE_STRING, example="1234"),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
        }
    )
    def post(self, request):
        """
        Create or update PIN for the authenticated user
        Creates if doesn't exist, updates if exists
        """
        user = request.user
        
        # Check if PIN already exists
        pin_verification = PinVerificationForUser.objects.filter(user=user).first()
        
        serializer = PinVerificationForUserSerializer(
            pin_verification,
            data=request.data,
            context={'request': request},
            partial=pin_verification is not None
        )
        
        if serializer.is_valid():
            if pin_verification:
                # Update existing PIN
                serializer.save()
                return Response(
                    {
                        'message': 'PIN updated successfully',
                        'status': 'success',
                        'data': serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                # Create new PIN
                pin_verification = serializer.save()
                return Response(
                    {
                        'message': 'PIN created successfully',
                        'status': 'success',
                        'data': serializer.data
                    },
                    status=status.HTTP_201_CREATED
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
        tags=['PIN Verification'],
        operation_description="""
        Get PIN for the authenticated user.
        
        Returns the PIN that belongs to the authenticated user.
        If no PIN exists, returns a 404 error.
        
        **Authentication Required:** Yes (JWT Token)
        """,
        responses={
            200: openapi.Response(
                description="PIN retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="PIN retrieved successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                                'pin': openapi.Schema(type=openapi.TYPE_STRING, example="1234"),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        ),
                    }
                )
            ),
            404: openapi.Response(
                description="PIN not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="PIN not found"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized - Invalid or missing JWT token"),
        }
    )
    def get(self, request):
        """
        Get PIN for the authenticated user
        Filtered by user (authenticated user)
        """
        user = request.user
        
        pin_verification = PinVerificationForUser.objects.filter(user=user).first()
        
        if not pin_verification:
            return Response(
                {
                    'message': 'PIN not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PinVerificationForUserSerializer(pin_verification, context={'request': request})
        return Response(
            {
                'message': 'PIN retrieved successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
