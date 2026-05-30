"""Driver checkout / cash history: completed orders (DB) + Stripe Connect ledger."""
from __future__ import annotations

from datetime import datetime, timezone as dt_tz
from decimal import Decimal
from typing import Any

import stripe
from django.conf import settings

from apps.accounts.models import CustomUser
from apps.order.models import Order, OrderDriver

from .checkout_fees import compute_checkout_preview
from .stripe_connect_common import configure_stripe, is_stripe_live_mode


def _cents_to_money(cents: int) -> str:
    return str((Decimal(cents) / Decimal('100')).quantize(Decimal('0.01')))


def _iso_timestamp(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=dt_tz.utc).isoformat()


def _completed_orders_qs(user: CustomUser):
    return (
        Order.objects.filter(
            order_drivers__driver=user,
            order_drivers__status=OrderDriver.DriverRequestStatus.ACCEPTED,
            status=Order.OrderStatus.COMPLETED,
        )
        .distinct()
        .order_by('-updated_at')
    )


def fetch_completed_orders_page(
    user: CustomUser,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    qs = _completed_orders_qs(user)
    total = qs.count()
    start = (page - 1) * page_size
    rows: list[dict[str, Any]] = []

    for o in qs[start : start + page_size]:
        preview = compute_checkout_preview(o)
        rows.append(
            {
                'order_id': o.id,
                'order_code': o.order_code,
                'order_number': o.order_code,
                'payment_type': o.payment_type,
                'stripe_payment_intent_id': o.stripe_trip_payment_intent_id or None,
                'stripe_payment_amount_cents': o.stripe_trip_payment_amount_cents,
                'stripe_payment_status': o.stripe_trip_payment_status or None,
                'stripe_payment_currency': (o.stripe_trip_payment_currency or preview['currency']).upper(),
                'customer_total': preview['customer_total'],
                'driver_payout_estimate': preview['driver_payout_estimate'],
                'completed_at': o.updated_at.isoformat() if o.updated_at else None,
            }
        )

    return {
        'results': rows,
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size if total else 0,
    }


def fetch_stripe_balance_transactions(
    user: CustomUser,
    *,
    limit: int = 30,
    starting_after: str | None = None,
) -> dict[str, Any]:
    acct_id = (user.stripe_connect_account_id or '').strip()
    if not acct_id:
        return {
            'results': [],
            'has_more': False,
            'starting_after_next': None,
        }

    configure_stripe()
    limit = max(1, min(100, int(limit)))
    params: dict[str, Any] = {'limit': limit, 'stripe_account': acct_id}
    if starting_after:
        params['starting_after'] = starting_after.strip()

    txs = stripe.BalanceTransaction.list(**params)
    results: list[dict[str, Any]] = []
    for tx in txs.data or []:
        amount_cents = int(tx.amount)
        fee_cents = int(getattr(tx, 'fee', 0) or 0)
        net_cents = int(getattr(tx, 'net', amount_cents) or amount_cents)
        results.append(
            {
                'id': tx.id,
                'type': tx.type,
                'amount_cents': amount_cents,
                'amount': _cents_to_money(abs(amount_cents)),
                'fee_cents': fee_cents,
                'fee': _cents_to_money(fee_cents),
                'net_cents': net_cents,
                'net': _cents_to_money(net_cents),
                'currency': (tx.currency or '').upper(),
                'description': tx.description or '',
                'created': _iso_timestamp(tx.created),
            }
        )

    next_cursor = txs.data[-1].id if getattr(txs, 'has_more', False) and txs.data else None
    return {
        'results': results,
        'has_more': bool(getattr(txs, 'has_more', False)),
        'starting_after_next': next_cursor,
    }


def build_checkout_history(
    user: CustomUser,
    *,
    page: int = 1,
    page_size: int = 20,
    stripe_tx_limit: int = 30,
    stripe_starting_after: str | None = None,
) -> dict[str, Any]:
    return {
        'stripe_connect_account_id': (user.stripe_connect_account_id or '').strip() or None,
        'livemode': is_stripe_live_mode(),
        'payout_mode': 'automatic_weekly',
        'orders': fetch_completed_orders_page(user, page=page, page_size=page_size),
        'stripe_balance_transactions': fetch_stripe_balance_transactions(
            user,
            limit=stripe_tx_limit,
            starting_after=stripe_starting_after,
        ),
    }
