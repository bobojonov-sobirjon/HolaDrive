"""
Charge rider card when a trip completes (Stripe PaymentIntent, optional Connect payout).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Any

import stripe
from django.conf import settings

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser
    from apps.order.models import Order

MIN_AMOUNT_CENTS = 50


def _configure_stripe() -> None:
    key = getattr(settings, 'STRIPE_SECRET_KEY', '') or ''
    if not key:
        raise ValueError('STRIPE_SECRET_KEY is not configured.')
    stripe.api_key = key


def order_trip_total_money(order: 'Order') -> Decimal:
    """Final trip total from order items (same basis as driver net_price)."""
    total = Decimal('0')
    for item in order.order_items.all():
        p = item.adjusted_price or item.calculated_price or item.original_price
        if p is not None:
            total += Decimal(str(p))
    return total.quantize(Decimal('0.01'), ROUND_HALF_UP)


def _money_to_cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal('1'), ROUND_HALF_UP))


def charge_trip_card_payment(order: 'Order', driver_user: 'CustomUser') -> dict[str, Any]:
    """
    Confirm off-session PaymentIntent for the rider; optional destination charge to driver's Connect account.

    Returns:
        dict with payment_intent_id, amount_cents, currency

    Raises:
        ValueError — validation / business rules
        stripe.error.StripeError — Stripe API
    """
    from apps.order.models import Order

    if order.payment_type != Order.PaymentType.CARD:
        raise ValueError('Order is not a card payment.')

    if not order.saved_card_id or not order.saved_card:
        raise ValueError('No saved card on this order. Rider must select a card before completing a card trip.')

    sc = order.saved_card
    pm_id = sc.stripe_payment_method_id
    customer_id = (sc.stripe_customer_id or '').strip()
    if not customer_id:
        raise ValueError('Saved card has no Stripe customer id.')

    total = order_trip_total_money(order)
    if total <= 0:
        raise ValueError('Trip total is zero; cannot charge.')

    total_cents = _money_to_cents(total)
    if total_cents < MIN_AMOUNT_CENTS:
        raise ValueError(f'Amount below Stripe minimum ({MIN_AMOUNT_CENTS} minor units).')

    currency = (getattr(settings, 'STRIPE_CHARGE_CURRENCY', None) or 'cad').strip().lower()
    dest = (getattr(driver_user, 'stripe_connect_account_id', None) or '').strip()

    fee_percent = Decimal(str(getattr(settings, 'STRIPE_APPLICATION_FEE_PERCENT', '0') or '0'))
    if fee_percent < 0 or fee_percent > 100:
        fee_percent = Decimal('0')

    _configure_stripe()

    intent_params: dict[str, Any] = {
        'amount': total_cents,
        'currency': currency,
        'customer': customer_id,
        'payment_method': pm_id,
        'confirm': True,
        'off_session': True,
        'metadata': {
            'order_id': str(order.id),
            'order_code': order.order_code or '',
            'driver_id': str(driver_user.id),
        },
        'description': f'HolaDrive trip ORD-{order.id}',
        'idempotency_key': f'holadrive_order_{order.id}_trip_complete_v1',
    }

    if dest:
        intent_params['transfer_data'] = {'destination': dest}
        fee_cents = int(
            (Decimal(total_cents) * fee_percent / Decimal('100')).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
        )
        if fee_cents > 0:
            if fee_cents >= total_cents:
                fee_cents = total_cents - 1
            intent_params['application_fee_amount'] = max(1, fee_cents)

    intent = stripe.PaymentIntent.create(**intent_params)

    if intent.status != 'succeeded':
        if intent.status == 'requires_action':
            raise ValueError(
                'Payment requires additional authentication (e.g. 3D Secure). '
                'The rider must complete payment in the app with a client-side confirmation flow.'
            )
        raise ValueError(f'Payment not completed (Stripe status: {intent.status}).')

    return {
        'payment_intent_id': intent.id,
        'amount_cents': total_cents,
        'currency': currency,
    }
