from django.urls import path

from .views import (
    CallAcceptView,
    CallCancelView,
    CallDetailView,
    CallEndView,
    CallHistoryView,
    CallRejectView,
    SupportCallInitiateView,
    SupportDutyView,
    TripCallInitiateView,
)

app_name = 'voice_call'

urlpatterns = [
    path('trip/initiate/', TripCallInitiateView.as_view(), name='trip-initiate'),
    path('support/initiate/', SupportCallInitiateView.as_view(), name='support-initiate'),
    path('history/', CallHistoryView.as_view(), name='history'),
    path('support-duty/', SupportDutyView.as_view(), name='support-duty'),
    path('<int:call_id>/', CallDetailView.as_view(), name='detail'),
    path('<int:call_id>/accept/', CallAcceptView.as_view(), name='accept'),
    path('<int:call_id>/reject/', CallRejectView.as_view(), name='reject'),
    path('<int:call_id>/cancel/', CallCancelView.as_view(), name='cancel'),
    path('<int:call_id>/end/', CallEndView.as_view(), name='end'),
]
