from django.urls import path
from .views import (
    RegistrationView, LoginView, TokenRefreshView, SendVerificationCodeView,
    VerifyCodeView, ResetPasswordRequestView, VerifyResetCodeView,
    ResetPasswordConfirmView, UserDetailView, UserAvatarUpdateView,
    UserPreferencesView, UserPreferencesDeleteView,
    DriverPreferencesView, VehicleDetailsView, VehicleDetailView, VehicleImageView,
    DriverVerificationCompletedIdentificationDetailView,
    DriverVerificationCompletedIdentificationView,
    InvitationGenerateView, InvitationGetView, InvitedUsersView,
    PinVerificationForUserView,
    RegistrationTermsListView,
    RegistrationTermsAcceptView,
    RegistrationTermsDeclineView,
    DriverIdentificationChecklistView,
    DriverIdentificationUploadTypeDetailView,
    DriverIdentificationLegalTypeDetailView,
    DriverIdentificationTermsTypeDetailView,
    DriverIdentificationUploadSubmitView,
    DriverIdentificationLegalAcceptView,
    DriverIdentificationLegalDeclineView,
    DriverIdentificationTermsAcceptView,
    DriverIdentificationTermsDeclineView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('send-verification-code/', SendVerificationCodeView.as_view(), name='send-verification-code'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('reset-password/', ResetPasswordRequestView.as_view(), name='reset-password'),
    path('verify-reset-code/', VerifyResetCodeView.as_view(), name='verify-reset-code'),
    path('reset-password-confirm/', ResetPasswordConfirmView.as_view(), name='reset-password-confirm'),

    path('me/', UserDetailView.as_view(), name='user-detail'),
    path('me/avatar/', UserAvatarUpdateView.as_view(), name='user-avatar-update'),

    path('preferences/', UserPreferencesView.as_view(), name='user-preferences'),
    path('preferences/delete/', UserPreferencesDeleteView.as_view(), name='user-preferences-delete'),

    path('driver/preferences/', DriverPreferencesView.as_view(), name='driver-preferences'),

    path('vehicle/', VehicleDetailsView.as_view(), name='vehicle-details'),
    path('vehicle/<int:pk>/', VehicleDetailView.as_view(), name='vehicle-detail'),

    path('vehicle/image/<int:pk>/', VehicleImageView.as_view(), name='vehicle-image-detail'),

    path(
        'driver/identification/completed/<int:pk>/',
        DriverVerificationCompletedIdentificationDetailView.as_view(),
        name='driver-identification-completed-detail',
    ),
    path(
        'driver/identification/completed/',
        DriverVerificationCompletedIdentificationView.as_view(),
        name='driver-identification-completed',
    ),

    path('driver/registration-terms/', RegistrationTermsListView.as_view(), name='registration-terms-list'),
    path('driver/registration-terms/accept/', RegistrationTermsAcceptView.as_view(), name='registration-terms-accept'),
    path('driver/registration-terms/decline/', RegistrationTermsDeclineView.as_view(), name='registration-terms-decline'),

    path('driver/identification/checklist/', DriverIdentificationChecklistView.as_view(), name='driver-identification-checklist'),
    path(
        'driver/identification/upload-types/<int:pk>/',
        DriverIdentificationUploadTypeDetailView.as_view(),
        name='driver-identification-upload-type-detail',
    ),
    path(
        'driver/identification/legal-types/<int:pk>/',
        DriverIdentificationLegalTypeDetailView.as_view(),
        name='driver-identification-legal-type-detail',
    ),
    path(
        'driver/identification/terms-types/<int:pk>/',
        DriverIdentificationTermsTypeDetailView.as_view(),
        name='driver-identification-terms-type-detail',
    ),
    path(
        'driver/identification/upload-types/submit/',
        DriverIdentificationUploadSubmitView.as_view(),
        name='driver-identification-upload-submit',
    ),
    path(
        'driver/identification/legal-types/accept/',
        DriverIdentificationLegalAcceptView.as_view(),
        name='driver-identification-legal-accept',
    ),
    path(
        'driver/identification/legal-types/decline/',
        DriverIdentificationLegalDeclineView.as_view(),
        name='driver-identification-legal-decline',
    ),
    path(
        'driver/identification/terms-types/accept/',
        DriverIdentificationTermsAcceptView.as_view(),
        name='driver-identification-terms-accept',
    ),
    path(
        'driver/identification/terms-types/decline/',
        DriverIdentificationTermsDeclineView.as_view(),
        name='driver-identification-terms-decline',
    ),

    path('invitations/generate/', InvitationGenerateView.as_view(), name='invitation-generate'),
    path('invitations/', InvitationGetView.as_view(), name='invitation-get'),
    path('invitations/users/', InvitedUsersView.as_view(), name='invited-users'),

    path('pin-verification/', PinVerificationForUserView.as_view(), name='pin-verification'),
]
