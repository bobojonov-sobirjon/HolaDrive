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
)
from .user_preferences import (
    UserPreferencesView,
    UserPreferencesDeleteView
)
from .driver_preferences import DriverPreferencesView
from .vehicle import VehicleDetailsView, VehicleDetailView, VehicleImageView
from .driver_identification import (
    DriverIdentificationUploadView,
    DriverIdentificationUserStatusView,
    DriverIdentificationListView
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
    'UserPreferencesView',
    'UserPreferencesDeleteView',
    'DriverPreferencesView',
    'VehicleDetailsView',
    'VehicleDetailView',
    'VehicleImageView',
    'DriverIdentificationUploadView',
    'DriverIdentificationUserStatusView',
    'DriverIdentificationListView',
    'DriverVerificationDetailView',
    'DriverVerificationMeView',
    'DriverVerificationSubmitView',
    'InvitationGenerateView',
    'InvitationGetView',
    'InvitedUsersView',
    'PinVerificationForUserView',
]

