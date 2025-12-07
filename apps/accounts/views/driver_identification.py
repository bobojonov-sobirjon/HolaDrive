from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from asgiref.sync import sync_to_async

from ..serializers import DriverIdentificationSerializer
from ..models import DriverIdentification


class DriverIdentificationView(AsyncAPIView):
    """
    Driver identification endpoint - GET, POST, PUT, PATCH
    
    This endpoint allows authenticated drivers to manage their identification documents:
    - Image documents: Proof of Work, Profile Photo, Driver's License, Background Check, etc.
    - Boolean agreements: Terms and Conditions, Legal Agreements
    
    **Only accessible to users with Driver role**
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    async def check_driver_permission(self, request):
        """
        Check if user is a Driver
        """
        user = request.user
        groups = await sync_to_async(list)(user.groups.all())
        group_names = [group.name for group in groups]
        
        if 'Driver' not in group_names:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        return None

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Get current driver's identification documents.
        
        Returns all identification documents and agreements for the authenticated driver.
        If no identification exists, returns a 404 error.
        
        **Authentication Required:** Yes (JWT Token)
        **Role Required:** Driver
        """,
        responses={
            200: openapi.Response(description="Identification retrieved successfully"),
            404: openapi.Response(description="Identification not found"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Driver role required"),
        }
    )
    async def get(self, request):
        """
        Get current driver's identification - ASYNC VERSION
        """
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        try:
            identification = await DriverIdentification.objects.select_related('user').aget(user=request.user)
        except DriverIdentification.DoesNotExist:
            return Response(
                {
                    'message': 'Identification not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DriverIdentificationSerializer(identification, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Identification retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Create or update driver identification documents.
        
        Creates identification if it doesn't exist, or updates existing one.
        Multiple image fields can be uploaded using multipart/form-data.
        
        **Image Fields (optional):**
        - proof_of_work_eligibility
        - profile_photo
        - drivers_license
        - background_check
        - driver_abstract
        - livery_vehicle_registration
        - vehicle_insurance
        - city_tndl
        - elvis_vehicle_inspection
        
        **Boolean Fields (optional):**
        - terms_and_conditions
        - legal_agreements
        
        **Authentication Required:** Yes (JWT Token)
        **Role Required:** Driver
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'proof_of_work_eligibility': openapi.Schema(type=openapi.TYPE_FILE),
                'profile_photo': openapi.Schema(type=openapi.TYPE_FILE),
                'drivers_license': openapi.Schema(type=openapi.TYPE_FILE),
                'background_check': openapi.Schema(type=openapi.TYPE_FILE),
                'driver_abstract': openapi.Schema(type=openapi.TYPE_FILE),
                'livery_vehicle_registration': openapi.Schema(type=openapi.TYPE_FILE),
                'vehicle_insurance': openapi.Schema(type=openapi.TYPE_FILE),
                'city_tndl': openapi.Schema(type=openapi.TYPE_FILE),
                'elvis_vehicle_inspection': openapi.Schema(type=openapi.TYPE_FILE),
                'terms_and_conditions': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'legal_agreements': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={
            200: openapi.Response(description="Identification updated successfully"),
            201: openapi.Response(description="Identification created successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Driver role required"),
        },
        consumes=['multipart/form-data', 'application/json']
    )
    async def post(self, request):
        """
        Create or update driver identification - ASYNC VERSION
        """
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        # Check if identification already exists
        existing = await DriverIdentification.objects.filter(user=request.user).only('id').afirst()
        is_update = existing is not None
        
        if is_update:
            serializer = DriverIdentificationSerializer(
                existing,
                data=request.data,
                partial=True,
                context={'request': request}
            )
        else:
            serializer = DriverIdentificationSerializer(
                data=request.data,
                context={'request': request}
            )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            identification = await sync_to_async(serializer.save)()
            serializer_data = await sync_to_async(lambda: serializer.data)()
            
            response_status = status.HTTP_200_OK if is_update else status.HTTP_201_CREATED
            message = 'Identification updated successfully' if is_update else 'Identification created successfully'
            
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

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Update driver identification (full update).
        
        Updates all identification fields. All fields must be provided.
        
        **Authentication Required:** Yes (JWT Token)
        **Role Required:** Driver
        """,
        request_body=DriverIdentificationSerializer,
        responses={
            200: openapi.Response(description="Identification updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Driver role required"),
            404: openapi.Response(description="Identification not found"),
        },
        consumes=['multipart/form-data', 'application/json']
    )
    async def put(self, request):
        """
        Update driver identification (full update) - ASYNC VERSION
        """
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        try:
            identification = await DriverIdentification.objects.select_related('user').aget(user=request.user)
        except DriverIdentification.DoesNotExist:
            return Response(
                {
                    'message': 'Identification not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DriverIdentificationSerializer(
            identification,
            data=request.data,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            await sync_to_async(serializer.save)()
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Identification updated successfully',
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

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Partially update driver identification.
        
        Updates only the provided fields.
        
        **Authentication Required:** Yes (JWT Token)
        **Role Required:** Driver
        """,
        request_body=DriverIdentificationSerializer,
        responses={
            200: openapi.Response(description="Identification updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Driver role required"),
            404: openapi.Response(description="Identification not found"),
        },
        consumes=['multipart/form-data', 'application/json']
    )
    async def patch(self, request):
        """
        Partially update driver identification - ASYNC VERSION
        """
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        try:
            identification = await DriverIdentification.objects.select_related('user').aget(user=request.user)
        except DriverIdentification.DoesNotExist:
            return Response(
                {
                    'message': 'Identification not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DriverIdentificationSerializer(
            identification,
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
                    'message': 'Identification updated successfully',
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


class CheckIdentificationView(AsyncAPIView):
    """
    Check identification completion status endpoint - GET
    
    Returns True/False for each identification step
    """
    permission_classes = [IsAuthenticated]

    async def check_driver_permission(self, request):
        """
        Check if user is a Driver
        """
        user = request.user
        groups = await sync_to_async(list)(user.groups.all())
        group_names = [group.name for group in groups]
        
        if 'Driver' not in group_names:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        return None

    @swagger_auto_schema(
        tags=['Driver Identification'],
        operation_description="""
        Check identification completion status.
        
        Returns True/False for each identification step, showing which documents are completed.
        
        **Authentication Required:** Yes (JWT Token)
        **Role Required:** Driver
        """,
        responses={
            200: openapi.Response(
                description="Identification status retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'proof_of_work_eligibility': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'profile_photo': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'drivers_license': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'background_check': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'driver_abstract': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'livery_vehicle_registration': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'vehicle_insurance': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'city_tndl': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'elvis_vehicle_inspection': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'terms_and_conditions': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'legal_agreements': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'completed_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'total_steps': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        ),
                    }
                )
            ),
            404: openapi.Response(description="Identification not found"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Driver role required"),
        }
    )
    async def get(self, request):
        """
        Check identification completion status - ASYNC VERSION
        """
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        try:
            identification = await DriverIdentification.objects.select_related('user').aget(user=request.user)
        except DriverIdentification.DoesNotExist:
            # Return all False if identification doesn't exist
            status_data = {
                'proof_of_work_eligibility': False,
                'profile_photo': False,
                'drivers_license': False,
                'background_check': False,
                'driver_abstract': False,
                'livery_vehicle_registration': False,
                'vehicle_insurance': False,
                'city_tndl': False,
                'elvis_vehicle_inspection': False,
                'terms_and_conditions': False,
                'legal_agreements': False,
                'completed_count': 0,
                'total_steps': 11,
            }
            return Response(
                {
                    'message': 'Identification status retrieved successfully',
                    'status': 'success',
                    'data': status_data
                },
                status=status.HTTP_200_OK
            )
        
        # Get completion status
        completion_status = await sync_to_async(identification.get_completion_status)()
        completed_count = await sync_to_async(identification.get_completion_count)()
        total_steps = await sync_to_async(identification.get_total_steps)()
        
        status_data = {
            **completion_status,
            'completed_count': completed_count,
            'total_steps': total_steps,
        }
        
        return Response(
            {
                'message': 'Identification status retrieved successfully',
                'status': 'success',
                'data': status_data
            },
            status=status.HTTP_200_OK
        )

