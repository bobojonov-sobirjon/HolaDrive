from rest_framework.response import Response
from apps.common.views import AsyncAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Prefetch
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

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

    @extend_schema(tags=['Chat'], summary='Create conversation', description='Create a new conversation. Rider/Driver only.', request=ConversationCreateSerializer)
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

    @extend_schema(
        tags=['Chat'],
        summary='List conversations',
        description='Get list of conversations. Rider/Driver: own only; Support: all. Optional query: status.',
        parameters=[OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description='Filter by conversation status')],
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

    @extend_schema(tags=['Chat'], summary='Get conversation', description='Get conversation detail by ID.')
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

    @extend_schema(tags=['Chat'], summary='Update conversation', description='Update conversation (status, subject). Support only.', request=ConversationSerializer)
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

