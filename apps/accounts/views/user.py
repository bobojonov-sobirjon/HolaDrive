from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers import UserDetailSerializer
from ..models import CustomUser


class UserDetailView(APIView):
    """
    User details endpoint
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Get authenticated user details",
        responses={
            200: openapi.Response(description="User details retrieved successfully"),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    def get(self, request):
        """
        Get current user details with optimized query
        """
        # Optimize query: prefetch groups to avoid N+1 queries
        user = CustomUser.objects.prefetch_related('groups').get(pk=request.user.pk)
        serializer = UserDetailSerializer(user, context={'request': request})
        return Response(
            {
                'message': 'User details retrieved successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Update authenticated user details. Avatar can be uploaded as a file using multipart/form-data.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'date_of_birth': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, enum=['male', 'female', 'other']),
                'avatar': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Avatar image file (use multipart/form-data for file upload)'
                ),
                'address': openapi.Schema(type=openapi.TYPE_STRING),
                'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
            }
        ),
        responses={
            200: openapi.Response(description="User details updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
        },
        consumes=['application/json']
    )
    def put(self, request):
        """
        Update current user details
        """
        serializer = UserDetailSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'User details updated successfully',
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
        tags=['User'],
        operation_description="Partially update authenticated user details",
        request_body=UserDetailSerializer,
        responses={
            200: openapi.Response(description="User details updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    def patch(self, request):
        """
        Partially update current user details
        """
        serializer = UserDetailSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'User details updated successfully',
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


class CustomUserListView(APIView):
    """
    List and create users endpoint (Admin only)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Get list of all users (Admin only)",
        responses={
            200: openapi.Response(description="Users retrieved successfully"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin access required"),
        }
    )
    def get(self, request):
        """
        Get list of all users (Admin only) with optimized query
        """
        if not request.user.is_staff:
            return Response(
                {
                    'message': 'You do not have permission to perform this action',
                    'status': 'error'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Optimize query: prefetch groups to avoid N+1 queries
        # Use only() to select only needed fields for better performance
        users = CustomUser.objects.prefetch_related('groups').only(
            'id', 'email', 'username', 'first_name', 'last_name', 'phone_number',
            'date_of_birth', 'gender', 'avatar', 'address', 'longitude', 'latitude',
            'is_verified', 'is_active', 'created_at', 'updated_at', 'last_login'
        ).order_by('-created_at')
        
        serializer = UserDetailSerializer(users, many=True, context={'request': request})
        return Response(
            {
                'message': 'Users retrieved successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Create a new user (Admin only)",
        request_body=UserDetailSerializer,
        responses={
            201: openapi.Response(description="User created successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin access required"),
        }
    )
    def post(self, request):
        """
        Create a new user (Admin only)
        """
        if not request.user.is_staff:
            return Response(
                {
                    'message': 'You do not have permission to perform this action',
                    'status': 'error'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UserDetailSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    'message': 'User created successfully',
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


class CustomUserDetailByIdView(APIView):
    """
    Retrieve, update, partial update, and delete user endpoint by ID
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk, user):
        """
        Get user object by ID with optimized query
        """
        try:
            # Optimize query: prefetch groups to avoid N+1 queries
            # Use select_related for any ForeignKey relationships if needed
            user_obj = CustomUser.objects.prefetch_related('groups').get(pk=pk)
            # Users can only access their own data unless they are staff
            if not user.is_staff and user != user_obj:
                return None
            return user_obj
        except CustomUser.DoesNotExist:
            return None

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Get user details by ID",
        responses={
            200: openapi.Response(description="User details retrieved successfully"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User not found"),
        }
    )
    def get(self, request, pk):
        """
        Get user details by ID
        """
        user = self.get_object(pk, request.user)
        
        if user is None:
            return Response(
                {
                    'message': 'User not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserDetailSerializer(user, context={'request': request})
        return Response(
            {
                'message': 'User details retrieved successfully',
                'status': 'success',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['User'],
        operation_description="Update user details (full update)",
        request_body=UserDetailSerializer,
        responses={
            200: openapi.Response(description="User updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User not found"),
        }
    )
    def put(self, request, pk):
        """
        Update user details (full update)
        """
        user = self.get_object(pk, request.user)
        
        if user is None:
            return Response(
                {
                    'message': 'User not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserDetailSerializer(
            user,
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'User updated successfully',
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
        tags=['User'],
        operation_description="Partially update user details",
        request_body=UserDetailSerializer,
        responses={
            200: openapi.Response(description="User updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User not found"),
        }
    )
    def patch(self, request, pk):
        """
        Partially update user details
        """
        user = self.get_object(pk, request.user)
        
        if user is None:
            return Response(
                {
                    'message': 'User not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserDetailSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'User updated successfully',
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
        tags=['User'],
        operation_description="Delete user (Admin only)",
        responses={
            204: openapi.Response(description="User deleted successfully"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin access required"),
            404: openapi.Response(description="User not found"),
        }
    )
    def delete(self, request, pk):
        """
        Delete user (Admin only)
        """
        if not request.user.is_staff:
            return Response(
                {
                    'message': 'You do not have permission to perform this action',
                    'status': 'error'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object(pk, request.user)
        
        if user is None:
            return Response(
                {
                    'message': 'User not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.delete()
        return Response(
            {
                'message': 'User deleted successfully',
                'status': 'success'
            },
            status=status.HTTP_204_NO_CONTENT
        )

