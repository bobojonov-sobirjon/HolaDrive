"""Stripe Connect account lifecycle (create, payout schedule, retrieve)."""
from __future__ import annotations

from typing import Any

import stripe
from django.conf import settings


def configure_stripe() -> None:
    key = getattr(settings, 'STRIPE_SECRET_KEY', '') or ''
    if not key:
        raise RuntimeError('STRIPE_SECRET_KEY is not configured.')
    stripe.api_key = key


def is_stripe_live_mode() -> bool:
    key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    return key.startswith('sk_live_')


def apply_payout_schedule(account_id: str) -> None:
    if not getattr(settings, 'STRIPE_CONNECT_APPLY_PAYOUT_SCHEDULE', True):
        return
    interval = getattr(settings, 'STRIPE_CONNECT_PAYOUT_INTERVAL', 'weekly') or 'weekly'
    params: dict[str, Any] = {'interval': interval}
    if interval == 'weekly':
        params['weekly_anchor'] = getattr(settings, 'STRIPE_CONNECT_PAYOUT_WEEKLY_ANCHOR', 'monday') or 'monday'
    delay = getattr(settings, 'STRIPE_CONNECT_PAYOUT_DELAY_DAYS', '') or ''
    if delay.isdigit():
        params['delay_days'] = int(delay)
    stripe.Account.modify(account_id, settings={'payouts': {'schedule': params}})


def create_connect_account(*, email: str | None, user_id: int) -> str:
    configure_stripe()
    country = getattr(settings, 'STRIPE_CONNECT_COUNTRY', 'US') or 'US'
    acct = stripe.Account.create(
        type=getattr(settings, 'STRIPE_CONNECT_ACCOUNT_TYPE', 'custom') or 'custom',
        country=country,
        email=email or None,
        capabilities={
            'card_payments': {'requested': True},
            'transfers': {'requested': True},
        },
        business_type='individual',
        metadata={'django_user_id': str(user_id)},
    )
    apply_payout_schedule(acct.id)
    return acct.id


def retrieve_connect_account(account_id: str) -> Any:
    configure_stripe()
    return stripe.Account.retrieve(account_id)


def account_status_payload(acct: Any) -> dict[str, Any]:
    req = getattr(acct, 'requirements', None) or {}
    currently_due = list(getattr(req, 'currently_due', None) or req.get('currently_due') or [])
    disabled = getattr(req, 'disabled_reason', None) or req.get('disabled_reason')
    charges_enabled = bool(getattr(acct, 'charges_enabled', False))
    payouts_enabled = bool(getattr(acct, 'payouts_enabled', False))
    details_submitted = bool(getattr(acct, 'details_submitted', False))
    interval = getattr(settings, 'STRIPE_CONNECT_PAYOUT_INTERVAL', 'weekly') or 'weekly'
    anchor = getattr(settings, 'STRIPE_CONNECT_PAYOUT_WEEKLY_ANCHOR', 'monday') or 'monday'
    return {
        'charges_enabled': charges_enabled,
        'payouts_enabled': payouts_enabled,
        'details_submitted': details_submitted,
        'requirements_currently_due': currently_due,
        'requirements_disabled_reason': disabled,
        'requirements': {
            'needs_additional_setup': bool(currently_due),
            'currently_due': currently_due,
            'disabled_reason': disabled,
        },
        'onboarding_complete': bool(charges_enabled and payouts_enabled),
        'account': {
            'charges_enabled': charges_enabled,
            'payouts_enabled': payouts_enabled,
            'details_submitted': details_submitted,
        },
        'weekly_direct_deposit': {
            'enabled': interval == 'weekly',
            'interval': interval,
            'weekly_anchor': anchor if interval == 'weekly' else None,
            'fee_note': 'No fee',
        },
    }
