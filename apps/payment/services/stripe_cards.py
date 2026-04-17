"""
Sync helpers for Stripe Customer + PaymentMethod (saved cards).
Called from async views via sync_to_async.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import stripe
from django.conf import settings
from django.db import transaction

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser

logger = logging.getLogger(__name__)

_MISSING = object()


def _configure_stripe() -> None:
    key = getattr(settings, 'STRIPE_SECRET_KEY', '') or ''
    if not key:
        raise RuntimeError('STRIPE_SECRET_KEY is not configured.')
    stripe.api_key = key


def get_existing_stripe_customer_id(user: 'CustomUser') -> str | None:
    from apps.payment.models import SavedCard

    cid = (
        SavedCard.objects.filter(user=user)
        .exclude(stripe_customer_id='')
        .values_list('stripe_customer_id', flat=True)
        .first()
    )
    return cid or None


def get_or_create_stripe_customer_id(user: 'CustomUser') -> str:
    _configure_stripe()
    existing = get_existing_stripe_customer_id(user)
    if existing:
        return existing
    customer = stripe.Customer.create(
        email=(user.email or None) if getattr(user, 'email', None) else None,
        metadata={'django_user_id': str(user.pk)},
    )
    return customer.id


def retrieve_payment_method(payment_method_id: str) -> Any:
    _configure_stripe()
    return stripe.PaymentMethod.retrieve(payment_method_id)


def attach_payment_method(customer_id: str, payment_method_id: str) -> None:
    _configure_stripe()
    try:
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
    except stripe.error.InvalidRequestError as e:
        err = (e.user_message or str(e) or '').lower()
        if 'already been attached' in err or 'already attached' in err:
            return
        raise


def detach_payment_method(payment_method_id: str) -> None:
    _configure_stripe()
    stripe.PaymentMethod.detach(payment_method_id)


def card_fields_from_pm(pm: Any) -> dict[str, Any]:
    if pm.type != 'card' or not pm.card:
        raise ValueError('Only Stripe card payment methods are supported.')
    c = pm.card
    return {
        'brand': c.brand or '',
        'last4': c.last4 or '',
        'exp_month': c.exp_month,
        'exp_year': c.exp_year,
        'funding': c.funding or '',
    }


def _ensure_default_for_holder_role(user_id: int, holder_role: str) -> None:
    from apps.payment.models import SavedCard

    active = SavedCard.objects.filter(
        user_id=user_id, holder_role=holder_role, is_active=True
    )
    if not active.exists():
        return
    if active.filter(is_default=True).exists():
        return
    newest = active.order_by('-created_at').first()
    SavedCard.objects.filter(pk=newest.pk).update(is_default=True)


def save_card_for_user(
    user: 'CustomUser',
    *,
    payment_method_id: str,
    holder_role: str,
    nickname: str,
    is_default: bool | None,
) -> Any:
    from apps.payment.models import SavedCard

    customer_id = get_or_create_stripe_customer_id(user)

    existing = SavedCard.objects.filter(
        stripe_payment_method_id=payment_method_id
    ).first()
    if existing and existing.user_id != user.id:
        raise ValueError('This payment method belongs to another account.')
    if existing and existing.user_id == user.id and existing.is_active:
        raise ValueError('This card is already saved.')

    pm = retrieve_payment_method(payment_method_id)
    card_fields = card_fields_from_pm(pm)
    attach_payment_method(customer_id, payment_method_id)
    pm = retrieve_payment_method(payment_method_id)
    card_fields = card_fields_from_pm(pm)

    with transaction.atomic():
        active_same_role = SavedCard.objects.filter(
            user=user, holder_role=holder_role, is_active=True
        )
        if existing:
            active_same_role = active_same_role.exclude(pk=existing.pk)

        if is_default is None:
            make_default = not active_same_role.exists()
        else:
            make_default = bool(is_default)

        if make_default:
            SavedCard.objects.filter(
                user=user, holder_role=holder_role, is_default=True
            ).update(is_default=False)

        if existing:
            obj = SavedCard.objects.select_for_update().get(pk=existing.pk)
        else:
            obj = SavedCard(
                user=user,
                stripe_payment_method_id=payment_method_id,
            )

        obj.user = user
        obj.holder_role = holder_role
        obj.stripe_customer_id = customer_id
        obj.nickname = nickname
        obj.is_active = True
        obj.is_default = make_default
        for k, v in card_fields.items():
            setattr(obj, k, v)
        obj.save()

        _ensure_default_for_holder_role(user.id, holder_role)

    return obj


def update_saved_card(
    obj: Any,
    *,
    nickname: Any = _MISSING,
    is_default: Any = _MISSING,
) -> Any:
    from apps.payment.models import SavedCard

    with transaction.atomic():
        obj = SavedCard.objects.select_for_update().get(pk=obj.pk)

        if is_default is True:
            SavedCard.objects.filter(
                user_id=obj.user_id,
                holder_role=obj.holder_role,
                is_default=True,
            ).exclude(pk=obj.pk).update(is_default=False)
            obj.is_default = True
        elif is_default is False:
            obj.is_default = False

        if nickname is not _MISSING:
            obj.nickname = nickname
        obj.save()

    _ensure_default_for_holder_role(obj.user_id, obj.holder_role)
    obj.refresh_from_db()
    return obj


def soft_delete_saved_card(obj: Any) -> None:
    from apps.payment.models import SavedCard

    try:
        detach_payment_method(obj.stripe_payment_method_id)
    except stripe.error.StripeError as e:
        logger.warning(
            'Stripe detach failed for pm=%s: %s', obj.stripe_payment_method_id, e
        )

    holder_role = obj.holder_role
    user_id = obj.user_id

    with transaction.atomic():
        obj = SavedCard.objects.select_for_update().get(pk=obj.pk)
        was_default = obj.is_default
        obj.is_active = False
        obj.is_default = False
        obj.save()
        if was_default:
            next_card = (
                SavedCard.objects.filter(
                    user_id=user_id,
                    holder_role=holder_role,
                    is_active=True,
                )
                .order_by('-created_at')
                .first()
            )
            if next_card:
                SavedCard.objects.filter(pk=next_card.pk).update(is_default=True)

    _ensure_default_for_holder_role(user_id, holder_role)
