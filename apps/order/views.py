from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    PriceEstimateSerializer,
    OrderItemUpdateSerializer,
    OrderItemSerializer,
    OrderItemManagePriceSerializer,
    OrderPreferencesSerializer,
    AdditionalPassengerSerializer,
    OrderScheduleSerializer,
    DriverNearbyOrderSerializer,
    DriverOrderActionSerializer,
    DriverLocationUpdateSerializer,
    DriverLocationSerializer,
    DriverInfoSerializer,
    DriverEarningsSerializer,
    DriverRideHistorySerializer,
    DriverOnlineStatusSerializer,
    TripRatingCreateSerializer,
    TripRatingSerializer,
    RatingFeedbackTagSerializer,
)
from .serializers.cancel_order import OrderCancelSerializer
from .models import Order, OrderItem, OrderDriver, OrderPreferences, TripRating
from apps.accounts.models import CustomUser, DriverPreferences
from .services.surge_pricing_service import calculate_distance
from .services.driver_assignment_service import DriverAssignmentService

class OrderCreateView(AsyncAPIView):
    """
    Create Order and OrderItem
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Create order', description='Create order and order items.', request=OrderCreateSerializer)
    async def post(self, request):
        """
        Create Order and OrderItem - ASYNC VERSION
        """
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Save order (async)
            order = await sync_to_async(serializer.save)()
            
            # Optimize query: prefetch related data to avoid N+1 queries (async)
            order = await Order.objects.select_related('user').prefetch_related(
                'order_items__ride_type'
            ).aget(pk=order.pk)
            
            # Serialize order (sync operation wrapped)
            order_serializer = OrderSerializer(order)
            serializer_data = await sync_to_async(lambda: order_serializer.data)()
            
            return Response(
                {
                    'message': 'Order created successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_201_CREATED
            )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class OrderPreferencesGetView(AsyncAPIView):
    """
    Get Order Preferences by Order ID
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Order'],
        summary='Get order preferences',
        description='Get order preferences by order_id (query param).',
        parameters=[OpenApiParameter('order_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description='Order ID')],
    )
    async def get(self, request):
        """
        Get Order Preferences by Order ID - ASYNC VERSION
        """
        order_id = request.query_params.get('order_id')
        
        if not order_id:
            return Response(
                {
                    'message': 'order_id parameter is required',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order_id = int(order_id)
        except (ValueError, TypeError):
            return Response(
                {
                    'message': 'Invalid order_id. Must be an integer.',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if order exists and belongs to user
        try:
            order = await Order.objects.select_related('user').aget(
                id=order_id,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response(
                {
                    'message': 'Order not found or you do not have permission to access it',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get preferences for this order
        preferences = await OrderPreferences.objects.filter(
            order=order
        ).select_related('order').afirst()
        
        if not preferences:
            return Response(
                {
                    'message': 'Order preferences not found for this order',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Serialize preferences (sync operation wrapped)
        serializer = OrderPreferencesSerializer(preferences, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        
        return Response(
            {
                'message': 'Order preferences retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

class OrderPreferencesGetView(AsyncAPIView):
    """
    Get Order Preferences by Order ID
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Order'],
        summary='Get order preferences',
        description='Get order preferences by order_id (query param).',
        parameters=[OpenApiParameter('order_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description='Order ID')],
    )
    async def get(self, request):
        """
        Get Order Preferences by Order ID - ASYNC VERSION
        """
        order_id = request.query_params.get('order_id')
        
        if not order_id:
            return Response(
                {
                    'message': 'order_id parameter is required',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order_id = int(order_id)
        except (ValueError, TypeError):
            return Response(
                {
                    'message': 'Invalid order_id. Must be an integer.',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if order exists and belongs to user
        try:
            order = await Order.objects.select_related('user').aget(
                id=order_id,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response(
                {
                    'message': 'Order not found or you do not have permission to access it',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get preferences for this order
        preferences = await OrderPreferences.objects.filter(
            order=order
        ).select_related('order').afirst()
        
        if not preferences:
            return Response(
                {
                    'message': 'Order preferences not found for this order',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Serialize preferences (sync operation wrapped)
        serializer = OrderPreferencesSerializer(preferences, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        
        return Response(
            {
                'message': 'Order preferences retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

class OrderPreferencesCreateView(AsyncAPIView):
    """
    Create or Update Order Preferences
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Create order preferences', description='Create or update order preferences.', request=OrderPreferencesSerializer)
    async def post(self, request):
        """
        Create or Update Order Preferences - ASYNC VERSION
        """
        serializer = OrderPreferencesSerializer(data=request.data, context={'request': request})
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Save preferences (async)
            preferences = await sync_to_async(serializer.save)()
            
            # Serialize preferences (sync operation wrapped)
            pref_serializer = OrderPreferencesSerializer(preferences)
            serializer_data = await sync_to_async(lambda: pref_serializer.data)()
            
            return Response(
                {
                    'message': 'Order preferences saved successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_201_CREATED
            )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class AdditionalPassengerCreateView(AsyncAPIView):
    """
    Create Additional Passenger
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Add passenger', description='Create additional passenger for an order.', request=AdditionalPassengerSerializer)
    async def post(self, request):
        """
        Create Additional Passenger - ASYNC VERSION
        """
        serializer = AdditionalPassengerSerializer(data=request.data, context={'request': request})
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Save passenger (async)
            passenger = await sync_to_async(serializer.save)()
            
            # Serialize passenger (sync operation wrapped)
            pass_serializer = AdditionalPassengerSerializer(passenger)
            serializer_data = await sync_to_async(lambda: pass_serializer.data)()
            
            return Response(
                {
                    'message': 'Additional passenger added successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_201_CREATED
            )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class OrderScheduleCreateView(AsyncAPIView):
    """
    Create Order Schedule
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Create schedule', description='Create order schedule (pickup/drop-off time).', request=OrderScheduleSerializer)
    async def post(self, request):
        """
        Create Order Schedule - ASYNC VERSION
        """
        serializer = OrderScheduleSerializer(data=request.data, context={'request': request})
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Save schedule (async)
            schedule = await sync_to_async(serializer.save)()
            
            # Serialize schedule (sync operation wrapped)
            sched_serializer = OrderScheduleSerializer(schedule)
            serializer_data = await sync_to_async(lambda: sched_serializer.data)()
            
            return Response(
                {
                    'message': 'Order schedule created successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_201_CREATED
            )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class DriverNearbyOrdersView(AsyncAPIView):
    """
    List nearby pending orders for authenticated driver.
    Uses driver's current location (CustomUser.latitude/longitude)
    and driver preferences (maximum_pickup_distance) to filter orders.
    """
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver'], summary='Nearby orders', description='List nearby pending orders for driver. Role: Driver.')
    async def get(self, request):
        user = request.user

        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get orders assigned to this driver with status=requested (Uber model)
        order_drivers_qs = (
            OrderDriver.objects.filter(
                driver=user,
                status=OrderDriver.DriverRequestStatus.REQUESTED
            )
            .select_related('order', 'order__user')
            .prefetch_related('order__order_items')
        )
        order_drivers = await sync_to_async(list)(order_drivers_qs)

        # Filter only pending orders (not yet accepted by another driver)
        nearby_orders = []
        for order_driver in order_drivers:
            order = order_driver.order
            
            # Only include if order is still pending
            if order.status != Order.OrderStatus.PENDING:
                continue
            
            # Check timeout (5 minutes = 300 seconds)
            from django.utils import timezone
            from apps.order.services.driver_assignment_service import DriverAssignmentService
            
            if order_driver.requested_at:
                time_elapsed = timezone.now() - order_driver.requested_at
                if time_elapsed.total_seconds() >= DriverAssignmentService.TIMEOUT_SECONDS:  # Timeout
                    # Mark as timeout
                    order_driver.status = OrderDriver.DriverRequestStatus.TIMEOUT
                    await sync_to_async(order_driver.save)()
                    
                    # Reassign to next driver (MUHIM: oldingi driver exclude qilinadi)
                    try:
                        next_order_driver = await sync_to_async(DriverAssignmentService.assign_to_next_driver)(order)
                        if next_order_driver:
                            # Keyingi driverga yuborildi, bu driver endi ko'rmaydi
                            pass
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to reassign order {order.id} after timeout: {e}")
                    
                    # Bu driver endi bu orderni ko'rmaydi (timeout bo'lgan)
                    continue
            
            first_item = order.order_items.first()
            if not first_item or not first_item.latitude_from or not first_item.longitude_from:
                continue

            # Calculate distance if driver location is available
            if user.latitude and user.longitude:
                distance = calculate_distance(
                    user.latitude,
                    user.longitude,
                    first_item.latitude_from,
                    first_item.longitude_from,
                )
                order.distance_to_pickup_km = round(float(distance), 2)
            else:
                order.distance_to_pickup_km = None

            nearby_orders.append(order)

        serializer = DriverNearbyOrderSerializer(nearby_orders, many=True)
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Assigned orders retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

class DriverOrderActionView(AsyncAPIView):
    """
    Driver can accept or reject a pending order.
    - accept: creates/updates OrderDriver with status='accepted' and sets Order.status='confirmed'
    - reject: creates/updates OrderDriver with status='rejected' (Order stays pending)
    """

    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver'], summary='Accept/Reject order', description='Driver accept or reject a pending order. Body: order_id, action (accept/reject). Role: Driver.', request=DriverOrderActionSerializer)
    async def post(self, request):
        user = request.user

        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DriverOrderActionSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {
                    'message': 'Validation error',
                    'status': 'error',
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = await sync_to_async(lambda: serializer.validated_data)()
        order_id = data['order_id']
        action = data['action']

        order = await Order.objects.select_related('user').aget(id=order_id)

        # Check if order is assigned to this driver
        order_driver = await OrderDriver.objects.filter(
            order=order,
            driver=user,
            status=OrderDriver.DriverRequestStatus.REQUESTED
        ).afirst()

        if not order_driver:
            return Response(
                {
                    'message': 'This order is not assigned to you or has already been processed',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only allow actions on pending orders
        if order.status != Order.OrderStatus.PENDING and action == 'accept':
            return Response(
                {
                    'message': 'Order is not available for accepting',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone

        # Update status based on action
        if action == 'accept':
            # Accept: assign to this driver
            order_driver.status = OrderDriver.DriverRequestStatus.ACCEPTED
            order.status = Order.OrderStatus.CONFIRMED
            order_driver.responded_at = timezone.now()
            await sync_to_async(order_driver.save)()
            await sync_to_async(order.save)()
            
            # Send push notification to rider
            try:
                from apps.notification.services import send_push_to_user
                send_push_to_user(
                    user=order.user,
                    title="Driver found",
                    body=f"Your ride has been accepted. Driver is on the way.",
                    data={
                        "order_id": order.id,
                        "order_code": order.order_code,
                        "type": "driver_accepted"
                    }
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send push notification to rider {order.user.id}: {e}")
        else:
            # Reject: mark as rejected and reassign to next driver
            order_driver.status = OrderDriver.DriverRequestStatus.REJECTED
            order_driver.responded_at = timezone.now()
            await sync_to_async(order_driver.save)()
            
            # Reassign to next nearest driver
            try:
                next_order_driver = await sync_to_async(DriverAssignmentService.assign_to_next_driver)(order)
                if next_order_driver:
                    message = "Order rejected. Reassigned to next driver."
                else:
                    message = "Order rejected. No more drivers available at the moment."
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to reassign order {order.id} after rejection: {e}")
                message = "Order rejected successfully."

        return Response(
            {
                'message': message if action == 'reject' else f"Order {action}ed successfully",
                'status': 'success',
            },
            status=status.HTTP_200_OK,
        )

class DriverLocationUpdateView(AsyncAPIView):
    """
    Update driver's current GPS location.
    Stores latitude/longitude on CustomUser model.
    """
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver'], summary='Update location', description="Update driver's GPS location. Body: latitude, longitude. Role: Driver.", request=DriverLocationUpdateSerializer)
    async def post(self, request):
        user = request.user

        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DriverLocationUpdateSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {
                    'message': 'Validation error',
                    'status': 'error',
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = await sync_to_async(lambda: serializer.validated_data)()

        user.latitude = data['latitude']
        user.longitude = data['longitude']
        await sync_to_async(user.save)(update_fields=['latitude', 'longitude'])

        response_data = {
            'driver_id': user.id,
            'latitude': user.latitude,
            'longitude': user.longitude,
            'updated_at': user.updated_at,
        }
        out_serializer = DriverLocationSerializer(response_data)
        serialized = await sync_to_async(lambda: out_serializer.data)()

        return Response(
            {
                'message': 'Location updated successfully',
                'status': 'success',
                'data': serialized,
            },
            status=status.HTTP_200_OK,
        )

class DriverLocationForOrderView(AsyncAPIView):
    """
    Rider can get driver's current location for a specific order.
    Only works if order is assigned to a driver (OrderDriver with status=accepted).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Driver location for order', description="Rider: get driver's current location for an order (when driver is assigned).")
    async def get(self, request, order_id: int):
        user = request.user

        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {
                    'message': 'Order not found',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.user != user:
            return Response(
                {
                    'message': 'You do not have permission to view this order',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get accepted driver
        order_driver = await OrderDriver.objects.filter(
            order=order,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        ).select_related('driver').afirst()

        if not order_driver or not order_driver.driver:
            return Response(
                {
                    'message': 'No driver assigned yet',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        driver = order_driver.driver
        if driver.latitude is None or driver.longitude is None:
            return Response(
                {
                    'message': 'Driver location is not available',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get driver's vehicle details (first vehicle)
        from apps.accounts.models import VehicleDetails
        vehicle = await sync_to_async(
            lambda: VehicleDetails.objects.filter(user=driver).select_related('default_ride_type').first()
        )()

        # Get completed trips count
        completed_trips_count = await sync_to_async(
            lambda: Order.objects.filter(
                order_drivers__driver=driver,
                order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
                status=Order.OrderStatus.COMPLETED
            ).count()
        )()

        # Calculate average rating
        ratings = await sync_to_async(list)(
            TripRating.objects.filter(driver=driver, status='approved').values_list('rating', flat=True)
        )
        average_rating = 0.0
        if ratings:
            average_rating = round(sum(ratings) / len(ratings), 2)

        # Build driver info data
        # Get avatar URL
        avatar_url = None
        if driver.avatar:
            request_obj = request
            avatar_url = request_obj.build_absolute_uri(driver.avatar.url) if hasattr(request_obj, 'build_absolute_uri') else driver.avatar.url

        driver_info_data = {
            'name': driver.get_full_name(),
            'avatar': avatar_url,
            'rating': average_rating,
            'trips_count': completed_trips_count,
            'member_since': driver.created_at.date() if driver.created_at else None,
            'car_model': f"{vehicle.brand} {vehicle.model}" if vehicle else None,
            'color': vehicle.color if vehicle else None,
            'plate_number': vehicle.plate_number if vehicle else None,
            'location': {
                'latitude': str(driver.latitude),
                'longitude': str(driver.longitude),
                'updated_at': driver.updated_at.isoformat() if driver.updated_at else None,
            }
        }

        serializer = DriverInfoSerializer(driver_info_data)
        serialized = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Driver information retrieved successfully',
                'status': 'success',
                'data': serialized,
            },
            status=status.HTTP_200_OK,
        )

class PriceEstimateView(AsyncAPIView):
    """
    Get price estimates for all ride types
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Price estimate', description='Get price estimates for all active ride types (from/to coordinates).', request=PriceEstimateSerializer)
    async def post(self, request):
        """
        Calculate price estimates for all active ride types - ASYNC VERSION
        """
        from apps.order.models import RideType
        from apps.order.services.surge_pricing_service import SurgePricingService, calculate_distance
        from decimal import Decimal
        
        serializer = PriceEstimateSerializer(data=request.data)
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Get validated data (sync operation)
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            
            lat_from = float(validated_data['latitude_from'])
            lon_from = float(validated_data['longitude_from'])
            lat_to = float(validated_data['latitude_to'])
            lon_to = float(validated_data['longitude_to'])
            
            # Calculate distance (sync function, but can run in thread)
            distance_km = await sync_to_async(calculate_distance)(lat_from, lon_from, lat_to, lon_to)
            
            # Get surge multiplier (sync function)
            surge_multiplier = await sync_to_async(SurgePricingService.get_multiplier)(lat_from, lon_from)
            
            # Get all active ride types (async query)
            ride_types = await sync_to_async(list)(RideType.objects.filter(is_active=True))
            
            # Process estimates (sync operations in async context)
            estimates = []
            for ride_type in ride_types:
                if ride_type.base_price and ride_type.price_per_km:
                    price = await sync_to_async(ride_type.calculate_price)(distance_km, surge_multiplier)
                    estimates.append({
                        'ride_type_id': ride_type.id,
                        'ride_type_name': ride_type.name or ride_type.name_large,
                        'ride_type_name_large': ride_type.name_large,
                        'ride_type_icon': ride_type.icon,
                        'base_price': float(ride_type.base_price) if ride_type.base_price else None,
                        'price_per_km': float(ride_type.price_per_km) if ride_type.price_per_km else None,
                        'distance_km': round(distance_km, 2),
                        'surge_multiplier': surge_multiplier,
                        'estimated_price': round(price, 2),
                        'capacity': ride_type.capacity,
                        'is_premium': ride_type.is_premium,
                        'is_ev': ride_type.is_ev,
                    })
            
            return Response(
                {
                    'message': 'Price estimates retrieved successfully',
                    'status': 'success',
                    'data': {
                        'distance_km': round(distance_km, 2),
                        'surge_multiplier': surge_multiplier,
                        'estimates': estimates
                    }
                },
                status=status.HTTP_200_OK
            )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class OrderItemUpdateView(AsyncAPIView):
    """
    Update OrderItem with ride_type
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Update order item', description='Update order item (e.g. ride_type).', request=OrderItemUpdateSerializer)
    async def patch(self, request, order_item_id):
        """
        Update OrderItem with ride_type - ASYNC VERSION
        """
        try:
            # Optimize query: use select_related to avoid N+1 queries (async)
            order_item = await OrderItem.objects.select_related(
                'order__user', 'ride_type'
            ).aget(id=order_item_id)
            # Check if order belongs to user
            if order_item.order.user != request.user:
                return Response(
                    {
                        'message': 'Permission denied',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        except OrderItem.DoesNotExist:
            return Response(
                {
                    'message': 'Order item not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderItemUpdateSerializer(
            order_item, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Save updated item (async)
            updated_item = await sync_to_async(serializer.save)()
            # Re-fetch with optimized query to avoid N+1 in serializer (async)
            updated_item = await OrderItem.objects.select_related('ride_type').aget(pk=updated_item.pk)
            
            # Serialize order item (sync operation wrapped)
            order_item_serializer = OrderItemSerializer(updated_item)
            serializer_data = await sync_to_async(lambda: order_item_serializer.data)()
            
            return Response(
                {
                    'message': 'Order item updated successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_200_OK
            )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class OrderItemManagePriceView(AsyncAPIView):
    """
    Manage (adjust) OrderItem price
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Manage order item price', description='Adjust order item price.', request=OrderItemManagePriceSerializer)
    async def patch(self, request, order_item_id):
        """
        Adjust OrderItem price - ASYNC VERSION
        """
        try:
            # Optimize query: use select_related to avoid N+1 queries (async)
            order_item = await OrderItem.objects.select_related(
                'order__user', 'ride_type'
            ).aget(id=order_item_id)
            # Check if order belongs to user
            if order_item.order.user != request.user:
                return Response(
                    {
                        'message': 'Permission denied',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        except OrderItem.DoesNotExist:
            return Response(
                {
                    'message': 'Order item not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderItemManagePriceSerializer(data=request.data)
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Get validated data (sync operation)
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            adjusted_price = validated_data['adjusted_price']
            
            # Check if original_price exists
            if not order_item.original_price:
                return Response(
                    {
                        'message': 'Original price not set. Please set ride_type first.',
                        'status': 'error'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure min_price and max_price are calculated (sync method)
            if not order_item.min_price or not order_item.max_price:
                min_price, max_price = await sync_to_async(order_item.calculate_price_range)()
                order_item.min_price = min_price
                order_item.max_price = max_price
                await sync_to_async(order_item.save)()
            
            # Validate price range
            from decimal import Decimal
            adjusted_price_decimal = Decimal(str(adjusted_price))
            
            if order_item.min_price and adjusted_price_decimal < order_item.min_price:
                return Response(
                    {
                        'message': f'Price cannot be less than {order_item.min_price}',
                        'status': 'error',
                        'data': {
                            'min_price': float(order_item.min_price),
                            'max_price': float(order_item.max_price) if order_item.max_price else None,
                            'original_price': float(order_item.original_price),
                            'requested_price': float(adjusted_price)
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if order_item.max_price and adjusted_price_decimal > order_item.max_price:
                return Response(
                    {
                        'message': f'Price cannot be more than {order_item.max_price}',
                        'status': 'error',
                        'data': {
                            'min_price': float(order_item.min_price),
                            'max_price': float(order_item.max_price) if order_item.max_price else None,
                            'original_price': float(order_item.original_price),
                            'requested_price': float(adjusted_price)
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Adjust price using the model method (sync method)
            try:
                await sync_to_async(order_item.adjust_price)(float(adjusted_price))
                # Re-fetch with optimized query to avoid N+1 in serializer (async)
                order_item = await OrderItem.objects.select_related('ride_type').aget(pk=order_item.pk)
                
                # Serialize order item (sync operation wrapped)
                order_item_serializer = OrderItemSerializer(order_item)
                serializer_data = await sync_to_async(lambda: order_item_serializer.data)()
                
                return Response(
                    {
                        'message': 'Price adjusted successfully',
                        'status': 'success',
                        'data': serializer_data
                    },
                    status=status.HTTP_200_OK
                )
            except ValueError as e:
                return Response(
                    {
                        'message': str(e),
                        'status': 'error'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class OrderCancelView(AsyncAPIView):
    """
    Cancel an order
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Order'], summary='Cancel order', description='Cancel an order. Body: reason, optional other_reason.', request=OrderCancelSerializer)
    async def post(self, request, order_id):
        """
        Cancel an order - ASYNC VERSION
        """
        try:
            # Optimize query: use select_related to avoid N+1 queries (async)
            order = await Order.objects.select_related('user').aget(id=order_id)
            # Check if order belongs to user
            if order.user != request.user:
                return Response(
                    {
                        'message': 'Permission denied',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        except Order.DoesNotExist:
            return Response(
                {
                    'message': 'Order not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if order can be cancelled
        if order.status == Order.OrderStatus.CANCELLED:
            return Response(
                {
                    'message': 'Order is already cancelled',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.status == Order.OrderStatus.COMPLETED:
            return Response(
                {
                    'message': 'Cannot cancel a completed order',
                    'status': 'error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = OrderCancelSerializer(data=request.data)
        
        # Validate serializer (sync operation)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            # Get validated data (sync operation)
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            reason = validated_data['reason']
            other_reason = validated_data.get('other_reason', '')
            
            # Update order status to cancelled (async)
            order.status = Order.OrderStatus.CANCELLED
            await sync_to_async(order.save)()
            
            # Create CancelOrder record if driver exists
            from .models import OrderDriver, CancelOrder
            order_driver = await sync_to_async(
                lambda: OrderDriver.objects.select_related('driver').filter(order=order).first()
            )()
            
            if order_driver:
                await sync_to_async(CancelOrder.objects.create)(
                    order=order,
                    driver=order_driver,
                    reason=reason,
                    other_reason=other_reason if reason == CancelOrder.CancelReason.OTHER else None
                )
            
            # Re-fetch order with optimized query to avoid N+1 in serializer (async)
            order = await Order.objects.select_related('user').prefetch_related(
                'order_items__ride_type',
                'order_drivers__driver'
            ).aget(pk=order.pk)
            
            # Serialize order (sync operation wrapped)
            order_serializer = OrderSerializer(order)
            serializer_data = await sync_to_async(lambda: order_serializer.data)()
            
            return Response(
                {
                    'message': 'Order cancelled successfully',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_200_OK
            )
        
        # Get errors (sync operation)
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

class MyOrderListView(AsyncAPIView):
    """
    Get current user's orders
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Order'],
        summary='My orders',
        description="Get current user's orders. Optional query: status, order_type, page, page_size.",
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description='Filter by order status'),
            OpenApiParameter('order_type', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description='Filter by order type'),
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Page number'),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Page size'),
        ],
    )
    async def get(self, request):
        """
        Get current user's orders with optional filtering - ASYNC VERSION
        Optimized with select_related and prefetch_related to avoid N+1 queries
        """
        from rest_framework.pagination import PageNumberPagination
        
        # Get user's orders with optimized queries to avoid N+1 problem (async)
        orders_queryset = Order.objects.filter(user=request.user).select_related(
            'user'  # Optimize user foreign key access
        ).prefetch_related(
            'order_items__ride_type',  # Optimize order_items and ride_type access
            'order_preferences',  # Optimize order preferences access
            'order_drivers__driver',  # Optimize order drivers and driver access
            'additional_passengers',  # Optimize additional passengers access
        ).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status', None)
        if status_filter:
            status_choices = await sync_to_async(lambda: [choice[0] for choice in Order.OrderStatus.choices])()
            if status_filter in status_choices:
                orders_queryset = orders_queryset.filter(status=status_filter)
            else:
                return Response(
                    {
                        'message': 'Invalid status value',
                        'status': 'error',
                        'errors': {
                            'status': f'Must be one of: {", ".join(status_choices)}'
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Filter by order_type if provided
        order_type_filter = request.query_params.get('order_type', None)
        if order_type_filter:
            order_type_choices = await sync_to_async(lambda: [choice[0] for choice in Order.OrderType.choices])()
            if order_type_filter in order_type_choices:
                orders_queryset = orders_queryset.filter(order_type=order_type_filter)
            else:
                return Response(
                    {
                        'message': 'Invalid order_type value',
                        'status': 'error',
                        'errors': {
                            'order_type': f'Must be one of: {", ".join(order_type_choices)}'
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Convert queryset to list (async)
        orders = await sync_to_async(list)(orders_queryset)
        
        # Pagination (sync operation wrapped)
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        paginated_orders = await sync_to_async(paginator.paginate_queryset)(orders, request)
        
        if paginated_orders is not None:
            # Serialize orders (sync operation wrapped)
            serializer = OrderSerializer(paginated_orders, many=True)
            serializer_data = await sync_to_async(lambda: serializer.data)()
            
            # Get paginated response (sync operation)
            response = await sync_to_async(paginator.get_paginated_response)(serializer_data)
            # Add custom message and status to paginated response
            response.data['message'] = 'Orders retrieved successfully'
            response.data['status'] = 'success'
            response.data['data'] = response.data.pop('results')
            return response
        
        # If no pagination
        serializer = OrderSerializer(orders, many=True)
        serializer_data = await sync_to_async(lambda: serializer.data)()
        orders_count = await sync_to_async(len)(orders)
        
        return Response(
            {
                'message': 'Orders retrieved successfully',
                'status': 'success',
                'count': orders_count,
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

class DriverEarningsView(AsyncAPIView):
    """
    Get driver earnings summary (today, weekly, monthly, total).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Driver'], summary='Earnings', description='Get driver earnings summary (today, weekly, monthly, total). Role: Driver.')
    async def get(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {'message': 'Only drivers can access this endpoint', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
        from django.utils import timezone
        from datetime import timedelta
        from decimal import Decimal
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        completed_orders = Order.objects.filter(
            order_drivers__driver=user,
            order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
            status=Order.OrderStatus.COMPLETED
        ).prefetch_related('order_items')
        today_orders = await sync_to_async(list)(completed_orders.filter(updated_at__gte=today_start))
        today_earnings = Decimal('0.00')
        today_distance_km = Decimal('0.00')
        for order in today_orders:
            for item in order.order_items.all():
                if item.calculated_price:
                    today_earnings += Decimal(str(item.calculated_price))
                if item.distance_km:
                    today_distance_km += Decimal(str(item.distance_km))
        today_rides_count = len(today_orders)
        week_orders = await sync_to_async(list)(completed_orders.filter(updated_at__gte=week_start))
        weekly_earnings = Decimal('0.00')
        weekly_distance_km = Decimal('0.00')
        for order in week_orders:
            for item in order.order_items.all():
                if item.calculated_price:
                    weekly_earnings += Decimal(str(item.calculated_price))
                if item.distance_km:
                    weekly_distance_km += Decimal(str(item.distance_km))
        weekly_rides_count = len(week_orders)
        month_orders = await sync_to_async(list)(completed_orders.filter(updated_at__gte=month_start))
        monthly_earnings = Decimal('0.00')
        monthly_distance_km = Decimal('0.00')
        for order in month_orders:
            for item in order.order_items.all():
                if item.calculated_price:
                    monthly_earnings += Decimal(str(item.calculated_price))
                if item.distance_km:
                    monthly_distance_km += Decimal(str(item.distance_km))
        monthly_rides_count = len(month_orders)
        all_orders = await sync_to_async(list)(completed_orders)
        total_earnings = Decimal('0.00')
        total_distance_km = Decimal('0.00')
        for order in all_orders:
            for item in order.order_items.all():
                if item.calculated_price:
                    total_earnings += Decimal(str(item.calculated_price))
                if item.distance_km:
                    total_distance_km += Decimal(str(item.distance_km))
        total_rides_count = len(all_orders)
        today_target = 6
        earnings_data = {
            'today_earnings': float(today_earnings),
            'today_rides_count': today_rides_count,
            'today_distance_km': float(today_distance_km),
            'today_target': today_target,
            'weekly_earnings': float(weekly_earnings),
            'weekly_rides_count': weekly_rides_count,
            'weekly_distance_km': float(weekly_distance_km),
            'monthly_earnings': float(monthly_earnings),
            'monthly_rides_count': monthly_rides_count,
            'monthly_distance_km': float(monthly_distance_km),
            'total_earnings': float(total_earnings),
            'total_rides_count': total_rides_count,
            'total_distance_km': float(total_distance_km),
        }
        serializer = DriverEarningsSerializer(earnings_data)
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {'message': 'Earnings retrieved successfully', 'status': 'success', 'data': data},
            status=status.HTTP_200_OK,
        )

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

class DriverRideHistoryView(AsyncAPIView):
    """
    Get driver ride history (completed orders).
    """
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(
        tags=['Driver'],
        summary='Ride history',
        description='Get driver ride history (completed orders). Pagination: page_size. Role: Driver.',
        parameters=[OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Page size')],
    )
    async def get(self, request):
        user = request.user

        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        from rest_framework.pagination import PageNumberPagination

        # Get completed orders for this driver
        completed_orders = Order.objects.filter(
            order_drivers__driver=user,
            order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
            status=Order.OrderStatus.COMPLETED
        ).select_related('user').prefetch_related('order_items').order_by('-updated_at')

        # Convert to list (async)
        orders = await sync_to_async(list)(completed_orders)

        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        paginated_orders = await sync_to_async(paginator.paginate_queryset)(orders, request)

        if paginated_orders is not None:
            serializer = DriverRideHistorySerializer(paginated_orders, many=True)
            serializer_data = await sync_to_async(lambda: serializer.data)()
            
            response = await sync_to_async(paginator.get_paginated_response)(serializer_data)
            response.data['message'] = 'Ride history retrieved successfully'
            response.data['status'] = 'success'
            response.data['data'] = response.data.pop('results')
            return response

        # If no pagination
        serializer = DriverRideHistorySerializer(orders, many=True)
        serializer_data = await sync_to_async(lambda: serializer.data)()
        count = await sync_to_async(len)(orders)

        return Response(
            {
                'message': 'Ride history retrieved successfully',
                'status': 'success',
                'count': count,
                'data': serializer_data,
            },
            status=status.HTTP_200_OK,
        )

class DriverOnlineStatusView(AsyncAPIView):
    """
    Get or update driver online/offline status.
    """
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver'], summary='Online status (GET)', description='Get driver online/offline status. Role: Driver.')
    async def get(self, request):
        user = request.user

        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Refresh user from database to get latest is_online status
        user = await CustomUser.objects.aget(id=user.id)

        serializer = DriverOnlineStatusSerializer({'is_online': user.is_online})
        data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Status retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(tags=['Driver'], summary='Update online status', description='Set driver online/offline. Body: is_online. Role: Driver.', request=DriverOnlineStatusSerializer)
    async def post(self, request):
        user = request.user

        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DriverOnlineStatusSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {
                    'message': 'Validation error',
                    'status': 'error',
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = await sync_to_async(lambda: serializer.validated_data)()
        is_online = data['is_online']

        # Update user's online status
        user.is_online = is_online
        await sync_to_async(user.save)(update_fields=['is_online'])

        response_serializer = DriverOnlineStatusSerializer({'is_online': user.is_online})
        response_data = await sync_to_async(lambda: response_serializer.data)()

        return Response(
            {
                'message': 'Status updated successfully',
                'status': 'success',
                'data': response_data,
            },
            status=status.HTTP_200_OK,
        )

class TripRatingCreateView(AsyncAPIView):
    """
    Create a rating for a completed trip.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rating'], summary='Create rating', description='Create a rating for a completed trip.', request=TripRatingCreateSerializer)
    async def post(self, request):
        user = request.user

        serializer = TripRatingCreateSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {
                    'message': 'Validation error',
                    'status': 'error',
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = await sync_to_async(lambda: serializer.validated_data)()
        order_id = validated_data['order_id']
        rating = validated_data['rating']
        comment = validated_data.get('comment')
        tip_amount = validated_data.get('tip_amount', 0)
        feedback_tag_ids = validated_data.get('feedback_tag_ids', [])

        # Get order and verify ownership
        try:
            order = await Order.objects.select_related('user').prefetch_related(
                'order_drivers__driver'
            ).aget(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {
                    'message': 'Order not found',
                    'status': 'error',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.user != user:
            return Response(
                {
                    'message': 'You can only rate your own orders',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get driver from order
        order_driver = await sync_to_async(
            lambda: order.order_drivers.filter(status=OrderDriver.DriverRequestStatus.ACCEPTED).first()
        )()
        
        if not order_driver or not order_driver.driver:
            return Response(
                {
                    'message': 'No driver found for this order',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver = order_driver.driver

        # Create rating
        trip_rating = await sync_to_async(TripRating.objects.create)(
            order=order,
            rider=user,
            driver=driver,
            rating=rating,
            comment=comment,
            tip_amount=tip_amount or 0,
        )

        # Add feedback tags if provided
        if feedback_tag_ids:
            from apps.order.models import RatingFeedbackTag
            tags = await sync_to_async(list)(
                RatingFeedbackTag.objects.filter(id__in=feedback_tag_ids, is_active=True)
            )
            await sync_to_async(trip_rating.feedback_tags.set)(tags)

        # Re-fetch with tags
        trip_rating = await TripRating.objects.select_related(
            'order', 'rider', 'driver'
        ).prefetch_related('feedback_tags').aget(pk=trip_rating.pk)

        response_serializer = TripRatingSerializer(trip_rating, context={'request': request})
        response_data = await sync_to_async(lambda: response_serializer.data)()

        return Response(
            {
                'message': 'Rating created successfully. Driver has been notified.',
                'status': 'success',
                'data': response_data,
            },
            status=status.HTTP_201_CREATED,
        )

class RatingFeedbackTagsListView(AsyncAPIView):
    """
    Get available feedback tags based on rating value.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rating'],
        summary='Feedback tags',
        description='Get available feedback tags by rating (query: rating).',
        parameters=[OpenApiParameter('rating', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description='Rating value 1-5')],
    )
    async def get(self, request):
        rating = request.query_params.get('rating')
        
        if not rating:
            return Response(
                {
                    'message': 'Rating parameter is required',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rating = int(rating)
        except (ValueError, TypeError):
            return Response(
                {
                    'message': 'Rating must be a number between 1 and 5',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if rating < 1 or rating > 5:
            return Response(
                {
                    'message': 'Rating must be between 1 and 5',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine tag type based on rating
        tag_type = 'positive' if rating >= 4 else 'negative'

        # Get tags
        from apps.order.models import RatingFeedbackTag
        tags = await sync_to_async(list)(
            RatingFeedbackTag.objects.filter(tag_type=tag_type, is_active=True).order_by('name')
        )

        tag_serializer = RatingFeedbackTagSerializer(tags, many=True)
        tag_data = await sync_to_async(lambda: tag_serializer.data)()

        return Response(
            {
                'message': 'Feedback tags retrieved successfully',
                'status': 'success',
                'data': {
                    'tags': tag_data,
                    'tag_type': tag_type,
                    'rating': rating,
                },
            },
            status=status.HTTP_200_OK,
        )
