"""Driver Connect bank linking (US external account) + payout profile."""
from __future__ import annotations

from typing import Any

import stripe
from django.conf import settings

from apps.accounts.models import CustomUser

from .stripe_connect_common import (
    account_status_payload,
    configure_stripe,
    create_connect_account,
    is_stripe_live_mode,
    retrieve_connect_account,
)
from .stripe_connect_setup import complete_connect_account_setup


def _list_connect_bank_accounts(acct: Any) -> list[Any]:
    external = getattr(acct, 'external_accounts', None)
    data = getattr(external, 'data', None) if external else None
    if not data:
        return []
    return [ext for ext in data if getattr(ext, 'object', '') == 'bank_account']


def _clear_user_connect_account(user: CustomUser) -> None:
    user.stripe_connect_account_id = ''
    user.save(update_fields=['stripe_connect_account_id'])


def _mask_bank(acct: Any) -> dict[str, Any] | None:
    default = None
    external = getattr(acct, 'external_accounts', None)
    data = getattr(external, 'data', None) if external else None
    if not data:
        return None
    for ext in data:
        if getattr(ext, 'object', '') == 'bank_account' and getattr(ext, 'default_for_currency', False):
            default = ext
            break
    if not default and data:
        default = data[0]
    if not default:
        return None
    bank = getattr(default, 'bank_name', None) or 'Bank'
    last4 = getattr(default, 'last4', '') or '????'
    return {
        'bank_account_id': getattr(default, 'id', ''),
        'bank_name': bank,
        'last4': last4,
        'currency': getattr(default, 'currency', ''),
        'status': getattr(default, 'status', ''),
        'display': f'{bank} •••• {last4}',
    }


def build_driver_payout_profile(user: CustomUser) -> dict[str, Any]:
    acct_id = (getattr(user, 'stripe_connect_account_id', None) or '').strip()
    base: dict[str, Any] = {
        'stripe_connect_account_id': acct_id or None,
        'stripe_publishable_key': (getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '') or '').strip() or None,
        'connected_account_agreement_url': getattr(
            settings, 'STRIPE_CONNECTED_ACCOUNT_AGREEMENT_URL', ''
        ),
        'bank': None,
        'bank_account': None,
        'live_mode': (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip().startswith('sk_live_'),
    }
    if not acct_id:
        base.update(
            {
                'onboarding_complete': False,
                'charges_enabled': False,
                'payouts_enabled': False,
                'requirements_currently_due': [],
                'requirements': None,
                'account': None,
                'weekly_direct_deposit': None,
            }
        )
        return base

    acct = retrieve_connect_account(acct_id)
    base.update(account_status_payload(acct))
    bank = _mask_bank(acct)
    base['bank'] = bank
    base['bank_account'] = bank
    return base


def ensure_connect_and_add_bank(
    user: CustomUser,
    *,
    routing_number: str,
    account_number: str,
    account_holder_name: str,
    account_holder_type: str,
    accept_agreement: bool,
) -> dict[str, Any]:
    configure_stripe()
    acct_id = (user.stripe_connect_account_id or '').strip()
    if not acct_id:
        acct_id = create_connect_account(email=user.email, user_id=user.id)
        user.stripe_connect_account_id = acct_id
        user.save(update_fields=['stripe_connect_account_id'])

    country = getattr(settings, 'STRIPE_CONNECT_COUNTRY', 'US') or 'US'
    currency = 'usd' if country == 'US' else getattr(settings, 'STRIPE_CHARGE_CURRENCY', 'cad')

    stripe.Account.create_external_account(
        acct_id,
        external_account={
            'object': 'bank_account',
            'country': country,
            'currency': currency,
            'routing_number': routing_number.strip(),
            'account_number': account_number.strip(),
            'account_holder_name': account_holder_name.strip() or user.get_full_name(),
            'account_holder_type': account_holder_type or 'individual',
        },
    )

    # Test: auto-enable with server-side DOB/SSN defaults.
    # Live: bank only here — call POST complete-setup for DOB/SSN + agreement.
    if not is_stripe_live_mode():
        complete_connect_account_setup(
            acct_id,
            user=user,
            accept_agreement=accept_agreement,
        )

    user.refresh_from_db()
    return build_driver_payout_profile(user)


def remove_bank_account(user: CustomUser, bank_account_id: str | None = None) -> dict[str, Any]:
    acct_id = (user.stripe_connect_account_id or '').strip()
    if not acct_id:
        raise ValueError('No Stripe Connect account linked.')

    configure_stripe()
    acct = retrieve_connect_account(acct_id)
    banks = _list_connect_bank_accounts(acct)
    if not banks:
        raise ValueError('No bank account to remove.')

    ext_id = (bank_account_id or '').strip()
    if not ext_id:
        masked = _mask_bank(acct)
        if not masked:
            raise ValueError('No bank account to remove.')
        ext_id = masked['bank_account_id']

    target = next((b for b in banks if getattr(b, 'id', None) == ext_id), None)
    if target is None:
        raise ValueError('Bank account not found on this Connect account.')

    # Stripe blocks deleting the sole default bank for the account currency.
    if len(banks) == 1:
        stripe.Account.delete(acct_id)
        _clear_user_connect_account(user)
        user.refresh_from_db()
        return build_driver_payout_profile(user)

    if getattr(target, 'default_for_currency', False):
        replacement = next((b for b in banks if getattr(b, 'id', None) != ext_id), None)
        if replacement is not None:
            stripe.Account.modify_external_account(
                acct_id,
                getattr(replacement, 'id'),
                default_for_currency=True,
            )

    try:
        stripe.Account.delete_external_account(acct_id, ext_id)
    except stripe.error.StripeError as exc:
        message = str(exc)
        if 'default external account' in message.lower():
            stripe.Account.delete(acct_id)
            _clear_user_connect_account(user)
            user.refresh_from_db()
            return build_driver_payout_profile(user)
        raise

    return build_driver_payout_profile(user)
