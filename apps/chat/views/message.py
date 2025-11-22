from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from django.db.models import Q

from apps.chat.models import Conversation, Message
from apps.chat.serializers import MessageSerializer, MessageCreateSerializer
from apps.chat.utils import get_support_user
from apps.notification.models import Notification


class MessageListView(APIView):
    """
    Get messages for a conversation
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="Get conversation messages",
        operation_description="Get all messages for a conversation",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Number of items per page",
                type=openapi.TYPE_INTEGER
            ),
        ],
        responses={
            200: MessageSerializer(many=True),
            404: "Conversation not found"
        },
        tags=['Chat']
    )
    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            user = request.user
            if not (user.is_staff or user.is_superuser) and conversation.user != user:
                return Response(
                    {
                        'message': 'You don\'t have access to this conversation',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            messages = Message.objects.filter(conversation=conversation).select_related('sender').order_by('created_at')
            
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 50))
            start = (page - 1) * page_size
            end = start + page_size
            
            total_count = messages.count()
            messages = messages[start:end]
            
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            return Response(
                {
                    'message': 'Messages retrieved successfully',
                    'status': 'success',
                    'data': serializer.data,
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


class MessageCreateView(APIView):
    """
    Create a new message
    Only Rider/Driver can create messages via API
    Support can only send messages from admin panel
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="Send a message",
        operation_description="Send a message in a conversation. Only Rider/Driver can send messages via API. Support must use admin panel.",
        request_body=MessageCreateSerializer,
        responses={
            201: MessageSerializer,
            400: "Bad Request",
            403: "Forbidden - Support must use admin panel"
        },
        tags=['Chat']
    )
    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
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
            if serializer.is_valid():
                message = serializer.save()
                
                conversation.last_message_at = timezone.now()
                conversation.unread_count_support += 1
                conversation.save()
                
                support_user = get_support_user()
                Notification.objects.create(
                    user=support_user,
                    notification_type='chat_message',
                    title=f'New message from {user.get_full_name() or user.username}',
                    message=f'New message in conversation: {message.message[:50]}...',
                    related_object_type='conversation',
                    related_object_id=conversation.id,
                    data={'conversation_id': conversation.id, 'message_id': message.id}
                )
                
                response_serializer = MessageSerializer(message, context={'request': request})
                return Response(
                    {
                        'message': 'Message sent successfully',
                        'status': 'success',
                        'data': response_serializer.data
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
        except Conversation.DoesNotExist:
            return Response(
                {
                    'message': 'Conversation not found',
                    'status': 'error'
                },
                status=status.HTTP_404_NOT_FOUND
            )


class MessageMarkAsReadView(APIView):
    """
    Mark messages as read
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="Mark messages as read",
        operation_description="Mark one or more messages as read",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description='List of message IDs to mark as read'
                )
            },
            required=['message_ids']
        ),
        responses={
            200: "Messages marked as read",
            400: "Bad Request"
        },
        tags=['Chat']
    )
    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
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
            
            messages = Message.objects.filter(
                id__in=message_ids,
                conversation=conversation
            )
            
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
                message.save()
            
            conversation.save()
            
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

