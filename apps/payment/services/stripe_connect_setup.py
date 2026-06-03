"""Complete Stripe Connect Custom account (identity, TOS) — AutoHandy-style."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

import stripe
from django.conf import settings

from apps.accounts.services import normalize_phone_number

from .stripe_connect_common import configure_stripe, is_stripe_live_mode, retrieve_connect_account

# Swagger / placeholder values sometimes saved on user.phone_number or address
_INVALID_PROFILE_LITERALS = frozenset(
    {'string', 'null', 'none', 'undefined', 'phone', 'test', 'n/a', 'na', 'example', 'address'}
)

_US_STATE_ZIP_RE = re.compile(
    r'^(?P<state>[A-Za-z]{2})\s+(?P<postal>\d{5}(?:-\d{4})?)$'
)
_CITY_STATE_ZIP_RE = re.compile(
    r'^(?P<city>.+?)\s+(?P<state>[A-Za-z]{2})\s+(?P<postal>\d{5}(?:-\d{4})?)$'
)


def _normalize_ssn(raw: str | None) -> str:
    return (raw or '').strip().replace('-', '')


def _business_display_name(user) -> str:
    parts = [
        (getattr(user, 'first_name', '') or '').strip(),
        (getattr(user, 'last_name', '') or '').strip(),
    ]
    full = ' '.join(p for p in parts if p).strip()
    if not full:
        full = (user.get_full_name() or '').strip()
    if full:
        return full[:100]
    email_local = (getattr(user, 'email', '') or '').split('@')[0].strip()
    return (email_local or 'Driver')[:100]


def _business_url_for_stripe() -> str | None:
    """Stripe rejects example.com; prefer PUBLIC_BASE_URL from server .env."""
    url = (getattr(settings, 'STRIPE_PLATFORM_BUSINESS_URL', '') or '').strip()
    if not url or 'example.com' in url.lower():
        url = (getattr(settings, 'PUBLIC_BASE_URL', '') or '').strip()
    if not url:
        return None
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    return url


def _statement_descriptor_for_user(user) -> str:
    """
    Stripe validates that statement_descriptor matches business_profile.name / URL.
    Never use platform brand alone when the driver has a name on file.
    """
    name = _business_display_name(user)
    clean = re.sub(r'[^A-Za-z0-9 ]', ' ', name).strip()
    clean = re.sub(r'\s+', ' ', clean).upper()
    if len(clean) >= 5:
        return clean[:22]

    if len(clean) > 0:
        padded = f'{clean} DRV'[:22]
        if len(padded) >= 5:
            return padded

    raise ValueError(
        'Driver profile must include first_name and last_name (or full name) so Stripe '
        'can set a valid statement descriptor. Update the user profile, then complete-setup again.'
    )


def _clean_profile_text(raw: str | None) -> str | None:
    text = (raw or '').strip()
    if not text or text.lower() in _INVALID_PROFILE_LITERALS:
        return None
    return text


def _stripe_individual_phone(raw: str | None) -> str | None:
    """Return E.164 phone for Stripe, or None if missing/invalid (do not send bad values)."""
    phone = _clean_profile_text(raw)
    if not phone:
        return None

    digits = re.sub(r'\D', '', phone)
    if len(digits) < 10:
        return None

    normalized = normalize_phone_number(phone)
    if not normalized or not re.fullmatch(r'\+\d{10,15}', normalized):
        return None
    return normalized[:20]


def _stripe_connect_country() -> str:
    return (getattr(settings, 'STRIPE_CONNECT_COUNTRY', 'US') or 'US').upper()


def _parse_us_address(raw: str, *, live: bool) -> dict[str, str]:
    """
    Parse CustomUser.address (free text) into Stripe individual.address.
    Preferred format: "123 Main St, San Francisco, CA 94111"
    """
    parts = [p.strip() for p in re.split(r'[,\n]+', raw) if p.strip()]
    if len(parts) >= 3:
        line1 = parts[0]
        city = parts[-2]
        tail_match = _US_STATE_ZIP_RE.match(parts[-1])
        if tail_match:
            return {
                'line1': line1[:200],
                'city': city[:100],
                'state': tail_match.group('state').upper(),
                'postal_code': tail_match.group('postal'),
                'country': 'US',
            }

    if len(parts) == 2:
        line1 = parts[0]
        tail_match = _CITY_STATE_ZIP_RE.match(parts[1])
        if tail_match:
            return {
                'line1': line1[:200],
                'city': tail_match.group('city').strip()[:100],
                'state': tail_match.group('state').upper(),
                'postal_code': tail_match.group('postal'),
                'country': 'US',
            }

    if not live:
        return {
            'line1': raw[:200],
            'city': 'San Francisco',
            'state': 'CA',
            'postal_code': '94111',
            'country': 'US',
        }

    raise ValueError(
        'Profile address must include street, city, state, and ZIP '
        '(e.g. "123 Main St, San Francisco, CA 94111"). Update the user profile address.'
    )


def _stripe_individual_address_from_user(user) -> dict[str, str]:
    """Build Stripe address from CustomUser.address (not request body)."""
    raw = _clean_profile_text(getattr(user, 'address', None))
    if not raw:
        if is_stripe_live_mode():
            raise ValueError(
                'Profile address is required. Set address on the user account before Connect setup.'
            )
        return _parse_us_address('123 Test Street', live=False)

    country = _stripe_connect_country()
    if country == 'US':
        return _parse_us_address(raw, live=is_stripe_live_mode())

    # Non-US: send full text as line1; Stripe may accept with country only.
    return {
        'line1': raw[:200],
        'country': country,
    }


def validate_live_identity_fields(
    *,
    user=None,
    dob_year: int | None,
    dob_month: int | None,
    dob_day: int | None,
    ssn_last4: str | None,
) -> None:
    """Live mode: DOB (profile or body) + full 9-digit SSN required."""
    if not is_stripe_live_mode():
        return

    has_request_dob = (
        dob_year is not None and dob_month is not None and dob_day is not None
    )
    has_profile_dob = bool(user is not None and getattr(user, 'date_of_birth', None))
    if not has_request_dob and not has_profile_dob:
        raise ValueError(
            'Date of birth is required in live mode (profile date_of_birth or dob_year/month/day).'
        )

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
    user=None,
    dob_year: int | None,
    dob_month: int | None,
    dob_day: int | None,
) -> tuple[int, int, int]:
    if dob_year is not None and dob_month is not None and dob_day is not None:
        return dob_year, dob_month, dob_day

    profile_dob = getattr(user, 'date_of_birth', None) if user is not None else None
    if profile_dob:
        return profile_dob.year, profile_dob.month, profile_dob.day

    if is_stripe_live_mode():
        raise ValueError(
            'Date of birth is required in live mode (profile date_of_birth or dob_year/month/day in request).'
        )

    today = date.today()
    return today.year - 25, 1, 1


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
        user=user,
        dob_year=dob_year,
        dob_month=dob_month,
        dob_day=dob_day,
        ssn_last4=ssn_last4,
    )

    configure_stripe()
    y, m, d = _resolve_dob(
        user=user,
        dob_year=dob_year,
        dob_month=dob_month,
        dob_day=dob_day,
    )

    individual: dict[str, Any] = {
        'email': getattr(user, 'email', None) or None,
        'first_name': (getattr(user, 'first_name', '') or 'Driver')[:100],
        'last_name': (getattr(user, 'last_name', '') or 'User')[:100],
        'dob': {'day': d, 'month': m, 'year': y},
        'address': _stripe_individual_address_from_user(user),
    }
    _apply_ssn_to_individual(individual, ssn_last4)

    phone = _stripe_individual_phone(getattr(user, 'phone_number', None))
    if not phone:
        if is_stripe_live_mode():
            raise ValueError(
                'Profile phone_number is required (E.164, e.g. +14155552671). '
                'Update the user account before Connect setup.'
            )
        phone = '+14085551234'
    individual['phone'] = phone

    business_name = _business_display_name(user)
    descriptor = _statement_descriptor_for_user(user)
    business_url = _business_url_for_stripe()
    if not business_url:
        raise ValueError(
            'Business website is required for Stripe Connect. '
            'Set STRIPE_PLATFORM_BUSINESS_URL or PUBLIC_BASE_URL in server .env '
            '(must be a real URL, not example.com).'
        )

    business_profile: dict[str, Any] = {
        'name': business_name,
        'url': business_url,
        'mcc': getattr(settings, 'STRIPE_PLATFORM_MCC', '4121'),
        'product_description': getattr(
            settings, 'STRIPE_PLATFORM_PRODUCT_DESCRIPTION', 'Ride-hailing'
        ),
    }

    params: dict[str, Any] = {
        'individual': individual,
        'business_profile': business_profile,
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
