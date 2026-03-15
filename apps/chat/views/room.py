from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.chat.models import ChatRoom, ChatMessage
from apps.chat.serializers.room import ChatRoomSerializer, ChatMessageSerializer


class ChatRoomListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Chat'],
        summary='List chat rooms',
        description='GET by order_id (query param), or /rider/ (my rooms as initiator), or /driver/ (my rooms as receiver). No POST – room is created when order is created.',
        parameters=[
            OpenApiParameter('order_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Filter by order ID'),
        ],
    )
    async def get(self, request, list_type=None):
        list_type = list_type or self.kwargs.get('list_type')
        user = request.user
        order_id = request.query_params.get('order_id')

        if order_id:
            qs = ChatRoom.objects.filter(order_id=int(order_id)).select_related('order', 'initiator', 'receiver')
        elif list_type == 'rider':
            qs = ChatRoom.objects.filter(initiator=user).select_related('order', 'initiator', 'receiver')
        elif list_type == 'driver':
            qs = ChatRoom.objects.filter(receiver=user).select_related('order', 'initiator', 'receiver')
        else:
            qs = ChatRoom.objects.none()

        qs = qs.order_by('-updated_at', '-created_at')
        rooms = await sync_to_async(list)(qs)
        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)


class ChatRoomMessagesView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Chat'], summary='Get room messages', description='GET messages by room_id. User must be initiator or receiver.')
    async def get(self, request, room_id):
        try:
            room = await ChatRoom.objects.select_related('initiator', 'receiver').aget(id=room_id)
        except ChatRoom.DoesNotExist:
            return Response({'message': 'Room not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if room.initiator_id != user.id and (not room.receiver_id or room.receiver_id != user.id):
            return Response({'message': 'Access denied', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        messages = await sync_to_async(list)(
            ChatMessage.objects.filter(room=room).select_related('sender').order_by('-id')
        )
        serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
        data = await sync_to_async(lambda: serializer.data)()
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)
