from types import SimpleNamespace

from rest_framework import status
from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from apps.common.throttles import OrderCreateThrottle
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample

from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderDetailSerializer,
    OrderSetPaymentCardSerializer,
    PriceEstimateSerializer,
    PriceEstimateManagePriceSerializer,
    OrderItemUpdateSerializer,
    OrderItemSerializer,
    OrderItemManagePriceSerializer,
    UserOrderPreferencesSerializer,
    AdditionalPassengerSerializer,
    OrderScheduleSerializer,
    DriverNearbyOrderSerializer,
    DriverOrderActionSerializer,
    DriverOrderLifecycleSerializer,
    DriverPickupSerializer,
    DriverCompleteSerializer,
    DriverLocationUpdateSerializer,
    DriverLocationSerializer,
    DriverInfoSerializer,
    DriverOnlineStatusSerializer,
    DriverEarningsSerializer,
    TripRatingCreateSerializer,
    TripRatingSerializer,
    DriverRiderRatingCreateSerializer,
    DriverRiderRatingSerializer,
    RatingFeedbackTagSerializer,
)
from .serializers.cancel_order import OrderCancelSerializer, DriverCancelSerializer
from .models import (
    Order,
    OrderItem,
    OrderDriver,
    UserOrderPreferences,
    TripRating,
    DriverRiderRating,
    DriverCashout,
    CancelOrder,
)
from apps.accounts.models import CustomUser, DriverPreferences
from apps.payment.models import SavedCard
from .services.surge_pricing_service import calculate_distance
from .services.driver_assignment_service import DriverAssignmentService
from .services.driver_dashboard import get_driver_dashboard, get_cash_history, get_ride_history, get_driver_earnings

class OrderCreateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [OrderCreateThrottle]

    @extend_schema(
        tags=['Rider: Orders'],
        summary='Create order',
        description=(
            'Create order and order items. Optional ride_type_id: tariff (RideType) ID; '
            'if omitted, first active is used. Optional payment_type: ``card`` (default), '
            '``cash``, or ``hola_wallet_cash``. Optional adjusted_price: reja/min-max '
            'qoidalariga mos narx (``price-estimate/manage-price/`` dan keyin).'
        ),
        request=OrderCreateSerializer,
        examples=[
            OpenApiExample(
                'Create order with ride type',
                value={
                    'address_from': 'string A',
                    'address_to': 'string B',
                    'latitude_from': 39.8046579,
                    'longitude_from': 64.4263534,
                    'latitude_to': 39.8009868,
                    'longitude_to': 64.4272017,
                    'order_type': 2,
                    'ride_type_id': 1,
                    'payment_type': 'card',
                },
                request_only=True,
            ),
        ],
    )
    async def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            order = await sync_to_async(serializer.save)()
            
            order = await Order.objects.select_related('user', 'saved_card').prefetch_related(
                'order_items__ride_type'
            ).aget(pk=order.pk)
            
            order_serializer = OrderSerializer(order, context={'request': request})
            serializer_data = await sync_to_async(lambda: order_serializer.data)()
            
            return Response(
                {
                    'message': 'Order created successfully',
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

class OrderPreferencesGetView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Preferences'],
        summary='Get user order preferences (pre-order)',
        description='Fetch current rider preference template used before creating orders. Returns one saved profile for request.user; order_id is not required.',
        responses={200: UserOrderPreferencesSerializer},
    )
    async def get(self, request):
        preferences = await UserOrderPreferences.objects.filter(
            user=request.user
        ).afirst()

        if not preferences:
            default_preferences = UserOrderPreferences(user=request.user)
            serializer = UserOrderPreferencesSerializer(default_preferences, context={'request': request})
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Preferences not set yet, returning defaults',
                    'status': 'success',
                    'data': serializer_data
                },
                status=status.HTTP_200_OK
            )

        serializer = UserOrderPreferencesSerializer(preferences, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()

        return Response(
            {
                'message': 'Preferences retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )

class OrderPreferencesCreateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Preferences'],
        summary='Create/update user order preferences (pre-order)',
        description='Create or replace the current rider preference template. This endpoint is pre-order and works without order_id.',
        request=UserOrderPreferencesSerializer,
        responses={200: UserOrderPreferencesSerializer},
    )
    async def post(self, request):
        current = await UserOrderPreferences.objects.filter(user=request.user).afirst()
        serializer = UserOrderPreferencesSerializer(
            current,
            data=request.data,
            context={'request': request},
            partial=current is not None,
        )

        is_valid = await sync_to_async(lambda: serializer.is_valid())()

        if is_valid:
            preferences = await sync_to_async(serializer.save)()
            pref_serializer = UserOrderPreferencesSerializer(preferences, context={'request': request})
            serializer_data = await sync_to_async(lambda: pref_serializer.data)()

            return Response(
                {
                    'message': 'Preferences saved successfully',
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

    @extend_schema(
        tags=['Rider: Preferences'],
        summary='Update user order preferences (pre-order)',
        description='Partially update fields of the current rider preference template (pre-order profile).',
        request=UserOrderPreferencesSerializer,
        responses={200: UserOrderPreferencesSerializer},
    )
    async def put(self, request):
        return await self.post(request)

class AdditionalPassengerCreateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rider: Orders'], summary='Add passenger', description='Add an extra passenger record to an existing order owned by the current rider.', request=AdditionalPassengerSerializer)
    async def post(self, request):
        serializer = AdditionalPassengerSerializer(data=request.data, context={'request': request})
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            passenger = await sync_to_async(serializer.save)()

            def _notify_accepted_driver_additional_passenger():
                od = (
                    OrderDriver.objects.filter(
                        order_id=passenger.order_id,
                        status=OrderDriver.DriverRequestStatus.ACCEPTED,
                    )
                    .select_related('order')
                    .first()
                )
                if not od:
                    return
                from apps.notification.services import enqueue_push_to_user_id

                order_obj = od.order
                label = (passenger.full_name or '').strip() or 'A passenger'
                enqueue_push_to_user_id(
                    od.driver_id,
                    title='Additional passenger',
                    body=f'{label} was added to order {order_obj.order_code}.',
                    data={
                        'type': 'additional_passenger',
                        'order_id': order_obj.id,
                        'order_code': order_obj.order_code or '',
                        'additional_passenger_id': passenger.id,
                    },
                )

            await sync_to_async(_notify_accepted_driver_additional_passenger)()

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
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rider: Orders'], summary='Create schedule', description='Attach or update scheduling info for an order (planned pickup/drop-off time window).', request=OrderScheduleSerializer)
    async def post(self, request):
        serializer = OrderScheduleSerializer(data=request.data, context={'request': request})
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            schedule = await sync_to_async(serializer.save)()
            
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
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver: Orders & trips'], summary='Nearby orders', description='List pending ride requests near the current driver with distance and order brief payload. Driver role required.')
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

        order_drivers_qs = (
            OrderDriver.objects.filter(
                driver=user,
                status=OrderDriver.DriverRequestStatus.REQUESTED
            )
            .select_related('order', 'order__user')
            .prefetch_related('order__order_items')
            .order_by('-requested_at')
        )
        order_drivers = await sync_to_async(list)(order_drivers_qs)

        nearby_orders = []
        for order_driver in order_drivers:
            order = order_driver.order
            
            if order.status != Order.OrderStatus.PENDING:
                continue
            
            from django.utils import timezone
            from apps.order.services.driver_assignment_service import DriverAssignmentService
            
            if order_driver.requested_at:
                time_elapsed = timezone.now() - order_driver.requested_at
                if time_elapsed.total_seconds() >= DriverAssignmentService.TIMEOUT_SECONDS:
                    order_driver.status = OrderDriver.DriverRequestStatus.TIMEOUT
                    await sync_to_async(order_driver.save)()

                    try:
                        from apps.order.services.driver_orders_websocket import send_order_timeout_to_driver
                        await sync_to_async(send_order_timeout_to_driver)(user.id, order.id)
                    except Exception:
                        pass

                    try:
                        next_order_driver = await sync_to_async(DriverAssignmentService.assign_to_next_driver)(order)
                        if next_order_driver:
                            pass
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to reassign order {order.id} after timeout: {e}")
                    
                    continue
            
            first_item = order.order_items.first()
            if not first_item or not first_item.latitude_from or not first_item.longitude_from:
                continue

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
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver: Orders & trips'], summary='Accept/Reject order', description='Driver decision endpoint for a pending request. Body: order_id and action=accept|reject. Updates assignment and notifies rider in real time.', request=DriverOrderActionSerializer)
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

        if order.status != Order.OrderStatus.PENDING and action == 'accept':
            return Response(
                {
                    'message': 'Order is not available for accepting',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone

        if action == 'accept':
            order_driver.status = OrderDriver.DriverRequestStatus.ACCEPTED
            order.status = Order.OrderStatus.ACCEPTED
            order_driver.responded_at = timezone.now()
            await sync_to_async(order_driver.save)()
            await sync_to_async(order.save)()
            
            try:
                from apps.chat.models import ChatRoom
                def set_receiver_and_status():
                    ChatRoom.objects.filter(order=order).update(
                        receiver=user,
                        status=ChatRoom.RoomStatus.PROCESS,
                    )
                await sync_to_async(set_receiver_and_status)()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to update ChatRoom for order {order.id}: {e}")
            
            try:
                from apps.notification.tasks import send_push_notification_async

                send_push_notification_async.delay(
                    user_id=order.user_id,
                    title='Driver found',
                    body='Your ride has been accepted. Driver is on the way.',
                    data={
                        'order_id': order.id,
                        'order_code': order.order_code,
                        'type': 'driver_accepted',
                    },
                )
            except ImportError:
                from apps.notification.services import send_push_to_user

                try:
                    send_push_to_user(
                        user=order.user,
                        title='Driver found',
                        body='Your ride has been accepted. Driver is on the way.',
                        data={
                            'order_id': order.id,
                            'order_code': order.order_code,
                            'type': 'driver_accepted',
                        },
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        'Failed to send push to rider %s (sync): %s', order.user_id, e
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    'Failed to schedule push to rider %s: %s', order.user_id, e
                )

            try:
                from apps.order.services.rider_orders_websocket import send_rider_order_driver_accepted

                await sync_to_async(send_rider_order_driver_accepted)(order.id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    'Failed to send rider WebSocket accept for order %s: %s', order.id, e
                )
        else:
            order_driver.status = OrderDriver.DriverRequestStatus.REJECTED
            order_driver.responded_at = timezone.now()
            await sync_to_async(order_driver.save)()
            rejected_driver_id = user.id
            reassigned = False

            try:
                next_order_driver = await sync_to_async(DriverAssignmentService.assign_to_next_driver)(order)
                if next_order_driver:
                    message = "Order rejected. Reassigned to next driver."
                    reassigned = True
                else:
                    message = "Order rejected. No more drivers available at the moment."
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to reassign order {order.id} after rejection: {e}")
                message = "Order rejected successfully."

            try:
                from apps.order.services.rider_orders_websocket import send_rider_order_driver_rejected

                await sync_to_async(send_rider_order_driver_rejected)(
                    order.id,
                    rejected_driver_id=rejected_driver_id,
                    rider_message=message,
                    reassigned=reassigned,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    'Failed to send rider WebSocket reject for order %s: %s', order.id, e
                )

            try:
                from apps.notification.tasks import send_push_notification_async

                send_push_notification_async.delay(
                    user_id=order.user_id,
                    title='Order update',
                    body=message,
                    data={
                        'order_id': order.id,
                        'order_code': order.order_code,
                        'type': 'driver_rejected',
                        'reassigned': str(reassigned).lower(),
                    },
                )
            except ImportError:
                from apps.notification.services import send_push_to_user

                try:
                    send_push_to_user(
                        user=order.user,
                        title='Order update',
                        body=message,
                        data={
                            'order_id': order.id,
                            'order_code': order.order_code,
                            'type': 'driver_rejected',
                            'reassigned': str(reassigned).lower(),
                        },
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        'Failed to send reject push to rider %s (sync): %s', order.user_id, e
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    'Failed to schedule reject push to rider %s: %s', order.user_id, e
                )

        return Response(
            {
                'message': message if action == 'reject' else f"Order {action}ed successfully",
                'status': 'success',
            },
            status=status.HTTP_200_OK,
        )


class DriverOnTheWayView(AsyncAPIView):
    """accepted → on_the_way: driver is heading to pickup."""

    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(
        tags=['Driver: Orders & trips'],
        summary='Driver: on the way to pickup',
        description=(
            'Sets order status to **on_the_way** after **accepted**. '
            'Lifecycle: accepted → on_the_way → arrived → pickup (in_progress) → complete.'
        ),
        request=DriverOrderLifecycleSerializer,
    )
    async def post(self, request):
        user = request.user
        if not await self._check_driver_role(user):
            return Response(
                {'message': 'Only drivers can access this endpoint', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DriverOrderLifecycleSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_id = (await sync_to_async(lambda: serializer.validated_data)())['order_id']

        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        order_driver = await OrderDriver.objects.filter(
            order=order,
            driver=user,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        ).afirst()

        if not order_driver:
            return Response(
                {
                    'message': 'This order is not assigned to you or is not in accepted state',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status != Order.OrderStatus.ACCEPTED:
            return Response(
                {
                    'message': (
                        f'Order must be accepted before marking on the way. Current status: {order.status}'
                    ),
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.OrderStatus.ON_THE_WAY
        await sync_to_async(order.save)(update_fields=['status'])

        try:
            from apps.notification.services import send_push_to_user

            send_push_to_user(
                user=order.user,
                title='Driver on the way',
                body='Your driver is heading to the pickup location.',
                data={
                    'order_id': order.id,
                    'order_code': order.order_code or '',
                    'type': 'driver_on_the_way',
                },
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                'Failed to send on-the-way push to rider %s: %s', order.user_id, e
            )

        try:
            from apps.order.services.rider_orders_websocket import notify_rider_order_updated

            await sync_to_async(notify_rider_order_updated)(
                order.id,
                'on_the_way',
                'Driver is on the way to pickup.',
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                'Failed rider WebSocket on_the_way for order %s: %s', order.id, e
            )

        return Response(
            {'message': 'Order marked as on the way', 'status': 'success'},
            status=status.HTTP_200_OK,
        )


class DriverArrivedView(AsyncAPIView):
    """on_the_way → arrived: driver at pickup point."""

    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(
        tags=['Driver: Orders & trips'],
        summary='Driver: arrived at pickup',
        description='Sets order status to **arrived** when current status is **on_the_way**.',
        request=DriverOrderLifecycleSerializer,
    )
    async def post(self, request):
        user = request.user
        if not await self._check_driver_role(user):
            return Response(
                {'message': 'Only drivers can access this endpoint', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DriverOrderLifecycleSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_id = (await sync_to_async(lambda: serializer.validated_data)())['order_id']

        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        order_driver = await OrderDriver.objects.filter(
            order=order,
            driver=user,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        ).afirst()

        if not order_driver:
            return Response(
                {
                    'message': 'This order is not assigned to you or is not in accepted state',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status != Order.OrderStatus.ON_THE_WAY:
            return Response(
                {
                    'message': (
                        f'Order must be on_the_way before marking arrived. Current status: {order.status}'
                    ),
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.OrderStatus.ARRIVED
        await sync_to_async(order.save)(update_fields=['status'])

        try:
            from apps.notification.services import send_push_to_user

            send_push_to_user(
                user=order.user,
                title='Driver has arrived',
                body='Your driver is at the pickup location.',
                data={
                    'order_id': order.id,
                    'order_code': order.order_code or '',
                    'type': 'driver_arrived',
                },
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                'Failed to send arrived push to rider %s: %s', order.user_id, e
            )

        try:
            from apps.order.services.rider_orders_websocket import notify_rider_order_updated

            await sync_to_async(notify_rider_order_updated)(
                order.id,
                'arrived',
                'Driver arrived at pickup.',
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                'Failed rider WebSocket arrived for order %s: %s', order.id, e
            )

        return Response(
            {'message': 'Order marked as arrived at pickup', 'status': 'success'},
            status=status.HTTP_200_OK,
        )


class DriverPickupView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(
        tags=['Driver: Orders & trips'],
        summary='Confirm pickup',
        description=(
            'Mark trip as **in_progress** after rider is in the vehicle. '
            'Requires order status **arrived** (after **on_the_way**). Body: order_id.'
        ),
        request=DriverPickupSerializer,
    )
    async def post(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DriverPickupSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        order_id = (await sync_to_async(lambda: serializer.validated_data)())['order_id']

        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        order_driver = await OrderDriver.objects.filter(
            order=order,
            driver=user,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        ).afirst()

        if not order_driver:
            return Response(
                {'message': 'This order is not assigned to you or is not in accepted state', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status != Order.OrderStatus.ARRIVED:
            return Response(
                {
                    'message': (
                        f'Order must be arrived at pickup before confirming pickup. '
                        f'Use driver/on-the-way/ then driver/arrived/ first. Current status: {order.status}'
                    ),
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone
        now = timezone.now()
        order_driver.pickup_confirmed_at = now
        order.status = Order.OrderStatus.IN_PROGRESS
        await sync_to_async(order_driver.save)(update_fields=['pickup_confirmed_at'])
        await sync_to_async(order.save)(update_fields=['status'])

        try:
            from apps.notification.services import send_push_to_user
            send_push_to_user(
                user=order.user,
                title="Ride started",
                body="Driver has picked you up. Your ride has started.",
                data={"order_id": order.id, "order_code": order.order_code, "type": "ride_started"}
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send pickup push to rider {order.user.id}: {e}")

        try:
            from apps.order.services.rider_orders_websocket import notify_rider_order_updated

            await sync_to_async(notify_rider_order_updated)(
                order.id,
                'in_progress',
                'Driver picked you up. Ride in progress.',
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'Failed to send rider WebSocket pickup update for order %s: %s', order.id, e
            )

        return Response({'message': 'Pickup confirmed successfully', 'status': 'success'}, status=status.HTTP_200_OK)


class DriverCompleteView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(
        tags=['Driver: Orders & trips'],
        summary='Confirm complete/dropoff',
        description=(
            'Mark trip as completed after drop-off. Body: order_id. '
            'If payment_type is **card**, charges the rider via Stripe (order total from order items) '
            'before completing; funds go to the driver’s Stripe Connect account when '
            '`stripe_connect_account_id` is set on the driver user, otherwise to the platform account. '
            'Cash / hola_wallet_cash skip Stripe.'
        ),
        request=DriverCompleteSerializer,
    )
    async def post(self, request):
        import stripe

        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DriverCompleteSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        order_id = (await sync_to_async(lambda: serializer.validated_data)())['order_id']

        try:
            order = await Order.objects.select_related('user', 'saved_card').prefetch_related(
                'order_items'
            ).aget(id=order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        if order.status == Order.OrderStatus.COMPLETED:
            return Response(
                {'message': 'Order is already completed', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_driver = await OrderDriver.objects.filter(
            order=order,
            driver=user,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        ).afirst()

        if not order_driver:
            return Response(
                {'message': 'This order is not assigned to you or is not in accepted state', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status != Order.OrderStatus.IN_PROGRESS:
            return Response(
                {'message': f'Order must be in progress to complete. Current status: {order.status}', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stripe_pi = ''
        stripe_pay_status = Order.StripeTripPaymentStatus.NOT_APPLICABLE
        stripe_cents = None
        stripe_currency = ''

        if order.payment_type == Order.PaymentType.CARD:
            from apps.payment.services.trip_charge import charge_trip_card_payment

            try:
                result = await sync_to_async(charge_trip_card_payment)(order, user)
            except ValueError as e:
                return Response(
                    {'message': str(e), 'status': 'error'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except stripe.error.StripeError as e:
                msg = getattr(e, 'user_message', None) or str(e)

                async def _persist_err():
                    o = await Order.objects.aget(pk=order.pk)
                    o.stripe_trip_payment_error = (msg or '')[:2000]
                    await sync_to_async(o.save)(update_fields=['stripe_trip_payment_error', 'updated_at'])

                await _persist_err()
                return Response(
                    {'message': msg, 'status': 'error'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            stripe_pi = result['payment_intent_id']
            stripe_pay_status = Order.StripeTripPaymentStatus.SUCCEEDED
            stripe_cents = result['amount_cents']
            stripe_currency = result['currency']

        from django.utils import timezone
        now = timezone.now()
        order_driver.completed_at = now
        order.status = Order.OrderStatus.COMPLETED
        order.stripe_trip_payment_intent_id = stripe_pi
        order.stripe_trip_payment_status = stripe_pay_status
        order.stripe_trip_payment_amount_cents = stripe_cents
        order.stripe_trip_payment_currency = stripe_currency or ''
        order.stripe_trip_payment_error = ''
        await sync_to_async(order_driver.save)(update_fields=['completed_at'])
        await sync_to_async(order.save)(
            update_fields=[
                'status',
                'stripe_trip_payment_intent_id',
                'stripe_trip_payment_status',
                'stripe_trip_payment_amount_cents',
                'stripe_trip_payment_currency',
                'stripe_trip_payment_error',
                'updated_at',
            ]
        )
        try:
            from apps.chat.models import ChatRoom
            await sync_to_async(lambda: ChatRoom.objects.filter(order=order).update(status=ChatRoom.RoomStatus.COMPLETED))()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to update ChatRoom status for order {order.id}: {e}")
        try:
            from apps.notification.services import send_push_to_user
            send_push_to_user(
                user=order.user,
                title="Ride completed",
                body="Thank you for riding with us. Your ride has been completed.",
                data={"order_id": order.id, "order_code": order.order_code, "type": "ride_completed"}
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send complete push to rider {order.user.id}: {e}")

        try:
            from apps.order.services.rider_orders_websocket import notify_rider_order_updated

            await sync_to_async(notify_rider_order_updated)(
                order.id,
                'completed',
                'Your ride has been completed.',
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'Failed to send rider WebSocket complete for order %s: %s', order.id, e
            )

        payment_info = {
            'payment_type': order.payment_type,
            'is_paid': bool(order.payment_type != Order.PaymentType.CARD or stripe_pi),
            'stripe_trip_payment_status': order.stripe_trip_payment_status,
            'stripe_trip_payment_intent_id': order.stripe_trip_payment_intent_id or None,
            'stripe_trip_payment_amount_cents': order.stripe_trip_payment_amount_cents,
            'stripe_trip_payment_currency': order.stripe_trip_payment_currency or None,
        }
        return Response(
            {
                'message': 'Ride completed successfully',
                'status': 'success',
                'data': {
                    'order_id': order.id,
                    'order_code': order.order_code,
                    'order_status': order.status,
                    'payment': payment_info,
                },
            },
            status=status.HTTP_200_OK,
        )


class DriverCancelOrderView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver: Orders & trips'], summary='Cancel order (driver)', description='Driver-initiated cancellation. Body: order_id, reason, optional other_reason. Persists CancelOrder and notifies rider channels.', request=DriverCancelSerializer)
    async def post(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DriverCancelSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response({'message': 'Validation error', 'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = await sync_to_async(lambda: serializer.validated_data)()
        order_id = validated_data['order_id']
        reason = validated_data['reason']
        other_reason = validated_data.get('other_reason', '')

        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        order_driver = await OrderDriver.objects.filter(
            order=order,
            driver=user,
            status=OrderDriver.DriverRequestStatus.ACCEPTED,
        ).afirst()

        if not order_driver:
            return Response(
                {'message': 'This order is not assigned to you', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status == Order.OrderStatus.CANCELLED:
            return Response({'message': 'Order is already cancelled', 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        if order.status == Order.OrderStatus.COMPLETED:
            return Response({'message': 'Cannot cancel a completed order', 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        if order.status not in [
            Order.OrderStatus.ACCEPTED,
            Order.OrderStatus.ON_THE_WAY,
            Order.OrderStatus.ARRIVED,
            Order.OrderStatus.IN_PROGRESS,
        ]:
            return Response(
                {'message': f'Cannot cancel order with status: {order.status}', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.OrderStatus.CANCELLED
        await sync_to_async(order.save)(update_fields=['status'])
        try:
            from apps.chat.models import ChatRoom
            await sync_to_async(lambda: ChatRoom.objects.filter(order=order).update(status=ChatRoom.RoomStatus.CANCEL))()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to update ChatRoom status for order {order.id}: {e}")
        await sync_to_async(CancelOrder.objects.create)(
            order=order,
            driver=order_driver,
            cancelled_by=CancelOrder.CancelledBy.DRIVER,
            reason=reason,
            other_reason=other_reason if reason == 'other' else None
        )

        try:
            from apps.notification.services import send_push_to_user
            send_push_to_user(
                user=order.user,
                title="Ride cancelled",
                body="Your ride has been cancelled by the driver.",
                data={"order_id": order.id, "order_code": order.order_code, "type": "ride_cancelled_by_driver"}
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send cancel push to rider {order.user.id}: {e}")

        try:
            from apps.order.services.rider_orders_websocket import notify_rider_order_updated

            await sync_to_async(notify_rider_order_updated)(
                order.id,
                'cancelled_driver',
                'Your ride has been cancelled by the driver.',
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'Failed to send rider WebSocket driver cancel for order %s: %s', order.id, e
            )

        return Response({'message': 'Order cancelled successfully', 'status': 'success'}, status=status.HTTP_200_OK)


class DriverLocationUpdateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver: Location'], summary='Update location', description="Update driver's GPS location. Body: latitude, longitude. Role: Driver.", request=DriverLocationUpdateSerializer)
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

        try:
            from .services.order_tracking_websocket import notify_driver_location_updated

            await sync_to_async(notify_driver_location_updated)(
                user.id,
                user.latitude,
                user.longitude,
                user.updated_at,
            )
        except Exception:
            # Location update API should still succeed even if websocket push fails.
            pass

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
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rider: Live tracking'], summary='Driver location for order', description="Rider: get driver's current location for an order (when driver is assigned).")
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

        from apps.accounts.models import VehicleDetails
        vehicle = await sync_to_async(
            lambda: VehicleDetails.objects.filter(user=driver).select_related('default_ride_type').first()
        )()

        completed_trips_count = await sync_to_async(
            lambda: Order.objects.filter(
                order_drivers__driver=driver,
                order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
                status=Order.OrderStatus.COMPLETED
            ).count()
        )()

        ratings = await sync_to_async(list)(
            TripRating.objects.filter(driver=driver, status='approved').values_list('rating', flat=True)
        )
        average_rating = 0.0
        if ratings:
            average_rating = round(sum(ratings) / len(ratings), 2)

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
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Pricing'],
        summary='Price estimate',
        description=(
            'Barcha aktiv ride type lar uchun narx. Har bir ``estimates`` elementida '
            '``id`` = ``ride_type_id`` (reja bosqichi; buyurtma hali yo‘q). '
            'Buyurtma yaratilgach narxni o‘zgartirish uchun ``order_items[].id`` bilan '
            '``PATCH .../order-item/{id}/manage-price/`` ishlating.'
        ),
        request=PriceEstimateSerializer,
    )
    async def post(self, request):
        from apps.order.models import RideType
        from apps.order.services.surge_pricing_service import SurgePricingService, calculate_distance
        from decimal import Decimal
        
        serializer = PriceEstimateSerializer(data=request.data)
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            
            lat_from = float(validated_data['latitude_from'])
            lon_from = float(validated_data['longitude_from'])
            lat_to = float(validated_data['latitude_to'])
            lon_to = float(validated_data['longitude_to'])
            
            distance_km = await sync_to_async(calculate_distance)(lat_from, lon_from, lat_to, lon_to)
            
            surge_multiplier = await sync_to_async(SurgePricingService.get_multiplier)(lat_from, lon_from)
            
            ride_types = await sync_to_async(list)(RideType.objects.filter(is_active=True))
            
            estimates = []
            for ride_type in ride_types:
                if ride_type.base_price and ride_type.price_per_km:
                    price = await sync_to_async(ride_type.calculate_price)(distance_km, surge_multiplier)
                    estimates.append({
                        'id': ride_type.id,
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
        
        errors = await sync_to_async(lambda: serializer.errors)()
        return Response(
            {
                'message': 'Validation error',
                'status': 'error',
                'errors': errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class PriceEstimateManagePriceView(AsyncAPIView):
    """
    Reja (order create oldin): bir ride_type va yo‘nalish uchun tanlangan narxni
    min/max oralig‘ida tekshirish. DB ga yozmaydi.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Pricing'],
        summary='Plan: validate adjusted price (pre-order)',
        description=(
            '``price-estimate`` dagi ``id`` / ``ride_type_id`` va xuddi shu koordinatalar bilan '
            'yuboring. Muvaffaqiyatli javobda ``valid``: true va min/max/calculated qaytadi. '
            'Buyurtma yaratishda shu narxni ``POST /order/create/`` bodyda ``adjusted_price`` '
            'sifatida yuborishingiz mumkin.'
        ),
        request=PriceEstimateManagePriceSerializer,
    )
    async def post(self, request):
        from apps.order.models import RideType
        from apps.order.services.surge_pricing_service import SurgePricingService
        from decimal import Decimal, ROUND_HALF_UP

        serializer = PriceEstimateManagePriceSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = await sync_to_async(lambda: serializer.validated_data)()
        lat_from = float(data['latitude_from'])
        lon_from = float(data['longitude_from'])
        lat_to = float(data['latitude_to'])
        lon_to = float(data['longitude_to'])
        ride_type_id = data['ride_type_id']
        adjusted = Decimal(str(data['adjusted_price']))

        distance_km = await sync_to_async(calculate_distance)(lat_from, lon_from, lat_to, lon_to)
        surge_multiplier = await sync_to_async(SurgePricingService.get_multiplier)(lat_from, lon_from)

        try:
            ride_type = await RideType.objects.aget(id=ride_type_id, is_active=True)
        except RideType.DoesNotExist:
            return Response(
                {'message': 'Ride type not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not ride_type.base_price or not ride_type.price_per_km:
            return Response(
                {'message': 'Ride type has no pricing configured', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        calculated = await sync_to_async(ride_type.calculate_price)(distance_km, surge_multiplier)
        original = Decimal(str(calculated)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        min_price = (original * (Decimal('1.00') - Decimal('0.20'))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        max_price = (original * (Decimal('1.00') + Decimal('0.50'))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        valid = min_price <= adjusted <= max_price
        body = {
            'message': 'Price validated successfully' if valid else 'Price is outside allowed range',
            'status': 'success' if valid else 'error',
            'data': {
                'id': ride_type.id,
                'ride_type_id': ride_type.id,
                'distance_km': round(distance_km, 2),
                'surge_multiplier': surge_multiplier,
                'calculated_price': float(original),
                'min_price': float(min_price),
                'max_price': float(max_price),
                'adjusted_price': float(adjusted),
                'valid': valid,
            },
        }
        return Response(body, status=status.HTTP_200_OK if valid else status.HTTP_400_BAD_REQUEST)


class OrderItemUpdateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rider: Order items'], summary='Update order item', description='Update mutable order-item fields (for example ride_type) for an order owned by current rider.', request=OrderItemUpdateSerializer)
    async def patch(self, request, order_item_id):
        try:
            order_item = await OrderItem.objects.select_related(
                'order__user', 'ride_type'
            ).aget(id=order_item_id)
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
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            updated_item = await sync_to_async(serializer.save)()
            updated_item = await OrderItem.objects.select_related('ride_type').aget(pk=updated_item.pk)
            
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
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Order items'],
        summary='Manage order item price',
        description=(
            'URL dagi ``order_item_id`` — **OrderItem** jadvalidagi primary key '
            '(``POST /order/create/`` yoki buyurtma detalidagi ``order_items[].id``). '
            '``GET/POST price-estimate`` dagi ``id`` bu yerda **emas** (u reja uchun '
            '``ride_type_id`` bilan bir xil). Buyurtma ``pending`` bo‘lsa ham '
            '(masalan, haydovchi kutish) ishlaydi — faqat buyurtma egasi.'
        ),
        request=OrderItemManagePriceSerializer,
    )
    async def patch(self, request, order_item_id):
        try:
            order_item = await OrderItem.objects.select_related(
                'order__user', 'ride_type'
            ).aget(id=order_item_id)
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
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            adjusted_price = validated_data['adjusted_price']
            
            if not order_item.original_price:
                return Response(
                    {
                        'message': 'Original price not set. Please set ride_type first.',
                        'status': 'error'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not order_item.min_price or not order_item.max_price:
                min_price, max_price = await sync_to_async(order_item.calculate_price_range)()
                order_item.min_price = min_price
                order_item.max_price = max_price
                await sync_to_async(order_item.save)()
            
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
            
            try:
                await sync_to_async(order_item.adjust_price)(float(adjusted_price))
                order_item = await OrderItem.objects.select_related('ride_type').aget(pk=order_item.pk)
                
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
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rider: Orders'], summary='Cancel order', description='Rider-initiated cancellation endpoint. Body: reason and optional other_reason. Writes cancellation meta and broadcasts updates to rider/driver sockets.', request=OrderCancelSerializer)
    async def post(self, request, order_id):
        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
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
        
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            validated_data = await sync_to_async(lambda: serializer.validated_data)()
            reason = validated_data['reason']
            other_reason = validated_data.get('other_reason', '')
            
            order.status = Order.OrderStatus.CANCELLED
            await sync_to_async(order.save)()
            try:
                from apps.chat.models import ChatRoom
                await sync_to_async(lambda: ChatRoom.objects.filter(order=order).update(status=ChatRoom.RoomStatus.CANCEL))()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to update ChatRoom status for order {order.id}: {e}")
            def _cancel_order_driver_for_record():
                od = (
                    OrderDriver.objects.select_related('driver')
                    .filter(
                        order=order,
                        status=OrderDriver.DriverRequestStatus.ACCEPTED,
                    )
                    .first()
                )
                if od:
                    return od
                return (
                    OrderDriver.objects.select_related('driver')
                    .filter(order=order)
                    .first()
                )

            order_driver = await sync_to_async(_cancel_order_driver_for_record)()
            
            await sync_to_async(CancelOrder.objects.create)(
                order=order,
                driver=order_driver,
                cancelled_by=CancelOrder.CancelledBy.RIDER,
                reason=reason,
                other_reason=other_reason if reason == CancelOrder.CancelReason.OTHER else None
            )

            try:
                from apps.order.services.rider_orders_websocket import notify_rider_order_updated

                await sync_to_async(notify_rider_order_updated)(
                    order.id,
                    'cancelled_rider',
                    'Ride cancelled.',
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    'Failed to send rider WebSocket rider cancel for order %s: %s', order.id, e
                )

            try:
                from apps.order.services.driver_orders_websocket import (
                    notify_drivers_order_cancelled_by_rider,
                )

                await sync_to_async(notify_drivers_order_cancelled_by_rider)(
                    order.id, request
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    'Failed to send driver WebSocket rider cancel for order %s: %s',
                    order.id,
                    e,
                )

            order = await Order.objects.select_related('user').prefetch_related(
                'order_items__ride_type',
                'order_drivers__driver'
            ).aget(pk=order.pk)
            
            order_serializer = OrderSerializer(order, context={'request': request})
            serializer_data = await sync_to_async(lambda: order_serializer.data)()
            
            return Response(
                {
                    'message': 'Order cancelled successfully',
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

class MyOrderListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Orders'],
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
        from rest_framework.pagination import PageNumberPagination
        
        orders_queryset = Order.objects.filter(user=request.user).select_related(
            'user', 'saved_card'
        ).prefetch_related(
            'order_items__ride_type',
            'order_preferences',
            'order_drivers__driver',
            'additional_passengers',
        ).order_by('-created_at')
        
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
        
        orders = await sync_to_async(list)(orders_queryset)
        
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        paginated_orders = await sync_to_async(paginator.paginate_queryset)(orders, request)
        
        if paginated_orders is not None:
            serializer = OrderSerializer(paginated_orders, many=True, context={'request': request})
            serializer_data = await sync_to_async(lambda: serializer.data)()
            
            response = await sync_to_async(paginator.get_paginated_response)(serializer_data)
            response.data['message'] = 'Orders retrieved successfully'
            response.data['status'] = 'success'
            response.data['data'] = response.data.pop('results')
            return response
        
        serializer = OrderSerializer(orders, many=True, context={'request': request})
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


class OrderDetailView(AsyncAPIView):
    """
    Single order by id. Rider: own orders. Driver: orders linked via OrderDriver (any request status).
    """

    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    async def _can_access_order(self, user, order):
        if order.user_id == user.id:
            return True
        if not await self._check_driver_role(user):
            return False
        return await OrderDriver.objects.filter(order=order, driver=user).aexists()

    @extend_schema(
        tags=['Rider: Orders'],
        summary='Get order by ID',
        description=(
            'Returns one order with order_items, user, and when a driver has accepted — '
            '`driver` (profile, vehicle, images) and `order_driver` (assignment row). '
            'Rider: only their orders. Driver: orders where this driver has an OrderDriver row.'
        ),
        responses={200: OrderDetailSerializer},
    )
    async def get(self, request, order_id: int):
        try:
            order = await Order.objects.select_related('user', 'saved_card').prefetch_related(
                'order_items__ride_type',
                'order_preferences',
                'order_drivers__driver__vehicle_details__images',
                'additional_passengers',
            ).aget(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'message': 'Order not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not await self._can_access_order(request.user, order):
            return Response(
                {
                    'message': 'You do not have permission to view this order',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order_serializer = OrderDetailSerializer(order, context={'request': request})
        serializer_data = await sync_to_async(lambda: order_serializer.data)()
        return Response(
            {
                'message': 'Order retrieved successfully',
                'status': 'success',
                'data': serializer_data,
            },
            status=status.HTTP_200_OK,
        )


class OrderPaymentCardView(AsyncAPIView):
    """
    Rider: attach a saved card to an order (card payment). Sets payment_type to card.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Orders'],
        summary='Set order payment card',
        description=(
            'Body: ``card_id`` — primary key of a **rider** saved card belonging to the request user. '
            'Updates the order’s ``saved_card`` and sets ``payment_type`` to **card**. '
            'Not allowed for completed / cancelled / rejected orders.'
        ),
        request=OrderSetPaymentCardSerializer,
        responses={200: OrderDetailSerializer},
        examples=[
            OpenApiExample(
                'Set card',
                value={'card_id': 1},
                request_only=True,
            ),
        ],
    )
    async def patch(self, request, order_id: int):
        try:
            order = await Order.objects.aget(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {'message': 'Order not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status in (
            Order.OrderStatus.COMPLETED,
            Order.OrderStatus.CANCELLED,
            Order.OrderStatus.REJECTED,
        ):
            return Response(
                {
                    'message': 'Cannot change payment card for this order.',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser_in = OrderSetPaymentCardSerializer(data=request.data)
        valid = await sync_to_async(lambda: ser_in.is_valid())()
        if not valid:
            errors = await sync_to_async(lambda: ser_in.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        card_id = ser_in.validated_data['card_id']
        try:
            card = await SavedCard.objects.aget(
                id=card_id,
                user=request.user,
                is_active=True,
                holder_role=SavedCard.HolderRole.RIDER,
            )
        except SavedCard.DoesNotExist:
            return Response(
                {
                    'message': 'Saved card not found or not available for this user.',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        def _save():
            order.saved_card = card
            order.payment_type = Order.PaymentType.CARD
            order.save(update_fields=['saved_card', 'payment_type', 'updated_at'])

        await sync_to_async(_save)()

        order = await Order.objects.select_related('user', 'saved_card').prefetch_related(
            'order_items__ride_type',
            'order_preferences',
            'order_drivers__driver__vehicle_details__images',
            'additional_passengers',
        ).aget(pk=order.pk)

        from apps.order.services.rider_orders_websocket import notify_rider_order_updated

        await sync_to_async(notify_rider_order_updated)(
            order.id,
            'payment_card',
            'Payment card updated',
        )

        order_serializer = OrderDetailSerializer(order, context={'request': request})
        serializer_data = await sync_to_async(lambda: order_serializer.data)()
        return Response(
            {
                'message': 'Order payment card updated successfully',
                'status': 'success',
                'data': serializer_data,
            },
            status=status.HTTP_200_OK,
        )


class RiderActiveRideView(AsyncAPIView):
    """
    Resume UX: one call after app launch to know if the rider still has a trip in progress.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Active ride'],
        summary='Rider: active ride',
        description=(
            'Returns this user’s current order if status is pending, accepted, on_the_way, '
            'arrived, or in_progress; otherwise `has_active_ride` is false and `data` is null. '
            'Picks the most recently updated order when several match (edge case).'
        ),
        responses={200: OrderDetailSerializer},
    )
    async def get(self, request):
        from .services.active_ride import get_rider_active_order

        order = await sync_to_async(get_rider_active_order)(request.user)
        if not order:
            return Response(
                {
                    'message': 'No active ride',
                    'status': 'success',
                    'has_active_ride': False,
                    'data': None,
                },
                status=status.HTTP_200_OK,
            )
        order_serializer = OrderDetailSerializer(order, context={'request': request})
        serializer_data = await sync_to_async(lambda: order_serializer.data)()
        return Response(
            {
                'message': 'Active ride',
                'status': 'success',
                'has_active_ride': True,
                'data': serializer_data,
            },
            status=status.HTTP_200_OK,
        )


class DriverActiveRideView(AsyncAPIView):
    """
    Resume UX: driver returns to the accepted trip after relaunching the app.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Driver: Orders & trips'],
        summary='Driver: active ride',
        description=(
            'Returns the order this driver has **accepted** (OrderDriver accepted) while the '
            'order is still in pending … in_progress. Does not return mere **requested** offers; '
            'use nearby orders / WebSocket for those.'
        ),
        responses={200: OrderDetailSerializer},
    )
    async def get(self, request):
        from .services.active_ride import get_driver_active_order

        order = await sync_to_async(get_driver_active_order)(request.user)
        if not order:
            return Response(
                {
                    'message': 'No active ride',
                    'status': 'success',
                    'has_active_ride': False,
                    'data': None,
                },
                status=status.HTTP_200_OK,
            )
        order_serializer = OrderDetailSerializer(order, context={'request': request})
        serializer_data = await sync_to_async(lambda: order_serializer.data)()
        return Response(
            {
                'message': 'Active ride',
                'status': 'success',
                'has_active_ride': True,
                'data': serializer_data,
            },
            status=status.HTTP_200_OK,
        )


class DriverDashboardView(AsyncAPIView):
    """Figma Earnings screen: overview, cash_history, ride_history."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Driver: Earnings & wallet'],
        summary='Driver dashboard',
        description='Overview, cashout history, ride history. Filters: filter=day|week|last_30|range, start_date, end_date (for range).',
        parameters=[
            OpenApiParameter('ride_limit', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Ride history limit (default 10)'),
            OpenApiParameter('filter', OpenApiTypes.STR, OpenApiParameter.QUERY, description='day, week, last_30, range'),
            OpenApiParameter('start_date', OpenApiTypes.DATE, OpenApiParameter.QUERY, description='YYYY-MM-DD (for range)'),
            OpenApiParameter('end_date', OpenApiTypes.DATE, OpenApiParameter.QUERY, description='YYYY-MM-DD (for range)'),
        ],
    )
    async def get(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        ride_limit = int(request.query_params.get('ride_limit', 10))
        filter_type = request.query_params.get('filter', 'last_30')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        overview, cash_history, ride_history = await sync_to_async(get_driver_dashboard)(
            user.id, ride_limit, filter_type, start_date, end_date
        )

        return Response({
            'message': 'Dashboard retrieved successfully',
            'status': 'success',
            'data': {
                'overview': overview,
                'cash_history': cash_history,
                'ride_history': ride_history,
            },
        }, status=status.HTTP_200_OK)

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names


class DriverEarningsView(AsyncAPIView):
    """Dedicated earnings summary for driver apps (matches DriverEarningsSerializer)."""

    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(
        tags=['Driver: Earnings & wallet'],
        summary='Driver earnings',
        description=(
            'Completed-trip earnings and distance: today, last 7 days, month-to-date, all-time. '
            'Optional query: today_target (default 10) — daily ride goal for UI.'
        ),
        parameters=[
            OpenApiParameter(
                'today_target',
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                required=False,
                description='Target rides for today (default 10)',
            ),
        ],
        responses={200: DriverEarningsSerializer},
    )
    async def get(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response(
                {'message': 'Only drivers can access this endpoint', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            today_target = int(request.query_params.get('today_target', 10))
        except (ValueError, TypeError):
            today_target = 10
        if today_target < 0:
            today_target = 10

        payload = await sync_to_async(get_driver_earnings)(user.id, today_target=today_target)
        serializer = DriverEarningsSerializer(instance=SimpleNamespace(**payload))
        data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Earnings retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DriverCashoutHistoryView(AsyncAPIView):
    """See all cash history. Paginated, same filters as dashboard."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Driver: Earnings & wallet'],
        summary='Cash history (See all)',
        description='Paginated cashout history. Filters: filter=day|week|last_30|range, start_date, end_date. Pagination: page, page_size.',
        parameters=[
            OpenApiParameter('filter', OpenApiTypes.STR, OpenApiParameter.QUERY, description='day, week, last_30, range'),
            OpenApiParameter('start_date', OpenApiTypes.DATE, OpenApiParameter.QUERY, description='YYYY-MM-DD (for range)'),
            OpenApiParameter('end_date', OpenApiTypes.DATE, OpenApiParameter.QUERY, description='YYYY-MM-DD (for range)'),
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, description='Page number (default 1)'),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, description='Page size (default 20)'),
        ],
    )
    async def get(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        filter_type = request.query_params.get('filter', 'last_30')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        data, total = await sync_to_async(get_cash_history)(
            user.id, filter_type, start_date, end_date, page, page_size
        )
        return Response({
            'message': 'Cash history retrieved successfully',
            'status': 'success',
            'data': data,
            'count': total,
            'page': page,
            'page_size': page_size,
        }, status=status.HTTP_200_OK)

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names


class DriverCashoutCreateView(AsyncAPIView):
    """Create cashout request. Figma: Cash out button."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Driver: Earnings & wallet'],
        summary='Cash out',
        description='Create a driver cashout request. Body: amount and payment_type (card|cash|hola_wallet_cash). Returns the created withdrawal row.',
    )
    async def post(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)
        amount = request.data.get('amount')
        if amount is None:
            return Response({'message': 'amount is required', 'status': 'error', 'errors': {'amount': ['This field is required.']}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from decimal import Decimal
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError('Amount must be positive')
        except (ValueError, TypeError):
            return Response({'message': 'Invalid amount', 'status': 'error', 'errors': {'amount': ['Must be a positive number.']}}, status=status.HTTP_400_BAD_REQUEST)
        payment_type = request.data.get('payment_type', 'card')
        if payment_type not in ('card', 'cash', 'hola_wallet_cash'):
            payment_type = 'card'
        cashout = await sync_to_async(DriverCashout.objects.create)(
            driver=user, amount=amount, payment_type=payment_type, status=DriverCashout.Status.PENDING
        )
        from .serializers.driver import DriverCashoutSerializer
        data = await sync_to_async(lambda: DriverCashoutSerializer(cashout).data)()
        return Response({'message': 'Cashout request submitted successfully', 'status': 'success', 'data': data}, status=status.HTTP_201_CREATED)

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names


class DriverRideHistoryView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(
        tags=['Driver: Earnings & wallet'],
        summary='Ride history (See all)',
        description='Paginated completed orders. Filters: filter=day|week|last_30|range, start_date, end_date. Pagination: page, page_size.',
        parameters=[
            OpenApiParameter('filter', OpenApiTypes.STR, OpenApiParameter.QUERY, description='day, week, last_30, range'),
            OpenApiParameter('start_date', OpenApiTypes.DATE, OpenApiParameter.QUERY, description='YYYY-MM-DD (for range)'),
            OpenApiParameter('end_date', OpenApiTypes.DATE, OpenApiParameter.QUERY, description='YYYY-MM-DD (for range)'),
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, description='Page number (default 1)'),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, description='Page size (default 10)'),
        ],
        responses={200: OrderSerializer(many=True)},
    )
    async def get(self, request):
        user = request.user
        is_driver = await self._check_driver_role(user)
        if not is_driver:
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        filter_type = request.query_params.get('filter', 'last_30')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        data, total = await sync_to_async(get_ride_history)(user.id, filter_type, start_date, end_date, page, page_size)
        return Response({
            'message': 'Ride history retrieved successfully',
            'status': 'success',
            'data': data,
            'count': total,
            'page': page,
            'page_size': page_size,
        }, status=status.HTTP_200_OK)

class DriverOnlineStatusView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def _check_driver_role(self, user):
        groups = await sync_to_async(list)(user.groups.all())
        names = [g.name for g in groups]
        return 'Driver' in names

    @extend_schema(tags=['Driver: Availability'], summary='Online status (GET)', description='Read current availability flag for the authenticated driver (`is_online`). Driver role required.')
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

    @extend_schema(tags=['Driver: Availability'], summary='Update online status', description='Update driver availability flag. Body requires boolean `is_online`; used by dispatch and nearby-order visibility.', request=DriverOnlineStatusSerializer)
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
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Trip ratings'], summary='Create rating', description='Rider submits rating/feedback for a completed trip and accepted driver assignment.', request=TripRatingCreateSerializer)
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

        trip_rating = await sync_to_async(TripRating.objects.create)(
            order=order,
            rider=user,
            driver=driver,
            rating=rating,
            comment=comment,
            tip_amount=tip_amount or 0,
        )

        if feedback_tag_ids:
            from apps.order.models import RatingFeedbackTag
            tags = await sync_to_async(list)(
                RatingFeedbackTag.objects.filter(
                    id__in=feedback_tag_ids, is_active=True, rating_target='rider_to_driver'
                )
            )
            await sync_to_async(trip_rating.feedback_tags.set)(tags)

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


def _create_driver_rider_rating(user_id, order_id, rating, comment, feedback_tag_ids):
    """Sync helper: create rating and return serialized data."""
    order = Order.objects.select_related('user').prefetch_related('order_drivers__driver').get(id=order_id)
    order_driver = order.order_drivers.filter(status=OrderDriver.DriverRequestStatus.ACCEPTED).first()
    if not order_driver or order_driver.driver_id != user_id:
        return None, 'Only the driver who completed this order can rate the rider'
    driver = order_driver.driver
    rider = order.user

    dr_rating = DriverRiderRating.objects.create(
        order=order,
        driver=driver,
        rider=rider,
        rating=rating,
        comment=comment or None,
    )
    if feedback_tag_ids:
        from apps.order.models import RatingFeedbackTag
        tags = list(RatingFeedbackTag.objects.filter(
            id__in=feedback_tag_ids, is_active=True, rating_target='driver_to_rider'
        ))
        dr_rating.feedback_tags.set(tags)

    dr_rating = DriverRiderRating.objects.select_related('order', 'driver', 'rider').prefetch_related('feedback_tags').get(pk=dr_rating.pk)
    response_serializer = DriverRiderRatingSerializer(dr_rating)
    return response_serializer.data, (rider.id, order.id, rating)


class DriverRiderRatingCreateView(AsyncAPIView):
    """
    Driver rates rider after completed trip. Figma: "Rate your trip" screen.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Trip ratings'],
        summary='Driver rate rider',
        description='Driver submits rating for rider after completed trip (1-5 stars, optional comment, feedback tags).',
        request=DriverRiderRatingCreateSerializer,
    )
    async def post(self, request):
        user = request.user

        serializer = DriverRiderRatingCreateSerializer(data=request.data)
        is_valid = await sync_to_async(lambda: serializer.is_valid())()

        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = await sync_to_async(lambda: serializer.validated_data)()
        order_id = validated_data['order_id']
        rating = validated_data['rating']
        comment = validated_data.get('comment')
        feedback_tag_ids = validated_data.get('feedback_tag_ids', [])

        try:
            response_data, notify_data = await sync_to_async(_create_driver_rider_rating)(
                user.id, order_id, rating, comment, feedback_tag_ids
            )
        except Order.DoesNotExist:
            return Response(
                {'message': 'Order not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if response_data is None:
            return Response(
                {'message': notify_data, 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            from apps.notification.tasks import send_push_notification_async
            rider_id, order_pk, rating_val = notify_data
            rating_text = f"{rating_val} star{'s' if rating_val != 1 else ''}"
            send_push_notification_async.delay(
                user_id=rider_id,
                title='New rating from driver',
                body=f'Driver rated you {rating_text}',
                data={'type': 'driver_rider_rating', 'order_id': order_pk, 'rating': rating_val},
            )
        except Exception:
            pass

        return Response(
            {
                'message': 'Rating submitted successfully. Rider has been notified.',
                'status': 'success',
                'data': response_data,
            },
            status=status.HTTP_201_CREATED,
        )


class RatingFeedbackTagsListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Trip ratings'],
        summary='Feedback tags',
        description='Get feedback tags by rating and target. target: rider_to_driver (rider rates driver), driver_to_rider (driver rates rider).',
        parameters=[
            OpenApiParameter('rating', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description='Rating value 1-5'),
            OpenApiParameter('target', OpenApiTypes.STR, OpenApiParameter.QUERY, required=True, description='rider_to_driver or driver_to_rider'),
        ],
    )
    async def get(self, request):
        rating = request.query_params.get('rating')
        target = request.query_params.get('target')

        if not rating:
            return Response(
                {'message': 'Rating parameter is required', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not target or target not in ('rider_to_driver', 'driver_to_rider'):
            return Response(
                {'message': 'Target must be rider_to_driver or driver_to_rider', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rating = int(rating)
        except (ValueError, TypeError):
            return Response(
                {'message': 'Rating must be a number between 1 and 5', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if rating < 1 or rating > 5:
            return Response(
                {'message': 'Rating must be between 1 and 5', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tag_type = 'positive' if rating >= 4 else 'negative'

        from apps.order.models import RatingFeedbackTag
        tags = await sync_to_async(list)(
            RatingFeedbackTag.objects.filter(
                tag_type=tag_type, rating_target=target, is_active=True
            ).order_by('name')
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
                    'rating_target': target,
                    'rating': rating,
                },
            },
            status=status.HTTP_200_OK,
        )


class OrderChatDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Trip chat'], summary='Get order chat', description='Return chat-room metadata for a specific order if rider/driver access is valid and room exists.')
    async def get(self, request, order_id: int):
        user = request.user

        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        order_driver = await OrderDriver.objects.filter(
            order=order,
            status=OrderDriver.DriverRequestStatus.ACCEPTED
        ).select_related('driver').afirst()

        is_rider = order.user == user
        is_driver = order_driver and order_driver.driver == user

        if not is_rider and not is_driver:
            return Response({'message': 'You do not have access to this chat', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        try:
            from apps.chat.models import ChatRoom
            from apps.chat.serializers.room import ChatRoomSerializer
            room = await ChatRoom.objects.select_related('order', 'initiator', 'receiver').aget(order=order)
        except Exception:
            room = None
        if not room:
            return Response({'message': 'Chat room not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ChatRoomSerializer(room, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response({'message': 'Chat retrieved successfully', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)


class OrderChatMessagesView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Trip chat'],
        summary='Get chat messages',
        description='Return paginated messages for an order chat and mark incoming messages as read for current participant.',
        parameters=[OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Number of messages per page')]
    )
    async def get(self, request, order_id: int):
        user = request.user

        try:
            order = await Order.objects.select_related('user').aget(id=order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        order_driver = await OrderDriver.objects.filter(
            order=order,
            status=OrderDriver.DriverRequestStatus.ACCEPTED
        ).select_related('driver').afirst()

        is_rider = order.user == user
        is_driver = order_driver and order_driver.driver == user

        if not is_rider and not is_driver:
            return Response({'message': 'You do not have access to this chat', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        try:
            from apps.chat.models import ChatRoom, ChatMessage
            from apps.chat.serializers.room import ChatMessageSerializer
            room = await ChatRoom.objects.aget(order=order)
        except Exception:
            room = None
        if not room:
            return Response({'message': 'Chat room not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        messages = ChatMessage.objects.filter(room=room).select_related('sender').order_by('created_at')
        messages_list = await sync_to_async(list)(messages)
        serializer = ChatMessageSerializer(messages_list, many=True, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()

        return Response({
            'message': 'Messages retrieved successfully',
            'status': 'success',
            'data': data,
            'count': len(messages_list)
        }, status=status.HTTP_200_OK)
        