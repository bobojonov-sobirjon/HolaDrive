"""Complete Stripe Connect Custom account (identity, TOS) — AutoHandy-style."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

import stripe
from django.conf import settings

from apps.accounts.services import normalize_phone_number

from .stripe_connect_common import configure_stripe, is_stripe_live_mode, retrieve_connect_account

# Swagger / placeholder values sometimes saved on user.phone_number
_INVALID_PHONE_LITERALS = frozenset(
    {'string', 'null', 'none', 'undefined', 'phone', 'test', 'n/a', 'na', 'example'}
)


def _normalize_ssn(raw: str | None) -> str:
    return (raw or '').strip().replace('-', '')


def _stripe_individual_phone(raw: str | None) -> str | None:
    """Return E.164 phone for Stripe, or None if missing/invalid (do not send bad values)."""
    phone = (raw or '').strip()
    if not phone or phone.lower() in _INVALID_PHONE_LITERALS:
        return None

    digits = re.sub(r'\D', '', phone)
    if len(digits) < 10:
        return None

    normalized = normalize_phone_number(phone)
    if not normalized or not re.fullmatch(r'\+\d{10,15}', normalized):
        return None
    return normalized[:20]


def validate_live_identity_fields(
    *,
    dob_year: int | None,
    dob_month: int | None,
    dob_day: int | None,
    ssn_last4: str | None,
) -> None:
    """Live mode: DOB + full 9-digit SSN required (field name ssn_last4 for API compatibility)."""
    if not is_stripe_live_mode():
        return

    if dob_year is None or dob_month is None or dob_day is None:
        raise ValueError('Date of birth (dob_year, dob_month, dob_day) is required in live mode.')

    ssn = _normalize_ssn(ssn_last4)
    if not ssn:
        raise ValueError('US SSN is required in live mode.')
    if len(ssn) != 9 or not ssn.isdigit():
        raise ValueError(
            'US SSN must be 9 digits in live mode (send in field ssn_last4; not stored in our database).'
        )
    if ssn.endswith('0000') or ssn == '000000000':
        raise ValueError('Invalid SSN. Test values like 0000 are not allowed in live mode.')


def _apply_ssn_to_individual(individual: dict[str, Any], ssn_last4: str | None) -> None:
    ssn = _normalize_ssn(ssn_last4)
    if is_stripe_live_mode():
        if ssn:
            individual['id_number'] = ssn
        return

    # Test mode: server-side defaults when omitted (Stripe test Connect).
    if not ssn:
        individual['ssn_last_4'] = '0000'
        return

    if len(ssn) == 9 and ssn.isdigit():
        individual['id_number'] = ssn
    elif len(ssn) == 4 and ssn.isdigit():
        individual['ssn_last_4'] = ssn


def _resolve_dob(
    *,
    dob_year: int | None,
    dob_month: int | None,
    dob_day: int | None,
) -> tuple[int, int, int]:
    if is_stripe_live_mode():
        if dob_year is None or dob_month is None or dob_day is None:
            raise ValueError('Date of birth (dob_year, dob_month, dob_day) is required in live mode.')
        return dob_year, dob_month, dob_day

    today = date.today()
    return (
        dob_year or today.year - 25,
        dob_month or 1,
        dob_day or 1,
    )


def complete_connect_account_setup(
    account_id: str,
    *,
    user,
    accept_agreement: bool,
    dob_year: int | None = None,
    dob_month: int | None = None,
    dob_day: int | None = None,
    ssn_last4: str | None = None,
) -> dict[str, Any]:
    if not accept_agreement:
        raise ValueError('You must accept the Stripe Connected Account Agreement.')

    validate_live_identity_fields(
        dob_year=dob_year,
        dob_month=dob_month,
        dob_day=dob_day,
        ssn_last4=ssn_last4,
    )

    configure_stripe()
    y, m, d = _resolve_dob(dob_year=dob_year, dob_month=dob_month, dob_day=dob_day)

    individual: dict[str, Any] = {
        'email': getattr(user, 'email', None) or None,
        'first_name': (getattr(user, 'first_name', '') or 'Driver')[:100],
        'last_name': (getattr(user, 'last_name', '') or 'User')[:100],
        'dob': {'day': d, 'month': m, 'year': y},
    }
    _apply_ssn_to_individual(individual, ssn_last4)

    phone = _stripe_individual_phone(getattr(user, 'phone_number', None))
    if phone:
        individual['phone'] = phone

    descriptor = getattr(settings, 'STRIPE_PLATFORM_STATEMENT_DESCRIPTOR', 'HolaDrive').strip()[:22]
    params: dict[str, Any] = {
        'individual': individual,
        'business_profile': {
            'mcc': getattr(settings, 'STRIPE_PLATFORM_MCC', '4121'),
            'product_description': getattr(
                settings, 'STRIPE_PLATFORM_PRODUCT_DESCRIPTION', 'Ride-hailing'
            ),
        },
        'settings': {
            'payments': {
                'statement_descriptor': descriptor,
            },
        },
        'tos_acceptance': {
            'date': int(__import__('time').time()),
            'ip': '127.0.0.1',
        },
    }

    stripe.Account.modify(account_id, **params)
    acct = retrieve_connect_account(account_id)
    from .stripe_connect_common import account_status_payload

    return account_status_payload(acct)
