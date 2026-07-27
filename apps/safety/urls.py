from django.urls import path

from .views import (
    SafetyRoomDetailView,
    SafetyRoomListView,
    SafetyRoomMessagesView,
    SafetyRoomOpenView,
    SafetyToolsConfigView,
    TripShareCreateView,
    TripShareListView,
    TripSharePublicView,
    TripShareRevokeView,
    VoiceRecordingDetailView,
    VoiceRecordingListView,
    VoiceRecordingStartView,
    VoiceRecordingStopView,
)

app_name = 'safety'

urlpatterns = [
    path('tools/', SafetyToolsConfigView.as_view(), name='tools-config'),
    # Share trip status
    path('share/', TripShareCreateView.as_view(), name='share-create'),
    path('share/list/', TripShareListView.as_view(), name='share-list'),
    path('share/<str:token>/', TripSharePublicView.as_view(), name='share-public'),
    path('share/<str:token>/revoke/', TripShareRevokeView.as_view(), name='share-revoke'),
    # Safety agent chat
    path('rooms/open/', SafetyRoomOpenView.as_view(), name='rooms-open'),
    path('rooms/', SafetyRoomListView.as_view(), name='rooms-list'),
    path('rooms/<int:room_id>/', SafetyRoomDetailView.as_view(), name='rooms-detail'),
    path('rooms/<int:room_id>/messages/', SafetyRoomMessagesView.as_view(), name='rooms-messages'),
    # Voice recording
    path('recordings/start/', VoiceRecordingStartView.as_view(), name='recordings-start'),
    path('recordings/', VoiceRecordingListView.as_view(), name='recordings-list'),
    path('recordings/<int:recording_id>/', VoiceRecordingDetailView.as_view(), name='recordings-detail'),
    path('recordings/<int:recording_id>/stop/', VoiceRecordingStopView.as_view(), name='recordings-stop'),
]
