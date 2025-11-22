from django.urls import path
from apps.chat.views import (
    ConversationCreateView,
    ConversationListView,
    ConversationDetailView,
    ConversationUpdateView,
    MessageListView,
    MessageCreateView,
    MessageMarkAsReadView
)

urlpatterns = [
    path('conversations/', ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/list/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/update/', ConversationUpdateView.as_view(), name='conversation-update'),
    
    path('conversations/<int:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<int:conversation_id>/messages/send/', MessageCreateView.as_view(), name='message-create'),
    path('conversations/<int:conversation_id>/messages/mark-read/', MessageMarkAsReadView.as_view(), name='message-mark-read'),
]
