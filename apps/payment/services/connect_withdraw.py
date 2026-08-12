"""Driver-initiated Stripe Connect payouts (standard + instant when available)."""
from __future__ import annotations

from typing import Any

import stripe
from django.conf import settings

from apps.accounts.models import CustomUser

from .connect_balance import _cents_to_money, _iso_timestamp, fetch_connect_balance_and_payouts
from .stripe_connect_common import configure_stripe, ensure_manual_payout_schedule, resolve_user_connect_account_id


class WithdrawError(ValueError):
    pass


def request_driver_withdraw(
    user: CustomUser,
    *,
    amount_cents: int | None = None,
    instant: bool = False,
) -> dict[str, Any]:
    """
    Withdraw available Connect balance to the driver's linked bank.
    amount_cents: optional; omit to withdraw full available balance.
    instant: use Stripe instant payout when supported and balance allows.
    """
    acct_id = resolve_user_connect_account_id(user)
    if not acct_id:
        raise WithdrawError('Link a bank account before withdrawing.')

    configure_stripe()
    ensure_manual_payout_schedule(acct_id)

    balance = fetch_connect_balance_and_payouts(user, payout_limit=5)
    currency = (balance.get('currency') or getattr(settings, 'STRIPE_CHARGE_CURRENCY', 'cad') or 'cad').lower()
    available_cents = int(balance.get('available_cents') or 0)
    instant_rows = balance.get('instant_available') or []
    instant_cents = sum(
        int(r.get('amount_cents') or 0)
        for r in instant_rows
        if str(r.get('currency', currency)).lower() == currency
    )

    if available_cents <= 0:
        raise WithdrawError('No available balance to withdraw.')

    withdraw_cents = int(amount_cents) if amount_cents is not None else available_cents
    if withdraw_cents <= 0:
        raise WithdrawError('Withdraw amount must be greater than zero.')
    if withdraw_cents > available_cents:
        raise WithdrawError(
            f'Amount exceeds available balance ({balance.get("available_total")} {currency.upper()}).'
        )

    method = 'standard'
    if instant:
        if instant_cents <= 0:
            raise WithdrawError(
                'Instant payout is not available for this account or balance. '
                'Try standard withdraw or check Stripe / bank eligibility.'
            )
        if withdraw_cents > instant_cents:
            raise WithdrawError(
                f'Instant payout limit is {_cents_to_money(instant_cents)} {currency.upper()}. '
                'Lower the amount or use standard withdraw.'
            )
        method = 'instant'

    payout = stripe.Payout.create(
        amount=withdraw_cents,
        currency=currency,
        method=method,
        stripe_account=acct_id,
        metadata={'django_user_id': str(user.id), 'payout_mode': 'driver_withdraw'},
    )

    updated_balance = fetch_connect_balance_and_payouts(user, payout_limit=5)

    return {
        'payout': {
            'id': payout.id,
            'amount': _cents_to_money(withdraw_cents),
            'amount_cents': withdraw_cents,
            'currency': currency.upper(),
            'status': payout.status,
            'method': method,
            'arrival_date': _iso_timestamp(getattr(payout, 'arrival_date', None)),
            'created': _iso_timestamp(getattr(payout, 'created', None)),
        },
        'balance': updated_balance,
        'message': (
            'Instant withdrawal initiated.'
            if method == 'instant'
            else 'Withdrawal initiated. Funds will arrive per your bank schedule (typically 1–2 business days).'
        ),
    }
