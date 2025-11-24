from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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


class OrderCreateView(APIView):
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
    def post(self, request):
        """
        Create Order and OrderItem
        """
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            order = serializer.save()
            order_serializer = OrderSerializer(order)
            
            return Response(
                {
                    'message': 'Order created successfully',
                    'status': 'success',
                    'data': order_serializer.data
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


class OrderPreferencesCreateView(APIView):
    """
    Create or Update Order Preferences
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Order Preferences'],
        operation_description="Create or update order preferences",
        request_body=OrderPreferencesSerializer,
        responses={
            201: openapi.Response(
                description="Order preferences created/updated successfully",
                schema=OrderPreferencesSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    def post(self, request):
        """
        Create or Update Order Preferences
        """
        serializer = OrderPreferencesSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            preferences = serializer.save()
            
            return Response(
                {
                    'message': 'Order preferences saved successfully',
                    'status': 'success',
                    'data': OrderPreferencesSerializer(preferences).data
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


class AdditionalPassengerCreateView(APIView):
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
    def post(self, request):
        """
        Create Additional Passenger
        """
        serializer = AdditionalPassengerSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            passenger = serializer.save()
            
            return Response(
                {
                    'message': 'Additional passenger added successfully',
                    'status': 'success',
                    'data': AdditionalPassengerSerializer(passenger).data
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


class OrderScheduleCreateView(APIView):
    """
    Create Order Schedule
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Order Schedule'],
        operation_description="Create order schedule",
        request_body=OrderScheduleSerializer,
        responses={
            201: openapi.Response(
                description="Order schedule created successfully",
                schema=OrderScheduleSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
        }
    )
    def post(self, request):
        """
        Create Order Schedule
        """
        serializer = OrderScheduleSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            schedule = serializer.save()
            
            return Response(
                {
                    'message': 'Order schedule created successfully',
                    'status': 'success',
                    'data': OrderScheduleSerializer(schedule).data
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


class PriceEstimateView(APIView):
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
    def post(self, request):
        """
        Calculate price estimates for all active ride types
        """
        from apps.order.models import RideType
        from apps.order.services.surge_pricing_service import SurgePricingService, calculate_distance
        from decimal import Decimal
        
        serializer = PriceEstimateSerializer(data=request.data)
        
        if serializer.is_valid():
            lat_from = float(serializer.validated_data['latitude_from'])
            lon_from = float(serializer.validated_data['longitude_from'])
            lat_to = float(serializer.validated_data['latitude_to'])
            lon_to = float(serializer.validated_data['longitude_to'])
            
            # Calculate distance
            distance_km = calculate_distance(lat_from, lon_from, lat_to, lon_to)
            
            # Get surge multiplier
            surge_multiplier = SurgePricingService.get_multiplier(lat_from, lon_from)
            
            # Get all active ride types
            ride_types = RideType.objects.filter(is_active=True)
            
            estimates = []
            for ride_type in ride_types:
                if ride_type.base_price and ride_type.price_per_km:
                    price = ride_type.calculate_price(distance_km, surge_multiplier)
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
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class OrderItemUpdateView(APIView):
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
    def patch(self, request, order_item_id):
        """
        Update OrderItem with ride_type
        """
        try:
            order_item = OrderItem.objects.get(id=order_item_id)
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
        
        if serializer.is_valid():
            updated_item = serializer.save()
            order_item_serializer = OrderItemSerializer(updated_item)
            
            return Response(
                {
                    'message': 'Order item updated successfully',
                    'status': 'success',
                    'data': order_item_serializer.data
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


class OrderItemManagePriceView(APIView):
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
    def patch(self, request, order_item_id):
        """
        Adjust OrderItem price
        """
        try:
            order_item = OrderItem.objects.get(id=order_item_id)
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
        
        if serializer.is_valid():
            adjusted_price = serializer.validated_data['adjusted_price']
            
            # Check if original_price exists
            if not order_item.original_price:
                return Response(
                    {
                        'message': 'Original price not set. Please set ride_type first.',
                        'status': 'error'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure min_price and max_price are calculated
            if not order_item.min_price or not order_item.max_price:
                order_item.min_price, order_item.max_price = order_item.calculate_price_range()
                order_item.save()
            
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
            
            # Adjust price using the model method
            try:
                order_item.adjust_price(float(adjusted_price))
                order_item_serializer = OrderItemSerializer(order_item)
                
                return Response(
                    {
                        'message': 'Price adjusted successfully',
                        'status': 'success',
                        'data': order_item_serializer.data
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
        
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class OrderCancelView(APIView):
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
    def post(self, request, order_id):
        """
        Cancel an order
        """
        try:
            order = Order.objects.get(id=order_id)
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
        
        if serializer.is_valid():
            reason = serializer.validated_data['reason']
            other_reason = serializer.validated_data.get('other_reason', '')
            
            # Update order status to cancelled
            order.status = Order.OrderStatus.CANCELLED
            order.save()
            
            # Create CancelOrder record if driver exists
            from .models import OrderDriver, CancelOrder
            order_driver = OrderDriver.objects.filter(order=order).first()
            
            if order_driver:
                CancelOrder.objects.create(
                    order=order,
                    driver=order_driver,
                    reason=reason,
                    other_reason=other_reason if reason == CancelOrder.CancelReason.OTHER else None
                )
            
            order_serializer = OrderSerializer(order)
            
            return Response(
                {
                    'message': 'Order cancelled successfully',
                    'status': 'success',
                    'data': order_serializer.data
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


class MyOrderListView(APIView):
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
    def get(self, request):
        """
        Get current user's orders with optional filtering
        """
        from rest_framework.pagination import PageNumberPagination
        
        # Get user's orders
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status', None)
        if status_filter:
            if status_filter in [choice[0] for choice in Order.OrderStatus.choices]:
                orders = orders.filter(status=status_filter)
            else:
                return Response(
                    {
                        'message': 'Invalid status value',
                        'status': 'error',
                        'errors': {
                            'status': f'Must be one of: {", ".join([choice[0] for choice in Order.OrderStatus.choices])}'
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Filter by order_type if provided
        order_type_filter = request.query_params.get('order_type', None)
        if order_type_filter:
            if order_type_filter in [choice[0] for choice in Order.OrderType.choices]:
                orders = orders.filter(order_type=order_type_filter)
            else:
                return Response(
                    {
                        'message': 'Invalid order_type value',
                        'status': 'error',
                        'errors': {
                            'order_type': f'Must be one of: {", ".join([choice[0] for choice in Order.OrderType.choices])}'
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        paginated_orders = paginator.paginate_queryset(orders, request)
        
        if paginated_orders is not None:
            serializer = OrderSerializer(paginated_orders, many=True)
            response = paginator.get_paginated_response(serializer.data)
            # Add custom message and status to paginated response
            response.data['message'] = 'Orders retrieved successfully'
            response.data['status'] = 'success'
            response.data['data'] = response.data.pop('results')
            return response
        
        # If no pagination
        serializer = OrderSerializer(orders, many=True)
        return Response(
            {
                'message': 'Orders retrieved successfully',
                'status': 'success',
                'count': orders.count(),
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
