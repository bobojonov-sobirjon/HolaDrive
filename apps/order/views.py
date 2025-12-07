from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from asgiref.sync import sync_to_async

from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    PriceEstimateSerializer,
    OrderItemUpdateSerializer,
    OrderItemSerializer,
    OrderItemManagePriceSerializer,
    OrderPreferencesSerializer,
    AdditionalPassengerSerializer,
    OrderScheduleSerializer
)
from .serializers.cancel_order import OrderCancelSerializer
from .models import Order, OrderItem


class OrderCreateView(AsyncAPIView):
    """
    Create Order and OrderItem
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Order'],
        operation_description="Create a new order with order item",
        request_body=OrderCreateSerializer,
        responses={
            201: openapi.Response(
                description="Order created successfully",
                schema=OrderSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
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


class OrderPreferencesCreateView(AsyncAPIView):
    """
    Create or Update Order Preferences
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Order Preferences'],
        operation_description="Create or update order preferences. Available enum values:\n"
                              "- chatting_preference: no_communication, casual, friendly\n"
                              "- temperature_preference: warm, comfortable, cool, cold\n"
                              "- music_preference: pop, rock, jazz, classical, hip_hop, electronic, country, no_music\n"
                              "- volume_level: low, medium, high, mute\n"
                              "- pet_preference: yes, no\n"
                              "- kids_chair_preference: yes, no\n"
                              "- wheelchair_preference: yes, no\n"
                              "- gender_preference: male, female, other\n"
                              "- favorite_driver_preference: yes, no",
        request_body=OrderPreferencesSerializer,
        responses={
            201: openapi.Response(
                description="Order preferences created/updated successfully",
                schema=OrderPreferencesSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
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
    
    @swagger_auto_schema(
        tags=['Order Additional Passenger'],
        operation_description="Add additional passenger to order",
        request_body=AdditionalPassengerSerializer,
        responses={
            201: openapi.Response(
                description="Additional passenger added successfully",
                schema=AdditionalPassengerSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
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
    
    @swagger_auto_schema(
        tags=['Order Schedule'],
        operation_description="Create order schedule. Available enum values:\n"
                              "- schedule_type: pickup_at (Pickup At), drop_off_by (Drop Off By)\n"
                              "- schedule_time_type: today (Today), tomorrow (Tomorrow), select_date (Select Date)",
        request_body=OrderScheduleSerializer,
        responses={
            201: openapi.Response(
                description="Order schedule created successfully",
                schema=OrderScheduleSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
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


class PriceEstimateView(AsyncAPIView):
    """
    Get price estimates for all ride types
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Order'],
        operation_description="Get price estimates for all active ride types based on coordinates",
        request_body=PriceEstimateSerializer,
        responses={
            200: openapi.Response(description="Price estimates retrieved successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
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
    
    @swagger_auto_schema(
        tags=['Order'],
        operation_description="Update order item with ride type and calculate price",
        request_body=OrderItemUpdateSerializer,
        responses={
            200: openapi.Response(description="Order item updated successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Order item not found"),
        }
    )
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
    
    @swagger_auto_schema(
        tags=['Order'],
        operation_description="Adjust order item price (must be within min_price and max_price range)",
        request_body=OrderItemManagePriceSerializer,
        responses={
            200: openapi.Response(description="Price adjusted successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Order item not found"),
        }
    )
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
    
    @swagger_auto_schema(
        tags=['Order'],
        operation_description="Cancel an order. Available cancel reasons:\n"
                              "- change_in_plans: Change in Plans\n"
                              "- waiting_for_long_time: Waiting for Long Time\n"
                              "- driver_denied_to_go_to_destination: Driver Denied to Go to Destination\n"
                              "- driver_denied_to_come_to_pickup: Driver Denied to Come to Pickup\n"
                              "- wrong_address_shown: Wrong Address Shown\n"
                              "- the_price_is_not_reasonable: The Price is Not Reasonable\n"
                              "- emergency_situation: Emergency Situation\n"
                              "- other: Other (requires other_reason field)",
        request_body=OrderCancelSerializer,
        responses={
            200: openapi.Response(description="Order cancelled successfully"),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Order not found"),
        }
    )
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
    
    @swagger_auto_schema(
        tags=['Order'],
        operation_description="Get current user's orders. Can filter by status and order_type using query parameters.",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by order status",
                type=openapi.TYPE_STRING,
                enum=['pending', 'confirmed', 'cancelled', 'completed', 'refunded', 'failed'],
                required=False
            ),
            openapi.Parameter(
                'order_type',
                openapi.IN_QUERY,
                description="Filter by order type",
                type=openapi.TYPE_STRING,
                enum=['pickup', 'for_me'],
                required=False
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number for pagination",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Number of items per page",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(description="Orders retrieved successfully"),
        }
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
