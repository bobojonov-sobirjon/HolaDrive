"""Stripe Connect balance and payout history for driver UI."""
from __future__ import annotations

from datetime import datetime, timezone as dt_tz
from decimal import Decimal
from typing import Any

import stripe
from django.conf import settings

from apps.accounts.models import CustomUser

from .stripe_connect_common import configure_stripe, is_stripe_live_mode


def _cents_to_money(cents: int) -> str:
    return str((Decimal(cents) / Decimal('100')).quantize(Decimal('0.01')))


def _iso_timestamp(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=dt_tz.utc).isoformat()


def _balance_buckets(items, *, default_currency: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items or []:
        cents = int(getattr(item, 'amount', 0) or 0)
        currency = (getattr(item, 'currency', None) or default_currency or 'usd').upper()
        rows.append(
            {
                'currency': currency,
                'amount_cents': cents,
                'amount': _cents_to_money(cents),
            }
        )
    return rows


def _sum_bucket_cents(rows: list[dict[str, Any]], currency: str) -> int:
    cur = currency.lower()
    return sum(r['amount_cents'] for r in rows if r['currency'].lower() == cur)


def fetch_connect_balance_and_payouts(user: CustomUser, *, payout_limit: int = 10) -> dict[str, Any]:
    acct_id = (user.stripe_connect_account_id or '').strip()
    if not acct_id:
        raise ValueError('Driver has no Stripe Connect account. Link a bank account first.')

    configure_stripe()
    bal = stripe.Balance.retrieve(stripe_account=acct_id)
    default_currency = (getattr(settings, 'STRIPE_CHARGE_CURRENCY', 'cad') or 'cad').lower()

    available = _balance_buckets(getattr(bal, 'available', []), default_currency=default_currency)
    pending = _balance_buckets(getattr(bal, 'pending', []), default_currency=default_currency)
    instant_available = _balance_buckets(
        getattr(bal, 'instant_available', []), default_currency=default_currency
    )

    avail_cents = _sum_bucket_cents(available, default_currency) if available else 0
    pend_cents = _sum_bucket_cents(pending, default_currency) if pending else 0
    currency = default_currency
    if available:
        currency = available[0]['currency'].lower()
    elif pending:
        currency = pending[0]['currency'].lower()

    payouts = stripe.Payout.list(limit=payout_limit, stripe_account=acct_id)
    recent: list[dict[str, Any]] = []
    for p in payouts.data or []:
        recent.append(
            {
                'id': p.id,
                'amount': _cents_to_money(int(p.amount)),
                'amount_cents': int(p.amount),
                'currency': (p.currency or currency).upper(),
                'status': p.status,
                'arrival_date': _iso_timestamp(p.arrival_date),
                'created': _iso_timestamp(p.created),
            }
        )

    anchor = getattr(settings, 'STRIPE_CONNECT_PAYOUT_WEEKLY_ANCHOR', 'monday')
    interval = getattr(settings, 'STRIPE_CONNECT_PAYOUT_INTERVAL', 'weekly')

    return {
        'stripe_connect_account_id': acct_id,
        'livemode': is_stripe_live_mode(),
        'currency': currency,
        'available': available,
        'pending': pending,
        'instant_available': instant_available,
        # Flat totals for simple clients
        'available_total': _cents_to_money(avail_cents),
        'available_cents': avail_cents,
        'pending_total': _cents_to_money(pend_cents),
        'pending_cents': pend_cents,
        'recent_payouts': recent,
        'payout_mode': 'automatic_weekly',
        'payout_schedule': {
            'interval': interval,
            'weekly_anchor': anchor if interval == 'weekly' else None,
        },
        'payout_schedule_note': (
            f'Automatic {interval} bank deposits (anchor: {anchor}). '
            'Trip earnings land in pending first, then become available, then Stripe pays out to your bank. '
            'No manual cash-out is required.'
        ),
    }
