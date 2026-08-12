"""Driver cash history — Stripe Connect payouts (manual withdraw + history)."""
from __future__ import annotations

from datetime import datetime, timezone as dt_tz
from typing import Any

import stripe

from apps.accounts.models import CustomUser

from .connect_balance import fetch_connect_balance_and_payouts
from .stripe_connect_common import configure_stripe, is_stripe_live_mode


def _iso_timestamp(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=dt_tz.utc).isoformat()


def _payout_row(p) -> dict[str, Any]:
    from .connect_balance import _cents_to_money

    return {
        'id': p.id,
        'source': 'stripe_payout',
        'payout_type': 'driver_withdraw',
        'amount': _cents_to_money(int(p.amount)),
        'amount_cents': int(p.amount),
        'currency': (p.currency or '').upper(),
        'status': p.status,
        'payment_type': 'bank',
        'arrival_date': _iso_timestamp(p.arrival_date),
        'created_at': _iso_timestamp(p.created),
    }


def build_driver_cash_history(
    user: CustomUser,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """
    Connect payout history for driver earnings screen.
    """
    acct_id = (user.stripe_connect_account_id or '').strip()
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))

    if not acct_id:
        return {
            'payout_mode': 'manual_withdraw',
            'stripe_connect_account_id': None,
            'livemode': is_stripe_live_mode(),
            'balance': None,
            'results': [],
            'count': 0,
            'page': page,
            'page_size': page_size,
            'note': 'Link a bank account via Stripe Connect, then withdraw earnings anytime.',
        }

    balance = fetch_connect_balance_and_payouts(user, payout_limit=min(page_size, 10))

    configure_stripe()
    # Stripe Payout.list is cursor-based; fetch enough rows then slice for page.
    fetch_limit = min(100, page * page_size)
    payouts = stripe.Payout.list(limit=fetch_limit, stripe_account=acct_id)
    all_rows = [_payout_row(p) for p in (payouts.data or [])]
    total = len(all_rows)
    if getattr(payouts, 'has_more', False):
        total = max(total, fetch_limit)

    start = (page - 1) * page_size
    page_rows = all_rows[start : start + page_size]

    payout_mode = balance.get('payout_mode', 'manual_withdraw')

    return {
        'payout_mode': payout_mode,
        'stripe_connect_account_id': acct_id,
        'livemode': is_stripe_live_mode(),
        'balance': {
            'available': balance['available'],
            'pending': balance['pending'],
            'available_cents': balance['available_cents'],
            'pending_cents': balance['pending_cents'],
            'instant_available_cents': balance.get('instant_available_cents', 0),
            'currency': balance['currency'],
        },
        'payout_schedule': balance['payout_schedule'],
        'payout_schedule_note': balance['payout_schedule_note'],
        'results': page_rows,
        'count': total,
        'page': page,
        'page_size': page_size,
        'note': (
            'Withdraw available earnings with POST /api/v1/payment/driver/stripe-connect/withdraw/. '
            'Set instant=true for instant payout when Stripe supports it on your bank.'
        ),
    }


def recent_cash_history_for_dashboard(user: CustomUser, *, limit: int = 20) -> list[dict[str, Any]]:
    """Short list for dashboard earnings screen."""
    acct_id = (user.stripe_connect_account_id or '').strip()
    if not acct_id:
        return []

    configure_stripe()
    payouts = stripe.Payout.list(limit=min(limit, 20), stripe_account=acct_id)
    return [_payout_row(p) for p in (payouts.data or [])]
