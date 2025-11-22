from django.urls import path
from .views import (
    RegistrationView, LoginView, SendVerificationCodeView,
    VerifyCodeView, ResetPasswordRequestView, VerifyResetCodeView,
    ResetPasswordConfirmView, UserDetailView, CustomUserListView,
    CustomUserDetailByIdView, UserPreferencesView, UserPreferencesDeleteView,
    InvitationGenerateView, InvitationGetView, InvitedUsersView,
    PinVerificationForUserView
)

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('send-verification-code/', SendVerificationCodeView.as_view(), name='send-verification-code'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('reset-password/', ResetPasswordRequestView.as_view(), name='reset-password'),
    path('verify-reset-code/', VerifyResetCodeView.as_view(), name='verify-reset-code'),
    path('reset-password-confirm/', ResetPasswordConfirmView.as_view(), name='reset-password-confirm'),
    
    # User endpoints
    path('me/', UserDetailView.as_view(), name='user-detail'),
    path('users/', CustomUserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', CustomUserDetailByIdView.as_view(), name='user-detail-by-id'),
    
    # User Preferences endpoints
    path('preferences/', UserPreferencesView.as_view(), name='user-preferences'),
    path('preferences/delete/', UserPreferencesDeleteView.as_view(), name='user-preferences-delete'),
    
    # Invitation endpoints
    path('invitations/generate/', InvitationGenerateView.as_view(), name='invitation-generate'),
    path('invitations/', InvitationGetView.as_view(), name='invitation-get'),
    path('invitations/users/', InvitedUsersView.as_view(), name='invited-users'),
    
    # PIN Verification endpoints
    path('pin-verification/', PinVerificationForUserView.as_view(), name='pin-verification'),
]