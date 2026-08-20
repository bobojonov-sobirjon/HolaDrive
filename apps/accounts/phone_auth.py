"""Phone OTP sign-in: get or create user (like Firebase social auth)."""
from __future__ import annotations

import logging
import re
import secrets
from typing import Optional, Tuple

from django.contrib.auth.models import Group
from django.db import transaction

from apps.accounts.models import CustomUser
from apps.accounts.services import normalize_phone_number

logger = logging.getLogger(__name__)

PHONE_EMAIL_DOMAIN = 'phone.holadrive.app'

ROLE_GROUP_NAMES = {
    'rider': 'Rider',
    'driver': 'Driver',
}

WRONG_APP_ROLE_CODE = 'wrong_app_role'
MIXED_APP_ROLES_CODE = 'mixed_app_roles'


class AppRoleMismatchError(ValueError):
    """Existing account belongs to the other app (Rider vs Driver)."""

    def __init__(self, account_role: str, requested_role: str, *, code: str = WRONG_APP_ROLE_CODE):
        self.account_role = account_role
        self.requested_role = requested_role
        self.code = code
        if code == MIXED_APP_ROLES_CODE:
            msg = (
                'This account has both Rider and Driver roles. Contact support to fix the account.'
            )
        else:
            app_name = (account_role or 'the correct').title()
            msg = (
                f'This account is registered as a {app_name}. '
                f'Please sign in with the {app_name} app.'
            )
        super().__init__(msg)

    def as_api_payload(self) -> dict:
        return {
            'message': str(self),
            'status': 'error',
            'code': self.code,
            'errors': {'role': [str(self)]},
            'data': {
                'account_role': self.account_role,
                'requested_role': self.requested_role,
            },
        }


def _unique_username(base: str) -> str:
    base = re.sub(r'[^a-zA-Z0-9_@.+-]', '', base)[:120] or 'user'
    username = base
    counter = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1
    return username


def _placeholder_email(normalized_phone: str) -> str:
    digits = re.sub(r'\D', '', normalized_phone) or secrets.token_hex(6)
    email = f'{digits}@{PHONE_EMAIL_DOMAIN}'
    while CustomUser.objects.filter(email__iexact=email).exists():
        email = f'{digits}{secrets.token_hex(2)}@{PHONE_EMAIL_DOMAIN}'
    return email


def find_user_by_phone(phone_number: str) -> CustomUser | None:
    normalized = normalize_phone_number(phone_number)
    if not normalized:
        return None
    raw = str(phone_number).strip()
    qs = CustomUser.objects.filter(phone_number__in=[normalized, raw])
    return qs.first()


def is_phone_signup_user(user: CustomUser) -> bool:
    email = (user.email or '').strip().lower()
    return email.endswith(f'@{PHONE_EMAIL_DOMAIN}')


def _assign_role_group(user: CustomUser, role: Optional[str]) -> None:
    if not role:
        return
    group_name = ROLE_GROUP_NAMES.get((role or '').strip().lower())
    if not group_name:
        return
    group = Group.objects.filter(name=group_name).first()
    if group and not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)


def user_has_app_role(user: CustomUser) -> bool:
    return user.groups.filter(name__in=ROLE_GROUP_NAMES.values()).exists()


def ensure_user_app_role(user: CustomUser, role: Optional[str], *, only_if_missing: bool = True) -> None:
    """Assign Rider/Driver group; by default only when user has no app role yet."""
    if not role:
        return
    if only_if_missing and user_has_app_role(user):
        return
    _assign_role_group(user, role)


def user_app_roles(user: CustomUser) -> list[str]:
    return list(user.groups.filter(name__in=ROLE_GROUP_NAMES.values()).values_list('name', flat=True))


def normalize_app_role(role: Optional[str]) -> Optional[str]:
    value = (role or '').strip().lower()
    return value if value in ROLE_GROUP_NAMES else None


def user_exclusive_app_role(user: CustomUser, *, requested_role: Optional[str] = None) -> Optional[str]:
    """
    Return 'rider' or 'driver' when the user has exactly one app group.
    None if unassigned. Raises AppRoleMismatchError if both groups are set.
    """
    names = set(user_app_roles(user))
    if not names:
        return None
    if names == {'Rider', 'Driver'}:
        raise AppRoleMismatchError('both', requested_role or '', code=MIXED_APP_ROLES_CODE)
    if 'Driver' in names:
        return 'driver'
    if 'Rider' in names:
        return 'rider'
    return None


def assert_login_app_role(user: CustomUser, role: Optional[str], *, assign_if_missing: bool = True) -> str:
    """
    Rider app may only sign in Rider accounts; Driver app may only sign in Driver accounts.
    Assigns the role when the account has none yet (first sign-in).
    """
    requested = normalize_app_role(role)
    if not requested:
        raise ValueError('role is required (rider or driver).')

    current = user_exclusive_app_role(user, requested_role=requested)
    if current is None:
        if assign_if_missing:
            _assign_role_group(user, requested)
        return requested
    if current != requested:
        raise AppRoleMismatchError(current, requested)
    return current


def _ensure_stripe_customer(user: CustomUser) -> None:
    try:
        from django.conf import settings

        if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
            return
        from apps.payment.services.stripe_cards import get_or_create_stripe_customer_id

        cid = get_or_create_stripe_customer_id(user)
        if cid and not (user.stripe_customer_id or '').strip():
            user.stripe_customer_id = cid
            user.save(update_fields=['stripe_customer_id'])
    except Exception as exc:
        logger.warning('Stripe customer init skipped after phone sign-up: %s', exc)


@transaction.atomic
def get_or_create_user_for_phone(
    phone_number: str,
    *,
    role: Optional[str] = None,
) -> Tuple[CustomUser, bool]:
    """
    Return (user, is_new_user). Creates a minimal account for new phone numbers.
    """
    normalized = normalize_phone_number(phone_number)
    if not normalized:
        raise ValueError('Invalid phone number.')

    existing = find_user_by_phone(normalized)
    if existing and not existing.is_active:
        existing.delete()
        existing = None
    if existing:
        if existing.phone_number != normalized:
            existing.phone_number = normalized
            existing.save(update_fields=['phone_number'])
        assert_login_app_role(existing, role, assign_if_missing=True)
        return existing, False

    email = _placeholder_email(normalized)
    phone_digits = re.sub(r'\D', '', normalized)
    username = _unique_username(f'phone_{phone_digits}')

    user = CustomUser(
        username=username,
        email=email,
        phone_number=normalized,
        is_verified=False,
    )
    user.set_unusable_password()
    user.save()

    if not role:
        raise ValueError('role is required for new phone sign-up (rider or driver).')

    _assign_role_group(user, role)
    _ensure_stripe_customer(user)

    return user, True
