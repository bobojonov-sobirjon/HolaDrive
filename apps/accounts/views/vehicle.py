from rest_framework import status
from apps.common.views import AsyncAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from ..serializers import VehicleDetailsSerializer, VehicleImageSerializer
from ..models import VehicleDetails, VehicleImages


class VehicleDetailsView(AsyncAPIView):
    """
    Vehicle details endpoint - GET, POST
    
    This endpoint allows authenticated drivers to manage their vehicle information:
    - GET: Get current driver's vehicle details
    - POST: Create new vehicle details with images
    
    **Only accessible to users with Driver role**
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    async def check_driver_permission(self, request):
        """
        Check if user is a Driver
        """
        user = request.user
        # Check if user is in Driver group (async)
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

    @extend_schema(tags=['Vehicle Details'], summary='Get vehicle details', description="Get current driver's vehicle details. Role: Driver.")
    async def get(self, request):
        """
        Get current driver's vehicle details - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        vehicle = await VehicleDetails.objects.filter(
            user=request.user
        ).prefetch_related('images').select_related('user').afirst()
        
        if not vehicle:
            return Response(
                {
                    'message': 'Vehicle details not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VehicleDetailsSerializer(vehicle, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Vehicle details retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(tags=['Vehicle Details'], summary='Create vehicle', description='Create vehicle details with images. multipart/form-data: brand, model, year_of_manufacture, vin (required); vehicle_condition, default_ride_type, supported_ride_types, images_data (optional). Role: Driver.')
    async def post(self, request):
        """
        Create vehicle details with multiple images - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        # Check if vehicle already exists for this user
        existing_vehicle = await VehicleDetails.objects.filter(
            user=request.user
        ).only('id').afirst()
        
        if existing_vehicle:
            return Response(
                {
                    'message': 'Vehicle details already exist. Use PUT or PATCH to update.',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle multiple images from request.FILES
        # Multipart/form-data da files request.FILES da bo'ladi
        images_data = []
        
        # Postman'da multiple files yuborilganda, ular images_data nomi bilan yuboriladi
        # Django QueryDict ularni list sifatida saqlaydi
        # getlist() method bilan barcha files ni olamiz
        if hasattr(request.FILES, 'getlist'):
            # images_data[] array notation
            images_list = request.FILES.getlist('images_data[]')
            if images_list:
                images_data.extend([img for img in images_list if img])
            
            # images_data (multiple files with same key)
            images_list = request.FILES.getlist('images_data')
            if images_list:
                images_data.extend([img for img in images_list if img])
        
        # If no array notation, check for indexed notation (images_data[0], images_data[1], etc.)
        if not images_data:
            i = 0
            while f'images_data[{i}]' in request.FILES:
                img = request.FILES[f'images_data[{i}]']
                if img:
                    images_data.append(img)
                i += 1
        
        # If still no images, check for single images_data field in FILES
        if not images_data and 'images_data' in request.FILES:
            img = request.FILES['images_data']
            if isinstance(img, list):
                images_data.extend([i for i in img if i])
            elif img:
                images_data.append(img)
        
        # Also check in request.data (for compatibility)
        if not images_data and 'images_data' in request.data:
            img = request.data['images_data']
            if isinstance(img, list):
                images_data.extend([i for i in img if i and hasattr(i, 'read')])
            elif img and hasattr(img, 'read'):
                images_data.append(img)
        
        # Prepare data for serializer (images_data ni olib tashlaymiz)
        # QueryDict dan to'g'ri qiymatlarni olish
        data = {}
        for key, value in request.data.items():
            # images_data related keys ni o'tkazib yuboramiz
            if key == 'images_data' or key == 'images_data[]' or key.startswith('images_data['):
                continue
            
            # QueryDict dan birinchi qiymatni olamiz (agar list bo'lsa)
            if isinstance(value, list) and len(value) > 0:
                data[key] = value[0]
            else:
                data[key] = value
        
        # Multipart/form-data da barcha values string sifatida keladi
        # year_of_manufacture ni int ga convert qilish kerak
        if 'year_of_manufacture' in data:
            try:
                data['year_of_manufacture'] = int(data['year_of_manufacture'])
            except (ValueError, TypeError):
                pass  # Serializer o'zi validate qiladi
        
        serializer = VehicleDetailsSerializer(
            data=data,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Serializer'da images_data ni validated_data ga qo'shamiz
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            if images_data:
                validated_data['images_data'] = images_data
            
            # Vehicle yaratish
            user = request.user
            validated_data['user'] = user
            
            # supported_ride_types ni alohida olish (ManyToMany field)
            supported_ride_types = validated_data.pop('supported_ride_types', [])
            vehicle_condition = validated_data.get('vehicle_condition', VehicleDetails.VehicleCondition.GOOD)
            default_ride_type = validated_data.get('default_ride_type', None)
            
            vehicle = await sync_to_async(VehicleDetails.objects.create)(
                brand=validated_data['brand'],
                model=validated_data['model'],
                year_of_manufacture=validated_data['year_of_manufacture'],
                vin=validated_data['vin'],
                vehicle_condition=vehicle_condition,
                default_ride_type=default_ride_type,
                user=user
            )
            
            # supported_ride_types ni qo'shish (ManyToMany)
            if supported_ride_types:
                await sync_to_async(vehicle.supported_ride_types.set)(supported_ride_types)
            # Agar supported_ride_types bo'sh bo'lsa, save() metodi avtomatik suggestion qiladi
            
            # Images yaratish
            if images_data:
                for image in images_data:
                    if image:
                        await sync_to_async(VehicleImages.objects.create)(
                            vehicle=vehicle,
                            image=image
                        )
            
            # Serialize qilish
            serializer = VehicleDetailsSerializer(vehicle, context={'request': request})
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Vehicle details created successfully',
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


class VehicleDetailView(AsyncAPIView):
    """
    Vehicle detail endpoint - GET, PUT, DELETE by ID
    
    This endpoint allows authenticated drivers to manage vehicle information by ID:
    - Brand, Model, Year of Manufacture, VIN
    - Multiple vehicle images
    
    **Only accessible to users with Driver role**
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    async def check_driver_permission(self, request):
        """
        Check if user is a Driver
        """
        user = request.user
        # Check if user is in Driver group (async)
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

    async def get_object(self, pk, user):
        """
        Get vehicle object by ID with permission check
        """
        try:
            vehicle = await VehicleDetails.objects.prefetch_related('images').select_related('user').aget(pk=pk)
            # Drivers can only access their own vehicles
            if vehicle.user != user:
                return None
            return vehicle
        except VehicleDetails.DoesNotExist:
            return None

    @extend_schema(tags=['Vehicle Details'], summary='Get vehicle by ID', description='Get vehicle details by ID. Drivers can only access their own vehicles. Role: Driver.')
    async def get(self, request, pk):
        """
        Get vehicle details by ID - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        vehicle = await self.get_object(pk, request.user)
        
        if not vehicle:
            return Response(
                {
                    'message': 'Vehicle details not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VehicleDetailsSerializer(vehicle, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Vehicle details retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(tags=['Vehicle Details'], summary='Update vehicle', description='Update vehicle details by ID. multipart/form-data. Can send only images_data to add images. Role: Driver.')
    async def put(self, request, pk):
        """
        Update vehicle details by ID (full update) - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        vehicle = await self.get_object(pk, request.user)
        
        if not vehicle:
            return Response(
                {
                    'message': 'Vehicle details not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle multiple images from request.FILES
        images_data = []
        
        # Postman'da multiple files yuborilganda, ular images_data nomi bilan yuboriladi
        # Django QueryDict ularni list sifatida saqlaydi
        # getlist() method bilan barcha files ni olamiz
        if hasattr(request.FILES, 'getlist'):
            # images_data[] array notation
            images_list = request.FILES.getlist('images_data[]')
            if images_list:
                images_data.extend([img for img in images_list if img])
            
            # images_data (multiple files with same key)
            images_list = request.FILES.getlist('images_data')
            if images_list:
                images_data.extend([img for img in images_list if img])
        
        # If no array notation, check for indexed notation (images_data[0], images_data[1], etc.)
        if not images_data:
            i = 0
            while f'images_data[{i}]' in request.FILES:
                img = request.FILES[f'images_data[{i}]']
                if img:
                    images_data.append(img)
                i += 1
        
        # If still no images, check for single images_data field in FILES
        if not images_data and 'images_data' in request.FILES:
            img = request.FILES['images_data']
            if isinstance(img, list):
                images_data.extend([i for i in img if i])
            elif img:
                images_data.append(img)
        
        # Also check in request.data (for compatibility)
        if not images_data and 'images_data' in request.data:
            img = request.data['images_data']
            if isinstance(img, list):
                images_data.extend([i for i in img if i and hasattr(i, 'read')])
            elif img and hasattr(img, 'read'):
                images_data.append(img)
        
        # Prepare data for serializer (images_data ni olib tashlaymiz)
        # QueryDict dan to'g'ri qiymatlarni olish
        data = {}
        for key, value in request.data.items():
            # images_data related keys ni o'tkazib yuboramiz
            if key == 'images_data' or key == 'images_data[]' or key.startswith('images_data['):
                continue
            
            # QueryDict dan birinchi qiymatni olamiz (agar list bo'lsa)
            if isinstance(value, list) and len(value) > 0:
                data[key] = value[0]
            else:
                data[key] = value
        
        # Agar hech narsa yuborilmagan bo'lsa, error qaytaramiz
        if not data and not images_data:
            return Response(
                {
                    'message': 'No data provided for update. Please provide at least one field or images.',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Agar faqat images_data yuborilgan bo'lsa (boshqa fieldlar yo'q), faqat images qo'shamiz
        if not data and images_data:
            # Faqat images qo'shish
            for image in images_data:
                if image:
                    await sync_to_async(VehicleImages.objects.create)(
                        vehicle=vehicle,
                        image=image
                    )
            
            # Vehicle ni refresh qilamiz
            await sync_to_async(vehicle.refresh_from_db)()
            serializer = VehicleDetailsSerializer(vehicle, context={'request': request})
            serialized_data = await sync_to_async(lambda: serializer.data)()
            
            return Response(
                {
                    'message': 'Images added successfully',
                    'status': 'success',
                    'data': serialized_data
                },
                status=status.HTTP_200_OK
            )
        
        # Agar boshqa fieldlar yuborilgan bo'lsa, ularni update qilamiz
        # Multipart/form-data da barcha values string sifatida keladi
        # year_of_manufacture ni int ga convert qilish kerak
        if 'year_of_manufacture' in data:
            try:
                data['year_of_manufacture'] = int(data['year_of_manufacture'])
            except (ValueError, TypeError):
                pass  # Serializer o'zi validate qiladi
        
        # Partial update - faqat yuborilgan fieldlarni update qilamiz
        serializer = VehicleDetailsSerializer(
            vehicle,
            data=data,
            partial=True,  # Partial update - required fieldlar talab qilinmaydi
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Update vehicle fields (agar yuborilgan bo'lsa)
            if data:
                validated_data = await sync_to_async(lambda: serializer.validated_data)()
                
                # supported_ride_types ni alohida handle qilish (ManyToMany)
                supported_ride_types = validated_data.pop('supported_ride_types', None)
                
                # Boshqa fieldlarni update qilish
                for attr, value in validated_data.items():
                    setattr(vehicle, attr, value)
                await sync_to_async(vehicle.save)()
                
                # supported_ride_types ni update qilish (agar yuborilgan bo'lsa)
                if supported_ride_types is not None:
                    await sync_to_async(vehicle.supported_ride_types.set)(supported_ride_types)
            
            # Add new images (agar yuborilgan bo'lsa)
            if images_data:
                for image in images_data:
                    if image:
                        await sync_to_async(VehicleImages.objects.create)(
                            vehicle=vehicle,
                            image=image
                        )
            
            # Serialize qilish
            serializer = VehicleDetailsSerializer(vehicle, context={'request': request})
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Vehicle details updated successfully',
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

    @extend_schema(tags=['Vehicle Details'], summary='Delete vehicle', description='Delete vehicle details and all images by ID. Role: Driver.')
    async def delete(self, request, pk):
        """
        Delete vehicle details by ID - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        vehicle = await self.get_object(pk, request.user)
        
        if not vehicle:
            return Response(
                {
                    'message': 'Vehicle details not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        await sync_to_async(vehicle.delete)()
        return Response(
            {
                'message': 'Vehicle details deleted successfully',
                'status': 'success'
            },
            status=status.HTTP_200_OK
        )


class VehicleImageView(AsyncAPIView):
    """
    Vehicle Image endpoint - GET, PUT, DELETE
    
    This endpoint allows authenticated drivers to manage individual vehicle images:
    - GET: Get vehicle image details by ID
    - PUT: Update vehicle image
    - DELETE: Delete vehicle image
    
    **Only accessible to users with Driver role**
    **Drivers can only access images of their own vehicles**
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    async def check_driver_permission(self, request):
        """
        Check if user is a Driver
        """
        user = request.user
        # Check if user is in Driver group (async)
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

    async def get_object(self, pk, user):
        """
        Get vehicle image object by ID with permission check
        """
        try:
            vehicle_image = await VehicleImages.objects.select_related('vehicle__user').aget(pk=pk)
            # Drivers can only access images of their own vehicles
            if vehicle_image.vehicle.user != user:
                return None
            return vehicle_image
        except VehicleImages.DoesNotExist:
            return None

    @extend_schema(tags=['Vehicle Images'], summary='Get vehicle image', description='Get vehicle image details by ID. Role: Driver.')
    async def get(self, request, pk):
        """
        Get vehicle image details by ID - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        vehicle_image = await self.get_object(pk, request.user)
        
        if not vehicle_image:
            return Response(
                {
                    'message': 'Vehicle image not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VehicleImageSerializer(vehicle_image, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        
        return Response(
            {
                'message': 'Vehicle image details retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(tags=['Vehicle Images'], summary='Update vehicle image', description='Update vehicle image by ID. multipart/form-data, field: image (required). Role: Driver.')
    async def put(self, request, pk):
        """
        Update vehicle image by ID - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        vehicle_image = await self.get_object(pk, request.user)
        
        if not vehicle_image:
            return Response(
                {
                    'message': 'Vehicle image not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare data for serializer
        data = {}
        if 'image' in request.FILES:
            data['image'] = request.FILES['image']
        elif 'image' in request.data:
            data['image'] = request.data['image']
        else:
            return Response(
                {
                    'message': 'Image file is required',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update using serializer
        serializer = VehicleImageSerializer(
            vehicle_image,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            await sync_to_async(serializer.save)()
            serializer_data = await sync_to_async(lambda: serializer.data)()
            
            return Response(
                {
                    'message': 'Vehicle image updated successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_200_OK
            )
        else:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {
                    'message': 'Validation error',
                    'status': 'error',
                    'errors': errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(tags=['Vehicle Images'], summary='Delete vehicle image', description='Delete vehicle image by ID. Role: Driver.')
    async def delete(self, request, pk):
        """
        Delete vehicle image by ID - ASYNC VERSION
        """
        # Check driver permission
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error
        
        vehicle_image = await self.get_object(pk, request.user)
        
        if not vehicle_image:
            return Response(
                {
                    'message': 'Vehicle image not found or you do not have permission',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        await sync_to_async(vehicle_image.delete)()
        return Response(
            {
                'message': 'Vehicle image deleted successfully',
                'status': 'success'
            },
            status=status.HTTP_200_OK
        )
