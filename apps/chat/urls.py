from django.urls import path
from apps.chat.views.room import (
    ChatRoomListView,
    ChatRoomMessagesView,
)
from apps.chat.views.support import (
    SupportRoomDetailView,
    SupportRoomListView,
    SupportRoomMessagesView,
    SupportRoomOpenView,
)

urlpatterns = [
    path('rooms/', ChatRoomListView.as_view(), name='chat-rooms-list'),
    path('rooms/rider/', ChatRoomListView.as_view(), {'list_type': 'rider'}, name='chat-rooms-rider'),
    path('rooms/driver/', ChatRoomListView.as_view(), {'list_type': 'driver'}, name='chat-rooms-driver'),
    path('rooms/<int:room_id>/messages/', ChatRoomMessagesView.as_view(), name='chat-room-messages'),

    # Support chat (Rider/Driver <-> Admin)
    path('support/rooms/open/', SupportRoomOpenView.as_view(), name='support-room-open'),
    path('support/rooms/', SupportRoomListView.as_view(), name='support-rooms'),
    path('support/rooms/<int:room_id>/', SupportRoomDetailView.as_view(), name='support-room-detail'),
    path('support/rooms/<int:room_id>/messages/', SupportRoomMessagesView.as_view(), name='support-room-messages'),
]
