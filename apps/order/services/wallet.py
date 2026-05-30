from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.accounts.models import CustomUser
from apps.order.models import DriverCashout, DriverWalletBalance, DriverWalletTransaction, Order


def _d(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v or 0))


@transaction.atomic
def get_or_create_balance(driver: CustomUser) -> DriverWalletBalance:
    bal, _ = DriverWalletBalance.objects.select_for_update().get_or_create(driver=driver)
    return bal


@transaction.atomic
def apply_trip_earning(*, driver: CustomUser, order: Order, amount: Decimal, payment_type: str) -> DriverWalletTransaction:
    """
    Creates an earning ledger row (idempotent per order) and updates cached balance.
    Cash is tracked as lifetime only; card/hola_wallet_cash are withdrawable (available).
    """
    amount = _d(amount).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("Earning amount must be > 0")

    if payment_type not in (Order.PaymentType.CARD, Order.PaymentType.CASH, Order.PaymentType.HOLA_WALLET_CASH):
        raise ValueError("Invalid payment_type")

    tx, created = DriverWalletTransaction.objects.get_or_create(
        order=order,
        kind=DriverWalletTransaction.Kind.EARNING,
        defaults={
            "driver": driver,
            "cashout": None,
            "payment_type": payment_type,
            "amount": amount,
            "note": f"Trip earning for {order.order_code or order.id}",
        },
    )

    if not created:
        return tx

    bal = get_or_create_balance(driver)
    if payment_type == Order.PaymentType.CARD:
        bal.lifetime_card = _d(bal.lifetime_card) + amount
        bal.available_card = _d(bal.available_card) + amount
    elif payment_type == Order.PaymentType.HOLA_WALLET_CASH:
        bal.lifetime_hola_wallet_cash = _d(bal.lifetime_hola_wallet_cash) + amount
        bal.available_hola_wallet_cash = _d(bal.available_hola_wallet_cash) + amount
    else:
        bal.lifetime_cash = _d(bal.lifetime_cash) + amount
    bal.save()
    return tx


@transaction.atomic
def apply_cashout_withdrawal(*, cashout: DriverCashout) -> DriverWalletTransaction:
    """
    On admin COMPLETED cashout, create a withdrawal ledger row (idempotent per cashout)
    and decrement withdrawable balance (card / hola_wallet_cash only).
    """
    if cashout.status != DriverCashout.Status.COMPLETED:
        raise ValueError("Cashout must be completed to apply withdrawal")

    payment_type = cashout.payment_type
    if payment_type == Order.PaymentType.CASH:
        raise ValueError("Cash is not withdrawable")
    if payment_type not in (Order.PaymentType.CARD, Order.PaymentType.HOLA_WALLET_CASH):
        raise ValueError("Invalid payment_type")

    amount = _d(cashout.amount).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("Withdrawal amount must be > 0")

    tx, created = DriverWalletTransaction.objects.get_or_create(
        cashout=cashout,
        kind=DriverWalletTransaction.Kind.WITHDRAWAL,
        defaults={
            "driver": cashout.driver,
            "order": None,
            "payment_type": payment_type,
            "amount": -amount,
            "note": f"Cashout withdrawal #{cashout.id}",
        },
    )
    if not created:
        return tx

    bal = get_or_create_balance(cashout.driver)
    if payment_type == Order.PaymentType.CARD:
        new_val = _d(bal.available_card) - amount
        if new_val < 0:
            raise ValueError("Insufficient card balance")
        bal.available_card = new_val
    else:
        new_val = _d(bal.available_hola_wallet_cash) - amount
        if new_val < 0:
            raise ValueError("Insufficient hola_wallet_cash balance")
        bal.available_hola_wallet_cash = new_val
    bal.save()
    return tx


def get_withdrawable_amounts(driver: CustomUser) -> dict[str, Decimal]:
    bal = DriverWalletBalance.objects.filter(driver=driver).first()
    if not bal:
        return {
            Order.PaymentType.CARD: Decimal("0.00"),
            Order.PaymentType.HOLA_WALLET_CASH: Decimal("0.00"),
        }
    return {
        Order.PaymentType.CARD: _d(bal.available_card).quantize(Decimal("0.01")),
        Order.PaymentType.HOLA_WALLET_CASH: _d(bal.available_hola_wallet_cash).quantize(Decimal("0.01")),
    }

