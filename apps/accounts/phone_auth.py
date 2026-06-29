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


def _unique_username(base: str) -> str:
    base = re.sub(r'[^a-zA-Z0-9_@.+-]', '', base)[:120] or 'user'
    username = base
    counter = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1
    return username


def _placeholder_email(normalized_phone: str) -> str:
    digits = re.sub(r'\D', '', normalized) or secrets.token_hex(6)
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
    if existing:
        if existing.phone_number != normalized:
            existing.phone_number = normalized
            existing.save(update_fields=['phone_number'])
        return existing, False

    email = _placeholder_email(normalized)
    username = _unique_username(f'phone_{re.sub(r"\D", "", normalized)}')

    user = CustomUser(
        username=username,
        email=email,
        phone_number=normalized,
        is_verified=False,
    )
    user.set_unusable_password()
    user.save()

    _assign_role_group(user, role)
    _ensure_stripe_customer(user)

    return user, True
