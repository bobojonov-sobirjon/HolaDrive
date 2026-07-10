"""
Hard-delete CustomUser so Google/Apple/phone can register again with the same identity.
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models.deletion import Collector

from apps.accounts.models import CustomUser

logger = logging.getLogger(__name__)


def _clear_identity_fields(user: CustomUser) -> None:
    """Free email / firebase_uid / phone so a new account can reuse them even if delete fails mid-way."""
    suffix = f'.deleted.{user.pk}.{user.updated_at.timestamp() if user.updated_at else user.pk}'
    updates = {
        'firebase_uid': None,
        'phone_number': None,
        'stripe_customer_id': '',
        'stripe_connect_account_id': '',
        'is_active': False,
        'is_online': False,
    }
    # Keep email unique but free the real address for re-registration
    if user.email and not user.email.endswith('@deleted.holadrive.local'):
        updates['email'] = f'deleted+{user.pk}@deleted.holadrive.local'
    if user.username:
        updates['username'] = f'deleted_{user.pk}_{user.username}'[:150]
    if user.id_identification:
        updates['id_identification'] = None
    CustomUser.objects.filter(pk=user.pk).update(**updates)


def _delete_related_blocking_rows(user: CustomUser) -> None:
    """
    Explicitly remove rows that commonly block user.delete() (orders as rider/driver, chats, etc.).
    CASCADE should handle most; this makes delete deterministic for admin hard-delete.
    """
    from apps.order.models import (
        DriverCashout,
        DriverRiderRating,
        DriverWalletBalance,
        DriverWalletTransaction,
        Order,
        OrderChat,
        OrderDriver,
        OrderPaymentSplit,
        OrderPromoCode,
        PromoCode,
        TripRating,
    )

    # Rider-owned orders (cascade children)
    Order.objects.filter(user=user).delete()

    # Driver assignment / cashout / wallet
    OrderDriver.objects.filter(driver=user).delete()
    DriverCashout.objects.filter(driver=user).delete()
    DriverWalletTransaction.objects.filter(driver=user).delete()
    DriverWalletBalance.objects.filter(driver=user).delete()

    # Ratings (both sides)
    TripRating.objects.filter(rider=user).delete()
    TripRating.objects.filter(driver=user).delete()
    DriverRiderRating.objects.filter(rider=user).delete()
    DriverRiderRating.objects.filter(driver=user).delete()

    # Order chat rooms
    OrderChat.objects.filter(rider=user).delete()
    OrderChat.objects.filter(driver=user).delete()

    # Payment splits / promo where user is referenced
    OrderPaymentSplit.objects.filter(user=user).delete()
    OrderPromoCode.objects.filter(applied_by=user).update(applied_by=None)
    PromoCode.objects.filter(user=user).delete()

    try:
        from apps.chat.models import ChatRoom, SupportRoom

        ChatRoom.objects.filter(initiator=user).delete()
        ChatRoom.objects.filter(receiver=user).delete()
        SupportRoom.objects.filter(user=user).delete()
        SupportRoom.objects.filter(admin=user).delete()
    except Exception as exc:
        logger.warning('hard_delete chat cleanup: %s', exc)

    try:
        from apps.voice_call.models import VoiceCallSession, SupportAgentDuty

        VoiceCallSession.objects.filter(caller=user).delete()
        VoiceCallSession.objects.filter(callee=user).update(callee=None)
        SupportAgentDuty.objects.filter(admin=user).delete()
    except Exception as exc:
        logger.warning('hard_delete voice_call cleanup: %s', exc)

    try:
        from apps.payment.models import SavedCard

        SavedCard.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning('hard_delete payment cleanup: %s', exc)


def hard_delete_user(user: CustomUser) -> dict[str, Any]:
    """
    Permanently remove a user and free Google/email/phone identity for re-registration.

    Returns snapshot of deleted identity fields.
    Raises IntegrityError if the row still cannot be removed after cleanup.
    """
    snapshot = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'full_name': user.get_full_name(),
        'firebase_uid': user.firebase_uid or None,
        'phone_number': user.phone_number or None,
    }

    with transaction.atomic():
        # Refresh under lock
        user = CustomUser.objects.select_for_update().get(pk=user.pk)

        _delete_related_blocking_rows(user)

        # Free identity before final delete so concurrent Google login cannot reattach
        _clear_identity_fields(user)
        user.refresh_from_db()

        try:
            user.delete()
        except IntegrityError:
            # Last resort: Django collector (same as admin delete cascade)
            collector = Collector(using='default')
            collector.collect([user])
            collector.delete()

        # Ensure no leftover row with same identity
        leftover = CustomUser.objects.filter(pk=snapshot['id']).exists()
        if leftover:
            raise IntegrityError('User row still exists after hard delete.')

        if snapshot['email']:
            still = CustomUser.objects.filter(email__iexact=snapshot['email']).exists()
            if still:
                CustomUser.objects.filter(email__iexact=snapshot['email']).update(
                    email=f"deleted+stale+{snapshot['id']}@deleted.holadrive.local",
                    firebase_uid=None,
                    phone_number=None,
                    is_active=False,
                )

        if snapshot['firebase_uid']:
            CustomUser.objects.filter(firebase_uid=snapshot['firebase_uid']).update(
                firebase_uid=None,
                is_active=False,
            )

    logger.info(
        'Hard-deleted user id=%s email=%s firebase_uid=%s',
        snapshot['id'],
        snapshot['email'],
        snapshot['firebase_uid'],
    )
    return snapshot
