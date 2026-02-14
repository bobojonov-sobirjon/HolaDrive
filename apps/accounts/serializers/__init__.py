from .authentication import (
    RegistrationSerializer,
    LoginSerializer,
    SendVerificationCodeSerializer,
    VerifyCodeSerializer,
    ResetPasswordRequestSerializer,
    VerifyResetCodeSerializer,
    ResetPasswordConfirmSerializer
)
from .user import UserDetailSerializer, AvatarUpdateRequestSerializer
from .user_preferences import UserPreferencesSerializer
from .driver_preferences import DriverPreferencesSerializer
from .vehicle import VehicleDetailsSerializer, VehicleImageSerializer
from .driver_identification import (
    DriverIdentificationSerializer,
    DriverIdentificationItemsSerializer,
    DriverIdentificationUploadDocumentSerializer,
    DriverIdentificationUploadRequestSerializer,
    DriverIdentificationUserStatusSerializer,
    DriverVerificationSerializer,
)
from .invitations import InvitationGenerateSerializer, InvitationUsersSerializer
from .pin_verification import PinVerificationForUserSerializer
from .legal import LegalPageSerializer

__all__ = [
    'RegistrationSerializer',
    'LoginSerializer',
    'SendVerificationCodeSerializer',
    'VerifyCodeSerializer',
    'ResetPasswordRequestSerializer',
    'VerifyResetCodeSerializer',
    'ResetPasswordConfirmSerializer',
    'UserDetailSerializer',
    'AvatarUpdateRequestSerializer',
    'UserPreferencesSerializer',
    'DriverPreferencesSerializer',
    'VehicleDetailsSerializer',
    'VehicleImageSerializer',
    'DriverIdentificationSerializer',
    'DriverIdentificationItemsSerializer',
    'DriverIdentificationUploadDocumentSerializer',
    'DriverIdentificationUploadRequestSerializer',
    'DriverIdentificationUserStatusSerializer',
    'DriverVerificationSerializer',
    'InvitationGenerateSerializer',
    'InvitationUsersSerializer',
    'PinVerificationForUserSerializer',
    'LegalPageSerializer',
]

