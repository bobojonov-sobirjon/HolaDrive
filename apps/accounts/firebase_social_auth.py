"""Firebase social sign-in: resolve or create CustomUser from verified ID token claims."""
from __future__ import annotations

import logging
import re
import secrets
from typing import Any, Optional, Tuple

from django.contrib.auth.models import Group
from django.db import transaction

from apps.accounts.models import CustomUser, UserDeviceToken

logger = logging.getLogger(__name__)

PROVIDER_CLAIMS = {
    'google': frozenset({'google.com'}),
    'apple': frozenset({'apple.com'}),
    'facebook': frozenset({'facebook.com'}),
}

ROLE_GROUP_NAMES = {
    'rider': 'Rider',
    'driver': 'Driver',
}


class SocialAuthError(Exception):
    def __init__(self, message: str, *, code: str = 'social_auth_error'):
        self.code = code
        super().__init__(message)


def _sign_in_provider(claims: dict[str, Any]) -> str:
    firebase_meta = claims.get('firebase') or {}
    if isinstance(firebase_meta, dict):
        provider = firebase_meta.get('sign_in_provider') or ''
        if provider:
            return str(provider)
    return str(claims.get('sign_in_provider') or '')


def _assert_provider(claims: dict[str, Any], expected: str) -> None:
    provider = _sign_in_provider(claims)
    allowed = PROVIDER_CLAIMS.get(expected)
    if not allowed or provider not in allowed:
        raise SocialAuthError(
            f'This endpoint is for {expected.title()} sign-in only. '
            f'Token was issued for provider "{provider or "unknown"}".',
            code='wrong_provider',
        )


def _unique_username(base: str) -> str:
    base = re.sub(r'[^a-zA-Z0-9_@.+-]', '', base)[:120] or 'user'
    username = base
    counter = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1
    return username


def _placeholder_email(firebase_uid: str) -> str:
    safe = re.sub(r'[^a-zA-Z0-9]', '', firebase_uid)[:40] or secrets.token_hex(8)
    return f'{safe}@social.holadrive.app'


def _split_name(full_name: str) -> Tuple[str, str]:
    parts = (full_name or '').strip().split(None, 1)
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]


def _assign_role_group(user: CustomUser, role: Optional[str]) -> None:
    if not role:
        return
    group_name = ROLE_GROUP_NAMES.get((role or '').strip().lower())
    if not group_name:
        return
    group = Group.objects.filter(name=group_name).first()
    if group and not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)


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
        logger.warning('Stripe customer init skipped after social sign-in: %s', exc)


@transaction.atomic
def get_or_create_user_from_firebase(
    claims: dict[str, Any],
    *,
    expected_provider: str,
    role: Optional[str] = None,
    device_token: str = '',
    device_type: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Tuple[CustomUser, bool]:
    _assert_provider(claims, expected_provider)

    firebase_uid = str(claims.get('uid') or '').strip()
    if not firebase_uid:
        raise SocialAuthError('Firebase token is missing uid.', code='invalid_token')

    email = (claims.get('email') or '').strip().lower() or None
    email_verified = bool(claims.get('email_verified', False))
    display_name = (full_name or claims.get('name') or '').strip()

    user = CustomUser.objects.select_for_update().filter(firebase_uid=firebase_uid).first()
    if user:
        if display_name and not user.get_full_name().strip():
            first, last = _split_name(display_name)
            user.first_name = first or user.first_name
            user.last_name = last or user.last_name
            user.save(update_fields=['first_name', 'last_name'])
        if device_token and device_type:
            UserDeviceToken.upsert_token(user=user, token=device_token, mobile=device_type)
        return user, False

    if email:
        existing = CustomUser.objects.select_for_update().filter(email__iexact=email).first()
        if existing:
            if existing.firebase_uid and existing.firebase_uid != firebase_uid:
                raise SocialAuthError(
                    'This email is linked to another account. Use email login or contact support.',
                    code='email_linked_other_firebase',
                )
            existing.firebase_uid = firebase_uid
            if email_verified:
                existing.is_verified = True
            if display_name and not existing.get_full_name().strip():
                first, last = _split_name(display_name)
                existing.first_name = first or existing.first_name
                existing.last_name = last or existing.last_name
            existing.save(update_fields=['firebase_uid', 'is_verified', 'first_name', 'last_name'])
            if device_token and device_type:
                UserDeviceToken.upsert_token(user=existing, token=device_token, mobile=device_type)
            return existing, False

    if not email:
        email = _placeholder_email(firebase_uid)
        while CustomUser.objects.filter(email__iexact=email).exists():
            email = _placeholder_email(firebase_uid + secrets.token_hex(4))

    first_name, last_name = _split_name(display_name)
    username = _unique_username(email.split('@')[0])

    user = CustomUser(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        firebase_uid=firebase_uid,
        is_verified=True,
    )
    user.set_unusable_password()
    user.save()

    _assign_role_group(user, role)
    _ensure_stripe_customer(user)

    if device_token and device_type:
        UserDeviceToken.upsert_token(user=user, token=device_token, mobile=device_type)

    return user, True
