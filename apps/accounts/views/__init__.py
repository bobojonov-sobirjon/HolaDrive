from .authentication import (
    RegistrationView,
    LoginView,
    AdminLoginView,
    TokenRefreshView,
    SendVerificationCodeView,
    VerifyCodeView,
    ResetPasswordRequestView,
    VerifyResetCodeView,
    ResetPasswordConfirmView
)
from .user import (
    UserDetailView,
    UserAvatarUpdateView,
)
from .user_preferences import (
    UserPreferencesView,
    UserPreferencesDeleteView
)
from .driver_preferences import DriverPreferencesView
from .vehicle import VehicleDetailsView, VehicleDetailView, VehicleImageView
from .driver_verification import (
    DriverVerificationCompletedIdentificationDetailView,
    DriverVerificationCompletedIdentificationView,
)
from .invitations import (
    InvitationGenerateView,
    InvitationGetView,
    InvitedUsersView
)
from .pin_verification import PinVerificationForUserView
from .registration_terms import (
    RegistrationTermsListView,
    RegistrationTermsAcceptView,
    RegistrationTermsDeclineView,
)
from .driver_identification import (
    DriverIdentificationChecklistView,
    DriverIdentificationLegalAcceptView,
    DriverIdentificationLegalDeclineView,
    DriverIdentificationLegalTypeDetailView,
    DriverIdentificationTermsAcceptView,
    DriverIdentificationTermsDeclineView,
    DriverIdentificationTermsTypeDetailView,
    DriverIdentificationUploadSubmitView,
    DriverIdentificationUploadTypeDetailView,
)

__all__ = [
    'RegistrationView',
    'LoginView',
    'AdminLoginView',
    'TokenRefreshView',
    'SendVerificationCodeView',
    'VerifyCodeView',
    'ResetPasswordRequestView',
    'VerifyResetCodeView',
    'ResetPasswordConfirmView',
    'UserDetailView',
    'UserAvatarUpdateView',
    'UserPreferencesView',
    'UserPreferencesDeleteView',
    'DriverPreferencesView',
    'VehicleDetailsView',
    'VehicleDetailView',
    'VehicleImageView',
    'DriverVerificationCompletedIdentificationView',
    'DriverVerificationCompletedIdentificationDetailView',
    'InvitationGenerateView',
    'InvitationGetView',
    'InvitedUsersView',
    'PinVerificationForUserView',
    'RegistrationTermsListView',
    'RegistrationTermsAcceptView',
    'RegistrationTermsDeclineView',
    'DriverIdentificationChecklistView',
    'DriverIdentificationUploadTypeDetailView',
    'DriverIdentificationLegalTypeDetailView',
    'DriverIdentificationTermsTypeDetailView',
    'DriverIdentificationUploadSubmitView',
    'DriverIdentificationLegalAcceptView',
    'DriverIdentificationLegalDeclineView',
    'DriverIdentificationTermsAcceptView',
    'DriverIdentificationTermsDeclineView',
]
