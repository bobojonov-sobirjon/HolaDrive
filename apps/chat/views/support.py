from __future__ import annotations

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.common.views import AsyncAPIView
from apps.chat.models import SupportRoom, SupportMessage
from apps.chat.serializers import (
    SupportMessageCreateSerializer,
    SupportMessageSerializer,
    SupportRoomOpenSerializer,
    SupportRoomSerializer,
)
from apps.chat.utils import get_support_admin_random
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from apps.notification.models import Notification
from apps.notification.services import enqueue_push_to_user_id


def _is_admin(user) -> bool:
    return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


def _emit_notification_ws(notification: Notification) -> None:
    """
    Best-effort: send notification event to ws/notifications/ group.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        payload = {
            'id': notification.id,
            'user_id': notification.user_id,
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'related_object_type': notification.related_object_type,
            'related_object_id': notification.related_object_id,
            'data': notification.data,
            'created_at': notification.created_at.isoformat() if notification.created_at else None,
            'status': notification.status,
        }
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.user_id}',
            {'type': 'notification', 'notification': payload},
        )
    except Exception:
        return


class SupportRoomOpenView(AsyncAPIView):
    """
    Rider/Driver opens support chat with admin.
    If room already exists, it is reused.
    If order_id is provided and not yet linked, it is added and a system message is created.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Support chat'],
        summary='Open/reuse support room',
        request=SupportRoomOpenSerializer,
        responses={200: SupportRoomSerializer},
    )
    async def post(self, request):
        ser = SupportRoomOpenSerializer(data=request.data, context={'request': request})
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order_id = (ser.validated_data.get('order_id') or None)

        def _open():
            admin = get_support_admin_random()
            if not admin:
                raise ValueError('Support admin is not configured.')

            with transaction.atomic():
                room, created = SupportRoom.objects.select_for_update().get_or_create(
                    user=request.user,
                    admin=admin,
                )

                linked_new_order = False
                order_obj = None
                if order_id:
                    from apps.order.models import Order

                    order_obj = Order.objects.filter(pk=order_id).first()
                    if order_obj and not room.orders.filter(pk=order_obj.pk).exists():
                        room.orders.add(order_obj)
                        linked_new_order = True

                if created and order_obj:
                    SupportMessage.objects.create(
                        room=room,
                        sender=request.user,
                        message_type=SupportMessage.MessageType.SYSTEM,
                        message=f'Chat opened for order #{order_obj.id}.',
                        order=order_obj,
                    )
                elif linked_new_order and order_obj:
                    SupportMessage.objects.create(
                        room=room,
                        sender=request.user,
                        message_type=SupportMessage.MessageType.SYSTEM,
                        message=f'Chat context switched to order #{order_obj.id}.',
                        order=order_obj,
                    )

                # bump updated_at
                SupportRoom.objects.filter(pk=room.pk).update(updated_at=room.updated_at)
                return room

        try:
            room = await sync_to_async(_open)()
        except ValueError as e:
            return Response({'message': str(e), 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        out = SupportRoomSerializer(room, context={'request': request})
        data = await sync_to_async(lambda: out.data)()
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)


class SupportRoomListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Support chat'],
        summary='List support rooms',
        description='Admin: all rooms. Rider/Driver: own rooms.',
        parameters=[
            OpenApiParameter('user_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Admin only'),
        ],
    )
    async def get(self, request):
        user_id = request.query_params.get('user_id')

        def _qs():
            qs = SupportRoom.objects.select_related('user', 'admin').prefetch_related('orders').order_by(
                '-updated_at', '-created_at'
            )
            if _is_admin(request.user):
                if user_id and str(user_id).isdigit():
                    qs = qs.filter(user_id=int(user_id))
                return qs
            return qs.filter(user=request.user)

        rooms = await sync_to_async(list)(_qs())
        ser = SupportRoomSerializer(rooms, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)


class SupportRoomDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Support chat'],
        summary='Get support room by id',
        description='Admin: any room. Rider/Driver: only own room.',
        responses={200: SupportRoomSerializer},
    )
    async def get(self, request, room_id: int):
        try:
            room = await SupportRoom.objects.select_related('user', 'admin').prefetch_related('orders').aget(
                pk=room_id
            )
        except SupportRoom.DoesNotExist:
            return Response({'message': 'Room not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        if not _is_admin(request.user) and room.user_id != request.user.id:
            return Response({'message': 'Access denied', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        ser = SupportRoomSerializer(
            room,
            context={'request': request, 'include_messages': True, 'messages_limit': 500},
        )
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)


class SupportRoomMessagesView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Support chat'],
        summary='List support messages',
        parameters=[
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        ],
    )
    async def get(self, request, room_id: int):
        try:
            room = await SupportRoom.objects.select_related('user', 'admin').aget(pk=room_id)
        except SupportRoom.DoesNotExist:
            return Response({'message': 'Room not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        if not _is_admin(request.user) and room.user_id != request.user.id:
            return Response({'message': 'Access denied', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size

        qs = SupportMessage.objects.filter(room_id=room_id).select_related('sender').order_by('created_at')
        total = await sync_to_async(qs.count)()
        rows = await sync_to_async(list)(qs[start:end])
        ser = SupportMessageSerializer(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response(
            {
                'message': 'OK',
                'status': 'success',
                'data': data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total,
                    'total_pages': (total + page_size - 1) // page_size,
                },
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Support chat'],
        summary='Send support message',
        request=SupportMessageCreateSerializer,
        responses={201: SupportMessageSerializer},
    )
    async def post(self, request, room_id: int):
        try:
            room = await SupportRoom.objects.select_related('user', 'admin').aget(pk=room_id)
        except SupportRoom.DoesNotExist:
            return Response({'message': 'Room not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        is_admin = _is_admin(request.user)
        if not is_admin and room.user_id != request.user.id:
            return Response({'message': 'Access denied', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)
        if is_admin and room.admin_id != request.user.id:
            # For now, a single admin per room. Superusers can still read all rooms, but to reply
            # they should be the assigned admin user.
            return Response(
                {'message': 'Only the assigned admin can reply in this room.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = SupportMessageCreateSerializer(data=request.data, context={'request': request})
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg_text = ser.validated_data['message'].strip()
        order_id = ser.validated_data.get('order_id') or None

        def _create():
            order_obj = None
            if order_id:
                from apps.order.models import Order

                order_obj = Order.objects.filter(pk=order_id).first()
                if order_obj and not room.orders.filter(pk=order_obj.pk).exists():
                    room.orders.add(order_obj)
                    SupportMessage.objects.create(
                        room=room,
                        sender=request.user,
                        message_type=SupportMessage.MessageType.SYSTEM,
                        message=f'Chat context switched to order #{order_obj.id}.',
                        order=order_obj,
                    )

            mtype = SupportMessage.MessageType.ADMIN if is_admin else SupportMessage.MessageType.USER
            msg = SupportMessage.objects.create(
                room=room,
                sender=request.user,
                message_type=mtype,
                message=msg_text,
                order=order_obj,
            )
            SupportRoom.objects.filter(pk=room.pk).update(updated_at=room.updated_at)
            return msg

        msg = await sync_to_async(_create)()

        # Notifications: notify the other participant (admin <-> user)
        def _notify():
            recipient = room.user if is_admin else room.admin
            if not recipient:
                return
            title = 'New support message'
            body = (msg_text[:120] + '…') if len(msg_text) > 120 else msg_text
            n = Notification.objects.create(
                user=recipient,
                notification_type=Notification.NotificationType.CHAT_MESSAGE,
                title=title,
                message=body,
                related_object_type='support_room',
                related_object_id=room.id,
                data={
                    'support_room_id': room.id,
                    'order_id': msg.order_id,
                    'sender_id': request.user.id,
                },
            )
            enqueue_push_to_user_id(
                recipient.id,
                title=title,
                body=body,
                data=n.data or {},
            )
            _emit_notification_ws(n)

        await sync_to_async(_notify)()

        out = SupportMessageSerializer(msg, context={'request': request})
        data = await sync_to_async(lambda: out.data)()
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=status.HTTP_201_CREATED)

