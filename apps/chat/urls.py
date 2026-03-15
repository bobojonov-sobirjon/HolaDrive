from django.urls import path
from apps.chat.views.room import (
    ChatRoomListView,
    ChatRoomMessagesView,
)

urlpatterns = [
    path('rooms/', ChatRoomListView.as_view(), name='chat-rooms-list'),
    path('rooms/rider/', ChatRoomListView.as_view(), {'list_type': 'rider'}, name='chat-rooms-rider'),
    path('rooms/driver/', ChatRoomListView.as_view(), {'list_type': 'driver'}, name='chat-rooms-driver'),
    path('rooms/<int:room_id>/messages/', ChatRoomMessagesView.as_view(), name='chat-room-messages'),
]
