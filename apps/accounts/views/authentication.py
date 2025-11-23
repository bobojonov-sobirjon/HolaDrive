from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from ..serializers import (
    RegistrationSerializer, LoginSerializer, SendVerificationCodeSerializer,
    VerifyCodeSerializer, ResetPasswordRequestSerializer, VerifyResetCodeSerializer,
    ResetPasswordConfirmSerializer
)
from ..models import VerificationCode, PasswordResetToken, InvitationGenerate, InvitationUsers
from ..services import send_verification_code


class RegistrationView(APIView):
    """
    User registration endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Register a new user account",
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
    def post(self, request):
        """
        Register a new user
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("REGISTRATION DEBUG: Starting registration process")
        logger.info(f"REGISTRATION DEBUG: Request data: {request.data}")
        
        serializer = RegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            logger.info("REGISTRATION DEBUG: Serializer is valid")
            user = serializer.save()
            logger.info(f"REGISTRATION DEBUG: User created - ID: {user.id}, Email: {user.email}")
            
            # Send verification code to email
            email = user.email
            if email:
                logger.info(f"REGISTRATION DEBUG: Attempting to send verification code to: {email}")
                logger.info(f"REGISTRATION DEBUG: Email settings - HOST: {settings.EMAIL_HOST}, PORT: {settings.EMAIL_PORT}")
                logger.info(f"REGISTRATION DEBUG: Email settings - FROM: {settings.DEFAULT_FROM_EMAIL}")
                logger.info(f"REGISTRATION DEBUG: Email settings - BACKEND: {settings.EMAIL_BACKEND}")
                
                verification_code, success, error = send_verification_code(
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
            
            return Response(
                {
                    'message': 'User registered successfully. Please check your email for verification code.',
                    'status': 'success',
                    'data': serializer.to_representation(user),
                    'debug': {
                        'verification_code_sent': success if email else False,
                        'verification_code': verification_code.code if email and success else None,
                        'error': error if email and not success else None
                    } if settings.DEBUG else None
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


class LoginView(APIView):
    """
    User login endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Login with email/phone and password",
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(description="Login successful"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    def post(self, request):
        """
        Login user with email/phone and password, then send verification code
        """
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            email = serializer.validated_data.get('email')
            phone_number = serializer.validated_data.get('phone_number')
            
            contact_email = email or user.email
            contact_phone = phone_number or user.phone_number
            verification_code, success, error = send_verification_code(
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
            
            response_data = {
                'message': 'Verification code sent successfully',
                'status': 'success',
                'data': {
                    'expires_in': 600,
                    'sent_to': contact_email if (email or (not phone_number and user.email)) else contact_phone
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class SendVerificationCodeView(APIView):
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
    def post(self, request):
        """
        Send verification code to user's email or phone
        """
        serializer = SendVerificationCodeSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            email = serializer.validated_data.get('email')
            phone_number = serializer.validated_data.get('phone_number')
            
            verification_code, success, error = send_verification_code(
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
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class VerifyCodeView(APIView):
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
    def post(self, request):
        """
        Verify code and login user
        """
        serializer = VerifyCodeSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            verification_code = serializer.validated_data['verification_code']
            invitation_code = serializer.validated_data.get('invitation_code', '').strip()
            
            verification_code.is_used = True
            verification_code.save()
            
            user.is_verified = True
            user.save()
            
            # Check if user has already been invited before
            already_invited = InvitationUsers.objects.filter(receiver=user).exists()
            
            invitation_message = None
            if invitation_code:
                if already_invited:
                    # User has already been invited before, cannot use invitation code again
                    invitation_message = "Bu invitation code bilan kirib bo'lmaydi, oldin kirgansiz"
                else:
                    # User hasn't been invited before, can use invitation code
                    try:
                        invitation_generate = InvitationGenerate.objects.select_related('user').get(
                            invite_code=invitation_code
                        )
                        sender = invitation_generate.user
                        
                        # Don't allow user to invite themselves
                        if sender.id == user.id:
                            invitation_message = "O'zingizni taklif qila olmaysiz"
                        else:
                            InvitationUsers.objects.create(
                                sender=sender,
                                receiver=user,
                                is_active=True
                            )
                    except InvitationGenerate.DoesNotExist:
                        invitation_message = "Noto'g'ri invitation code"
            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            response_data = {
                'message': 'Code verified successfully',
                'status': 'success',
                'data': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'full_name': user.get_full_name(),
                        'username': user.username,
                        'is_verified': user.is_verified,
                    }
                }
            }
            
            # Add invitation message if there is one
            if invitation_message:
                response_data['data']['invitation_message'] = invitation_message
            
            return Response(
                response_data,
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


class ResetPasswordRequestView(APIView):
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
    def post(self, request):
        """
        Send password reset code via email or SMS
        """
        serializer = ResetPasswordRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            email = serializer.validated_data.get('email')
            phone_number = serializer.validated_data.get('phone_number')
            
            contact_email = email or user.email
            contact_phone = phone_number or user.phone_number
            verification_code, success, error = send_verification_code(
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
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class VerifyResetCodeView(APIView):
    """
    Verify reset password code endpoint
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Verify reset password code and get reset token",
        request_body=VerifyResetCodeSerializer,
        responses={
            200: openapi.Response(description="Code verified successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    def post(self, request):
        """
        Verify reset password code and generate reset token
        """
        serializer = VerifyResetCodeSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            verification_code = serializer.validated_data['verification_code']
            
            verification_code.is_used = True
            verification_code.save()
            
            reset_token = PasswordResetToken.objects.create(user=user)
            
            return Response(
                {
                    'message': 'Code verified successfully',
                    'status': 'success',
                    'data': {
                        'token': reset_token.token,
                        'expires_in': 86400
                    }
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


class ResetPasswordConfirmView(APIView):
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
    def post(self, request):
        """
        Reset password with reset token
        """
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            reset_token = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']
            
            user.set_password(new_password)
            user.save()
            
            reset_token.is_used = True
            reset_token.save()
            
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
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

