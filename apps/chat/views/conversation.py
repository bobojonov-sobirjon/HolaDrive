from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from django.db.models import Q, Prefetch
from asgiref.sync import sync_to_async

from apps.chat.models import Conversation, Message
from apps.chat.serializers import (
    ConversationCreateSerializer,
    ConversationListSerializer,
    ConversationSerializer
)


class ConversationCreateView(AsyncAPIView):
    """
    Create a new conversation
    Only Rider/Driver can create conversations
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="Create a new conversation",
        operation_description="Create a new conversation with support. Only Rider/Driver can create conversations.",
        request_body=ConversationCreateSerializer,
        responses={
            201: ConversationSerializer,
            400: "Bad Request"
        },
        tags=['Chat']
    )
    async def post(self, request):
        """
        Create a new conversation - ASYNC VERSION
        """
        serializer = ConversationCreateSerializer(data=request.data, context={'request': request})
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        
        if is_valid:
            conversation = await sync_to_async(serializer.save)()
            response_serializer = ConversationSerializer(conversation, context={'request': request})
            serializer_data = await sync_to_async(lambda: response_serializer.data)()
            return Response(
                {
                    'message': 'Conversation created successfully',
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


class ConversationListView(AsyncAPIView):
    """
    Get list of conversations
    - Rider/Driver: sees only their conversations
    - Support: sees all conversations
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="Get conversation list",
        operation_description="Get list of conversations. Rider/Driver see only their conversations. Support sees all conversations.",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by status (open, closed, pending)",
                type=openapi.TYPE_STRING,
                enum=['open', 'closed', 'pending']
            ),
        ],
        responses={
            200: ConversationListSerializer(many=True)
        },
        tags=['Chat']
    )
    async def get(self, request):
        """
        Get list of conversations - ASYNC VERSION
        """
        user = request.user
        status_filter = request.query_params.get('status', None)
        
        if user.is_staff or user.is_superuser:
            conversations_queryset = Conversation.objects.select_related('user').prefetch_related(
                Prefetch(
                    'messages',
                    queryset=Message.objects.select_related('sender').order_by('-created_at')
                )
            ).all()
        else:
            conversations_queryset = Conversation.objects.select_related('user').prefetch_related(
                Prefetch(
                    'messages',
                    queryset=Message.objects.select_related('sender').order_by('-created_at')
                )
            ).filter(user=user)
        
        if status_filter:
            conversations_queryset = conversations_queryset.filter(status=status_filter)
        
        conversations_queryset = conversations_queryset.order_by('-last_message_at', '-created_at')
        
        # Convert queryset to list (async)
        conversations = await sync_to_async(list)(conversations_queryset)
        
        serializer = ConversationListSerializer(conversations, many=True, context={'request': request})
        serializer_data = await sync_to_async(lambda: serializer.data)()
        return Response(
            {
                'message': 'Conversations retrieved successfully',
                'status': 'success',
                'data': serializer_data
            },
            status=status.HTTP_200_OK
        )


class ConversationDetailView(AsyncAPIView):
    """
    Get conversation detail
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="Get conversation detail",
        operation_description="Get detailed information about a conversation",
        responses={
            200: ConversationSerializer,
            404: "Conversation not found"
        },
        tags=['Chat']
    )
    async def get(self, request, conversation_id):
        """
        Get conversation detail - ASYNC VERSION
        """
        try:
            conversation = await Conversation.objects.select_related('user').aget(id=conversation_id)
            
            user = request.user
            if not (user.is_staff or user.is_superuser) and conversation.user != user:
                return Response(
                    {
                        'message': 'You don\'t have access to this conversation',
                        'status': 'error'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ConversationSerializer(conversation, context={'request': request})
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Conversation retrieved successfully',
                    'status': 'success',
                    'data': serializer_data
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


class ConversationUpdateView(AsyncAPIView):
    """
    Update conversation (status, etc.)
    Only Support can update conversations
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="Update conversation",
        operation_description="Update conversation status. Only Support can update conversations.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['open', 'closed', 'pending'],
                    description='New conversation status'
                ),
                'subject': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Conversation subject'
                )
            }
        ),
        responses={
            200: ConversationSerializer,
            403: "Forbidden - Only Support can update conversations",
            404: "Conversation not found"
        },
        tags=['Chat']
    )
    async def patch(self, request, conversation_id):
        """
        Update conversation - ASYNC VERSION
        """
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {
                    'message': 'Only Support can update conversations',
                    'status': 'error'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            conversation = await Conversation.objects.aget(id=conversation_id)
            
            if 'status' in request.data:
                conversation.status = request.data['status']
            
            if 'subject' in request.data:
                conversation.subject = request.data['subject']
            
            await sync_to_async(conversation.save)()
            
            serializer = ConversationSerializer(conversation, context={'request': request})
            serializer_data = await sync_to_async(lambda: serializer.data)()
            return Response(
                {
                    'message': 'Conversation updated successfully',
                    'status': 'success',
                    'data': serializer_data
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

