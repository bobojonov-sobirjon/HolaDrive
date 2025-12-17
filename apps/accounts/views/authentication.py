from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from asgiref.sync import sync_to_async

from ..serializers import (
    RegistrationSerializer, LoginSerializer, SendVerificationCodeSerializer,
    VerifyCodeSerializer, ResetPasswordRequestSerializer, VerifyResetCodeSerializer,
    ResetPasswordConfirmSerializer
)
from ..models import VerificationCode, PasswordResetToken, InvitationGenerate, InvitationUsers, UserDeviceToken
from ..services import send_verification_code


class RegistrationView(AsyncAPIView):
    """
    User registration endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="""
        Register a new user account.

        Optional push notification fields:
        - device_token: string (FCM/APNs token)
        - device_type: one of ['android', 'ios', 'web']
        """,
        request_body=RegistrationSerializer,
        responses={
            201: openapi.Response(
                description="User successfully created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="User registered successfully"),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'full_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'groups': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        }
                                    )
                                ),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_verified': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
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
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
        }
    )
    async def post(self, request):
        """
        Register a new user - ASYNC VERSION
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("REGISTRATION DEBUG: Starting registration process")
        logger.info(f"REGISTRATION DEBUG: Request data: {request.data}")
        
        serializer = RegistrationSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            logger.info("REGISTRATION DEBUG: Serializer is valid")
            
            # Get invitation_code from request data (before saving user)
            invitation_code = request.data.get('invitation_code', '').strip() if request.data.get('invitation_code') else ''
            
            # Save user (invitation_code is processed here, device token handled in serializer)
            user = await sync_to_async(serializer.save)()
            logger.info(f"REGISTRATION DEBUG: User created - ID: {user.id}, Email: {user.email}")
            
            # Process invitation code if provided
            invitation_message = None
            if invitation_code:
                # Check if user has already been invited before (async)
                already_invited = await sync_to_async(InvitationUsers.objects.filter(receiver=user).exists)()
                
                if already_invited:
                    # User has already been invited before, cannot use invitation code again
                    invitation_message = "Bu invitation code bilan kirib bo'lmaydi, oldin kirgansiz"
                else:
                    # User hasn't been invited before, can use invitation code
                    try:
                        invitation_generate = await InvitationGenerate.objects.select_related('user').aget(
                            invite_code=invitation_code
                        )
                        sender = invitation_generate.user
                        
                        # Don't allow user to invite themselves
                        if sender.id == user.id:
                            invitation_message = "O'zingizni taklif qila olmaysiz"
                        else:
                            await sync_to_async(InvitationUsers.objects.create)(
                                sender=sender,
                                receiver=user,
                                is_active=True
                            )
                            invitation_message = "Invitation code muvaffaqiyatli qo'llanildi"
                    except InvitationGenerate.DoesNotExist:
                        invitation_message = "Noto'g'ri invitation code"
            
            # Send verification code to email (sync function)
            email = user.email
            if email:
                logger.info(f"REGISTRATION DEBUG: Attempting to send verification code to: {email}")
                logger.info(f"REGISTRATION DEBUG: Email settings - HOST: {settings.EMAIL_HOST}, PORT: {settings.EMAIL_PORT}")
                logger.info(f"REGISTRATION DEBUG: Email settings - FROM: {settings.DEFAULT_FROM_EMAIL}")
                logger.info(f"REGISTRATION DEBUG: Email settings - BACKEND: {settings.EMAIL_BACKEND}")
                
                verification_code, success, error = await sync_to_async(send_verification_code)(
                    user=user,
                    email=email
                )
                
                logger.info(f"REGISTRATION DEBUG: Verification code created - Code: {verification_code.code}, ID: {verification_code.id}")
                logger.info(f"REGISTRATION DEBUG: Email send result - Success: {success}, Error: {error}")
                
                if not success:
                    logger.error(f"REGISTRATION DEBUG: Failed to send verification code to {email}: {error}")
                else:
                    logger.info(f"REGISTRATION DEBUG: Verification code sent successfully to {email}")
            else:
                logger.warning("REGISTRATION DEBUG: No email provided for user")
            
            logger.info("REGISTRATION DEBUG: Registration completed successfully")
            logger.info("=" * 80)
            
            user_data = await sync_to_async(serializer.to_representation)(user)
            
            response_data = {
                'message': 'User registered successfully. Please check your email for verification code.',
                'status': 'success',
                'data': user_data,
                'debug': {
                    'verification_code_sent': success if email else False,
                    'verification_code': verification_code.code if email and success else None,
                    'error': error if email and not success else None
                } if settings.DEBUG else None
            }
            
            # Add invitation message if there is one
            if invitation_message:
                response_data['data']['invitation_message'] = invitation_message
            
            return Response(
                response_data,
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


class LoginView(AsyncAPIView):
    """
    User login endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="""
        Login with email/phone and password.

        Optional push notification fields:
        - device_token: string (FCM/APNs token)
        - device_type: one of ['android', 'ios', 'web']
        """,
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(description="Login successful"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    async def post(self, request):
        """
        Login user with email/phone and password, then send verification code - ASYNC VERSION
        """
        serializer = LoginSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            user = validated_data['user']
            email = validated_data.get('email')
            phone_number = validated_data.get('phone_number')
            
            contact_email = email or user.email
            contact_phone = phone_number or user.phone_number
            verification_code, success, error = await sync_to_async(send_verification_code)(
                user=user,
                email=contact_email if email or (not phone_number and user.email) else None,
                phone_number=contact_phone if phone_number or (not email and user.phone_number) else None
            )
            
            if not success:
                show_code = phone_number or contact_phone or settings.DEBUG
                return Response(
                    {
                        'message': 'Failed to send verification code',
                        'status': 'error',
                        'errors': {'verification': [error] if error else ['Failed to send verification code']},
                        'data': {
                            'code': verification_code.code if show_code else None,
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Store/update device token if provided
            device_token = (validated_data.get('device_token') or '').strip()
            device_type = validated_data.get('device_type')
            if device_token and device_type:
                await sync_to_async(UserDeviceToken.upsert_token)(
                    user=user,
                    token=device_token,
                    mobile=device_type,
                )

            response_data = {
                'message': 'Verification code sent successfully',
                'status': 'success',
                'data': {
                    'expires_in': 600,
                    'sent_to': contact_email if (email or (not phone_number and user.email)) else contact_phone
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class SendVerificationCodeView(AsyncAPIView):
    """
    Send verification code endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Send verification code to email or phone",
        request_body=SendVerificationCodeSerializer,
        responses={
            200: openapi.Response(description="Verification code sent successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    async def post(self, request):
        """
        Send verification code to user's email or phone - ASYNC VERSION
        """
        serializer = SendVerificationCodeSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            user = validated_data['user']
            email = validated_data.get('email')
            phone_number = validated_data.get('phone_number')
            
            verification_code, success, error = await sync_to_async(send_verification_code)(
                user=user,
                email=email,
                phone_number=phone_number
            )
            
            if not success:
                show_code = phone_number or settings.DEBUG
                return Response(
                    {
                        'message': 'Failed to send verification code',
                        'status': 'error',
                        'errors': {'verification': [error] if error else ['Failed to send verification code']},
                        'data': {
                            'code': verification_code.code if show_code else None,
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(
                {
                    'message': 'Verification code sent successfully',
                    'status': 'success',
                    'data': {
                        'expires_in': 600,
                        'sent_to': email or phone_number
                    }
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


class VerifyCodeView(AsyncAPIView):
    """
    Verify code endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Verify code and login user",
        request_body=VerifyCodeSerializer,
        responses={
            200: openapi.Response(description="Code verified successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    async def post(self, request):
        """
        Verify code and login user - ASYNC VERSION
        """
        serializer = VerifyCodeSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            user = validated_data['user']
            verification_code = validated_data['verification_code']
            
            verification_code.is_used = True
            await sync_to_async(verification_code.save)()
            
            user.is_verified = True
            await sync_to_async(user.save)()
            
            refresh = await sync_to_async(RefreshToken.for_user)(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            return Response(
                {
                    'message': 'Code verified successfully',
                    'status': 'success',
                    'data': {
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'user': {
                            'id': user.id,
                            'email': user.email,
                            'full_name': await sync_to_async(user.get_full_name)(),
                            'username': user.username,
                            'is_verified': user.is_verified,
                        }
                    }
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


class ResetPasswordRequestView(AsyncAPIView):
    """
    Request password reset endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Request password reset",
        request_body=ResetPasswordRequestSerializer,
        responses={
            200: openapi.Response(description="Password reset email sent successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    async def post(self, request):
        """
        Send password reset code via email or SMS - ASYNC VERSION
        """
        serializer = ResetPasswordRequestSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            user = validated_data['user']
            email = validated_data.get('email')
            phone_number = validated_data.get('phone_number')
            
            contact_email = email or user.email
            contact_phone = phone_number or user.phone_number
            verification_code, success, error = await sync_to_async(send_verification_code)(
                user=user,
                email=contact_email if (email or (not phone_number and user.email)) else None,
                phone_number=contact_phone if (phone_number or (not email and user.phone_number)) else None
            )
            
            if not success:
                show_code = phone_number or contact_phone or settings.DEBUG
                return Response(
                    {
                        'message': 'Failed to send verification code',
                        'status': 'error',
                        'errors': {'verification': [error] if error else ['Failed to send verification code']},
                        'data': {
                            'code': verification_code.code if show_code else None,
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(
                {
                    'message': 'Password reset code sent successfully',
                    'status': 'success',
                    'data': {
                        'expires_in': 600,
                        'sent_to': contact_email if (email or (not phone_number and user.email)) else contact_phone,
                        'message': 'Enter the verification code to reset your password'
                    }
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


class VerifyResetCodeView(AsyncAPIView):
    """
    Verify reset password code endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Verify reset password code and get JWT tokens (access_token and refresh_token)",
        request_body=VerifyResetCodeSerializer,
        responses={
            200: openapi.Response(description="Code verified successfully - JWT tokens returned"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    async def post(self, request):
        """
        Verify reset password code and generate JWT token - ASYNC VERSION
        """
        serializer = VerifyResetCodeSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            user = validated_data['user']
            verification_code = validated_data['verification_code']
            
            verification_code.is_used = True
            await sync_to_async(verification_code.save)()
            
            # Generate JWT tokens (same as login)
            refresh = await sync_to_async(RefreshToken.for_user)(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            return Response(
                {
                    'message': 'Code verified successfully',
                    'status': 'success',
                    'data': {
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'expires_in': 86400  # 24 hours
                    }
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


class ResetPasswordConfirmView(AsyncAPIView):
    """
    Confirm password reset endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Confirm password reset with token",
        request_body=ResetPasswordConfirmSerializer,
        responses={
            200: openapi.Response(description="Password reset successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    async def post(self, request):
        """
        Reset password with reset token - ASYNC VERSION
        """
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            user = validated_data['user']
            reset_token = validated_data['reset_token']
            new_password = validated_data['new_password']
            
            await sync_to_async(user.set_password)(new_password)
            await sync_to_async(user.save)()
            
            reset_token.is_used = True
            await sync_to_async(reset_token.save)()
            
            return Response(
                {
                    'message': 'Password reset successfully',
                    'status': 'success',
                    'data': {
                        'message': 'Your password has been reset successfully'
                    }
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

