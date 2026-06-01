"""Complete Stripe Connect Custom account (identity, TOS, address, phone)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import stripe
from django.conf import settings

from .stripe_connect_common import configure_stripe, is_stripe_live_mode, retrieve_connect_account


@dataclass(frozen=True)
class ConnectProfileInput:
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


def _normalize_ssn(raw: str | None) -> str:
    return (raw or '').strip().replace('-', '')


def _clean(value: str | None) -> str:
    return (value or '').strip()


def _resolve_phone(user, phone: str | None) -> str:
    return _clean(phone) or _clean(getattr(user, 'phone_number', None))


def _resolve_country(country: str | None) -> str:
    c = (_clean(country) or getattr(settings, 'STRIPE_CONNECT_COUNTRY', 'US') or 'US').upper()
    return c[:2]


def _build_stripe_address(profile: ConnectProfileInput) -> dict[str, str] | None:
    line1 = _clean(profile.address_line1)
    city = _clean(profile.city)
    state = _clean(profile.state).upper()
    postal_code = _clean(profile.postal_code)
    country = _resolve_country(profile.country)

    if not any([line1, city, state, postal_code]):
        return None

    addr: dict[str, str] = {'country': country}
    if line1:
        addr['line1'] = line1[:200]
    line2 = _clean(profile.address_line2)
    if line2:
        addr['line2'] = line2[:200]
    if city:
        addr['city'] = city[:100]
    if state:
        addr['state'] = state[:2]
    if postal_code:
        addr['postal_code'] = postal_code[:20]
    return addr


def _test_profile_defaults() -> ConnectProfileInput:
    return ConnectProfileInput(
        phone='+15555550100',
        address_line1='1234 Main Street',
        address_line2='',
        city='San Francisco',
        state='CA',
        postal_code='94111',
        country='US',
    )


def validate_live_identity_fields(
    *,
    dob_year: int | None,
    dob_month: int | None,
    dob_day: int | None,
    ssn_last4: str | None,
) -> None:
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


def validate_live_connect_profile_fields(user, profile: ConnectProfileInput) -> None:
    """Address + phone required in live mode (request body or user profile)."""
    if not is_stripe_live_mode():
        return

    phone = _resolve_phone(user, profile.phone)
    if not phone:
        raise ValueError('Phone number is required in live mode (phone or user profile phone_number).')

    line1 = _clean(profile.address_line1)
    city = _clean(profile.city)
    state = _clean(profile.state)
    postal_code = _clean(profile.postal_code)
    if not line1:
        raise ValueError('address_line1 is required in live mode.')
    if not city:
        raise ValueError('city is required in live mode.')
    if not state or len(state) != 2:
        raise ValueError('state is required in live mode (2-letter US code, e.g. CA).')
    if not postal_code:
        raise ValueError('postal_code is required in live mode.')


def resolve_connect_profile(user, profile: ConnectProfileInput) -> ConnectProfileInput:
    """Merge request profile with user profile; apply test defaults when needed."""
    phone = _resolve_phone(user, profile.phone)
    line1 = _clean(profile.address_line1)
    city = _clean(profile.city)
    state = _clean(profile.state)
    postal_code = _clean(profile.postal_code)
    country = _resolve_country(profile.country)
    line2 = _clean(profile.address_line2)

    if not is_stripe_live_mode() and not all([line1, city, state, postal_code]):
        defaults = _test_profile_defaults()
        line1 = line1 or defaults.address_line1
        city = city or defaults.city
        state = state or defaults.state
        postal_code = postal_code or defaults.postal_code
        country = country or defaults.country
        line2 = line2 or defaults.address_line2
        phone = phone or defaults.phone

    return ConnectProfileInput(
        phone=phone,
        address_line1=line1,
        address_line2=line2,
        city=city,
        state=state,
        postal_code=postal_code,
        country=country,
    )


def _apply_ssn_to_individual(individual: dict[str, Any], ssn_last4: str | None) -> None:
    ssn = _normalize_ssn(ssn_last4)
    if not ssn:
        return

    if is_stripe_live_mode():
        individual['id_number'] = ssn
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


def _statement_descriptor() -> str:
    return getattr(settings, 'STRIPE_PLATFORM_STATEMENT_DESCRIPTOR', 'HolaDrive').strip()[:22]


def complete_connect_account_setup(
    account_id: str,
    *,
    user,
    accept_agreement: bool,
    dob_year: int | None = None,
    dob_month: int | None = None,
    dob_day: int | None = None,
    ssn_last4: str | None = None,
    profile: ConnectProfileInput | None = None,
) -> dict[str, Any]:
    if not accept_agreement:
        raise ValueError('You must accept the Stripe Connected Account Agreement.')

    raw_profile = profile or ConnectProfileInput()
    validate_live_identity_fields(
        dob_year=dob_year,
        dob_month=dob_month,
        dob_day=dob_day,
        ssn_last4=ssn_last4,
    )
    validate_live_connect_profile_fields(user, raw_profile)
    resolved = resolve_connect_profile(user, raw_profile)

    configure_stripe()
    y, m, d = _resolve_dob(dob_year=dob_year, dob_month=dob_month, dob_day=dob_day)

    individual: dict[str, Any] = {
        'email': getattr(user, 'email', None) or None,
        'first_name': (getattr(user, 'first_name', '') or 'Driver')[:100],
        'last_name': (getattr(user, 'last_name', '') or 'User')[:100],
        'dob': {'day': d, 'month': m, 'year': y},
    }
    _apply_ssn_to_individual(individual, ssn_last4)

    if resolved.phone:
        individual['phone'] = resolved.phone[:20]

    address = _build_stripe_address(resolved)
    if address:
        individual['address'] = address

    descriptor = _statement_descriptor()
    params: dict[str, Any] = {
        'individual': individual,
        'business_profile': {
            'mcc': getattr(settings, 'STRIPE_PLATFORM_MCC', '4121'),
            'product_description': getattr(
                settings, 'STRIPE_PLATFORM_PRODUCT_DESCRIPTION', 'Ride-hailing'
            ),
            'support_phone': resolved.phone[:20] if resolved.phone else None,
        },
        'settings': {
            'payments': {
                'statement_descriptor': descriptor,
            },
            'payouts': {
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
