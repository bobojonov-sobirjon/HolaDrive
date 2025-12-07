from django.urls import path
from .views import (
    RegistrationView, LoginView, SendVerificationCodeView,
    VerifyCodeView, ResetPasswordRequestView, VerifyResetCodeView,
    ResetPasswordConfirmView, UserDetailView,
    UserPreferencesView, UserPreferencesDeleteView,
    DriverPreferencesView, VehicleDetailsView, VehicleDetailView, VehicleImageView,
    DriverIdentificationView, CheckIdentificationView,
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
    
    # User Preferences endpoints
    path('preferences/', UserPreferencesView.as_view(), name='user-preferences'),
    path('preferences/delete/', UserPreferencesDeleteView.as_view(), name='user-preferences-delete'),
    
    # Driver Preferences endpoints
    path('driver/preferences/', DriverPreferencesView.as_view(), name='driver-preferences'),
    
    # Vehicle Details endpoints (Driver only)
    path('vehicle/', VehicleDetailsView.as_view(), name='vehicle-details'),
    path('vehicle/<int:pk>/', VehicleDetailView.as_view(), name='vehicle-detail'),
    
    # Vehicle Image endpoints (Driver only)
    path('vehicle/image/<int:pk>/', VehicleImageView.as_view(), name='vehicle-image-detail'),
    
    # Driver Identification endpoints (Driver only)
    path('driver/identification/', DriverIdentificationView.as_view(), name='driver-identification'),
    path('driver/identification/check/', CheckIdentificationView.as_view(), name='check-identification'),
    
    # Invitation endpoints
    path('invitations/generate/', InvitationGenerateView.as_view(), name='invitation-generate'),
    path('invitations/', InvitationGetView.as_view(), name='invitation-get'),
    path('invitations/users/', InvitedUsersView.as_view(), name='invited-users'),
    
    # PIN Verification endpoints
    path('pin-verification/', PinVerificationForUserView.as_view(), name='pin-verification'),
]