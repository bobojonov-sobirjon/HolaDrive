"""Marketplace checkout breakdown for rider/driver preview."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

from apps.payment.services.trip_charge import order_trip_total_money


def _pct(amount: Decimal, percent: str) -> Decimal:
    p = Decimal(str(percent or '0'))
    if p <= 0:
        return Decimal('0')
    return (amount * p / Decimal('100')).quantize(Decimal('0.01'), ROUND_HALF_UP)


def compute_checkout_preview(order) -> dict:
    """
    Job total from order items; optional rider/driver fee lines from settings.
    """
    job_total = order_trip_total_money(order)
    rider_platform = _pct(job_total, getattr(settings, 'CUSTOMER_PLATFORM_FEE_PERCENT', '0'))
    rider_service = _pct(job_total, getattr(settings, 'CUSTOMER_SERVICE_FEE_PERCENT', '0'))
    driver_platform_pct = Decimal(str(getattr(settings, 'PROVIDER_PLATFORM_FEE_PERCENT', '0') or '0'))
    driver_fee = _pct(job_total, str(driver_platform_pct))
    customer_total = (job_total + rider_platform + rider_service).quantize(Decimal('0.01'))
    driver_payout = (job_total - driver_fee).quantize(Decimal('0.01'))
    if driver_payout < 0:
        driver_payout = Decimal('0')

    currency = getattr(settings, 'STRIPE_CHARGE_CURRENCY', 'cad')

    return {
        'order_id': order.id,
        'order_code': order.order_code,
        'payment_type': order.payment_type,
        'currency': currency,
        'job_total': str(job_total),
        'rider_platform_fee': str(rider_platform),
        'rider_service_fee': str(rider_service),
        'customer_total': str(customer_total),
        'driver_platform_fee_percent': str(driver_platform_pct),
        'driver_platform_fee': str(driver_fee),
        'driver_payout_estimate': str(driver_payout),
        'note': 'Card trips are charged customer_total on driver complete. Connect transfer uses driver_payout_estimate when driver has acct_….',
    }
