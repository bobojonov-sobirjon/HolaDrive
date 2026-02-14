from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.chat.models import Conversation, Message
from apps.chat.serializers import MessageSerializer, MessageCreateSerializer, MessageMarkAsReadSerializer
from apps.chat.utils import get_support_user
from apps.notification.models import Notification

class MessageListView(AsyncAPIView):
    """
    Get messages for a conversation
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Chat'],
        summary='List messages',
        description='Get messages for a conversation. Pagination: page, page_size.',
        parameters=[
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Page number'),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description='Page size'),
        ],
    )
    async def get(self, request, conversation_id):
        """
        Get messages for a conversation - ASYNC VERSION
        """
        try:
            conversation = await Conversation.objects.aget(id=conversation_id)
            
            user = request.user
            if not (user.is_staff or user.is_superuser) and conversation.user != user:
                return Response(
                    {
                        'message': 'You don\'t have access to this conversation',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            messages_queryset = Message.objects.filter(conversation=conversation).select_related('sender').order_by('created_at')
            
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 50))
            start = (page - 1) * page_size
            end = start + page_size
            
            total_count = await sync_to_async(messages_queryset.count)()
            messages = await sync_to_async(list)(messages_queryset[start:end])
            
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Messages retrieved successfully',
                    'status': 'success',
                    'data': serializer_data,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size
                    }
                },
                status=status.HTTP_200_OK
            )
        except Conversation.DoesNotExist:
            return Response(
                {
                    'message': 'Conversation not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )

class MessageCreateView(AsyncAPIView):
    """
    Create a new message
    Only Rider/Driver can create messages via API
    Support can only send messages from admin panel
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Chat'], summary='Send message', description='Create a new message in a conversation. Rider/Driver only via API.', request=MessageCreateSerializer)
    async def post(self, request, conversation_id):
        """
        Create a new message - ASYNC VERSION
        """
        try:
            conversation = await Conversation.objects.aget(id=conversation_id)
            
            user = request.user
            if not (user.is_staff or user.is_superuser) and conversation.user != user:
                return Response(
                    {
                        'message': 'You don\'t have access to this conversation',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if user.is_staff or user.is_superuser:
                return Response(
                    {
                        'message': 'Support can only send messages from admin panel. Please use admin panel to reply.',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            data = request.data.copy()
            data['conversation'] = conversation_id
            
            serializer = MessageCreateSerializer(data=data, context={'request': request})
            is_valid = await sync_to_async(lambda: serializer.is_valid())()
            
            if is_valid:
                message = await sync_to_async(serializer.save)()
                
                conversation.last_message_at = timezone.now()
                conversation.unread_count_support += 1
                await sync_to_async(conversation.save)()
                
                support_user = await sync_to_async(get_support_user)()
                await sync_to_async(Notification.objects.create)(
                    user=support_user,
                    notification_type='chat_message',
                    title=f'New message from {await sync_to_async(user.get_full_name)() or user.username}',
                    message=f'New message in conversation: {message.message[:50]}...',
                    related_object_type='conversation',
                    related_object_id=conversation.id,
                    data={'conversation_id': conversation.id, 'message_id': message.id}
                )
                
                response_serializer = MessageSerializer(message, context={'request': request})
                serializer_data = await sync_to_async(lambda: response_serializer.data)()
                return Response(
                    {
                        'message': 'Message sent successfully',
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
        except Conversation.DoesNotExist:
            return Response(
                {
                    'message': 'Conversation not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )

class MessageMarkAsReadView(AsyncAPIView):
    """
    Mark messages as read
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Chat'], summary='Mark messages read', description='Mark messages as read. Body: message_ids (list).', request=MessageMarkAsReadSerializer)
    async def post(self, request, conversation_id):
        """
        Mark messages as read - ASYNC VERSION
        """
        try:
            conversation = await Conversation.objects.aget(id=conversation_id)
            
            user = request.user
            if not (user.is_staff or user.is_superuser) and conversation.user != user:
                return Response(
                    {
                        'message': 'You don\'t have access to this conversation',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            message_ids = request.data.get('message_ids', [])
            if not message_ids:
                return Response(
                    {
                        'message': 'message_ids is required',
                        'status': 'error'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            messages_queryset = Message.objects.filter(
                id__in=message_ids,
                conversation=conversation
            )
            
            messages = await sync_to_async(list)(messages_queryset)
            
            is_support = user.is_staff or user.is_superuser
            updated_count = 0
            
            for message in messages:
                if is_support:
                    if not message.is_read_by_support:
                        message.is_read_by_support = True
                        if conversation.unread_count_support > 0:
                            conversation.unread_count_support -= 1
                        updated_count += 1
                else:
                    if not message.is_read_by_user:
                        message.is_read_by_user = True
                        if conversation.unread_count_user > 0:
                            conversation.unread_count_user -= 1
                        updated_count += 1
                await sync_to_async(message.save)()
            
            await sync_to_async(conversation.save)()
            
            return Response(
                {
                    'message': f'{updated_count} message(s) marked as read',
                    'status': 'success',
                    'updated_count': updated_count
                },
                status=status.HTTP_200_OK
            )
        except Conversation.DoesNotExist:
            return Response(
                {
                    'message': 'Conversation not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )

