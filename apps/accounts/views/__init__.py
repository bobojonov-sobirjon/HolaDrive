from .authentication import (
    RegistrationView,
    LoginView,
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
from .legal import LegalPageListView
from .user_preferences import (
    UserPreferencesView,
    UserPreferencesDeleteView
)
from .driver_preferences import DriverPreferencesView
from .vehicle import VehicleDetailsView, VehicleDetailView, VehicleImageView
from .driver_identification import (
    DriverIdentificationUploadView,
    DriverIdentificationUserStatusView,
    DriverIdentificationListView,
    DriverAgreementListView,
)
from .driver_verification import (
    DriverVerificationDetailView,
    DriverVerificationMeView,
    DriverVerificationSubmitView,
)
from .invitations import (
    InvitationGenerateView,
    InvitationGetView,
    InvitedUsersView
)
from .pin_verification import PinVerificationForUserView

__all__ = [
    'RegistrationView',
    'LoginView',
    'SendVerificationCodeView',
    'VerifyCodeView',
    'ResetPasswordRequestView',
    'VerifyResetCodeView',
    'ResetPasswordConfirmView',
    'UserDetailView',
    'UserAvatarUpdateView',
    'LegalPageListView',
    'UserPreferencesView',
    'UserPreferencesDeleteView',
    'DriverPreferencesView',
    'VehicleDetailsView',
    'VehicleDetailView',
    'VehicleImageView',
    'DriverIdentificationUploadView',
    'DriverIdentificationUserStatusView',
    'DriverIdentificationListView',
    'DriverAgreementListView',
    'DriverVerificationDetailView',
    'DriverVerificationMeView',
    'DriverVerificationSubmitView',
    'InvitationGenerateView',
    'InvitationGetView',
    'InvitedUsersView',
    'PinVerificationForUserView',
]

