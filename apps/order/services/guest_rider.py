"""
Book a ride for someone else (Switch rider).

Payer is always the logged-in user. Guest fields are who the driver picks up.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers

from apps.accounts.services import validate_phone_number
from apps.order.models import Order, SavedRider

logger = logging.getLogger(__name__)

BOOKED_FOR_ME = Order.BookedFor.ME
BOOKED_FOR_SOMEONE_ELSE = Order.BookedFor.SOMEONE_ELSE


def normalize_guest_fields(*, full_name, email=None, phone_number=None):
    name = (full_name or '').strip()
    if not name:
        raise serializers.ValidationError({'full_name': 'Full name is required.'})

    try:
        phone = validate_phone_number(phone_number, required=True)
    except ValueError as exc:
        raise serializers.ValidationError({'phone_number': str(exc)})

    email_clean = (email or '').strip().lower()
    if email_clean:
        try:
            validate_email(email_clean)
        except DjangoValidationError:
            raise serializers.ValidationError({'email': 'Enter a valid email address.'})
    return name, email_clean, phone


def upsert_saved_rider(owner, *, full_name, email, phone_number) -> SavedRider:
    rider, created = SavedRider.objects.get_or_create(
        owner=owner,
        phone_number=phone_number,
        defaults={
            'full_name': full_name,
            'email': email or '',
        },
    )
    if not created:
        rider.full_name = full_name
        if email:
            rider.email = email
        rider.save(update_fields=['full_name', 'email', 'updated_at'])
    return rider


def resolve_create_passenger(*, user, booked_for=None, saved_rider_id=None, guest=None, save_guest=True):
    """
    Return kwargs for Order.objects.create related to passenger.
    Empty booked_for + no guest = Me (backward compatible).
    """
    booked_for = (booked_for or '').strip().lower() or None
    guest = guest or None
    has_guest = bool(guest)
    has_saved = saved_rider_id is not None

    if booked_for == BOOKED_FOR_ME and (has_guest or has_saved):
        raise serializers.ValidationError(
            {'booked_for': 'Do not send guest or saved_rider_id when booked_for is me.'}
        )

    is_someone = (
        booked_for == BOOKED_FOR_SOMEONE_ELSE
        or (booked_for is None and (has_guest or has_saved))
    )
    if not is_someone:
        return {
            'booked_for': BOOKED_FOR_ME,
            'guest_full_name': '',
            'guest_email': '',
            'guest_phone_number': '',
            'saved_rider': None,
        }

    if has_guest and has_saved:
        raise serializers.ValidationError(
            {'guest': 'Send either saved_rider_id or guest, not both.'}
        )
    if not has_guest and not has_saved:
        raise serializers.ValidationError(
            {'guest': 'saved_rider_id or guest {full_name, phone_number} is required.'}
        )

    saved = None
    touch_saved = False
    upsert_guest = False
    if has_saved:
        saved = SavedRider.objects.filter(id=saved_rider_id, owner=user).first()
        if not saved:
            raise serializers.ValidationError({'saved_rider_id': 'Saved rider not found.'})
        name, email, phone = saved.full_name, saved.email or '', saved.phone_number
        touch_saved = True
    else:
        name, email, phone = normalize_guest_fields(
            full_name=guest.get('full_name'),
            email=guest.get('email'),
            phone_number=guest.get('phone_number'),
        )
        upsert_guest = bool(save_guest)

    return {
        'booked_for': BOOKED_FOR_SOMEONE_ELSE,
        'guest_full_name': name,
        'guest_email': email or '',
        'guest_phone_number': phone,
        'saved_rider': saved,
        '_touch_saved': touch_saved,
        '_upsert_guest': upsert_guest,
    }


def passenger_payload(order: Order) -> dict:
    user = getattr(order, 'user', None)
    booked_for = getattr(order, 'booked_for', None) or BOOKED_FOR_ME
    if booked_for == BOOKED_FOR_SOMEONE_ELSE and (
        order.guest_full_name or order.guest_phone_number
    ):
        return {
            'booked_for': BOOKED_FOR_SOMEONE_ELSE,
            'is_guest': True,
            'full_name': order.guest_full_name or '',
            'email': order.guest_email or None,
            'phone_number': order.guest_phone_number or None,
            'saved_rider_id': order.saved_rider_id,
        }
    return {
        'booked_for': BOOKED_FOR_ME,
        'is_guest': False,
        'full_name': (user.get_full_name() if user else '') or '',
        'email': (user.email if user else None) or None,
        'phone_number': (user.phone_number if user else None) or None,
        'saved_rider_id': None,
    }


def _pickup_dropoff(order: Order):
    item = order.order_items.order_by('stop_sequence', 'id').first()
    pickup = (item.address_from if item else '') or ''
    dropoff = (item.address_to if item else '') or ''
    return pickup, dropoff


def notify_guest_ride_booked(order: Order) -> None:
    if getattr(order, 'booked_for', None) != BOOKED_FOR_SOMEONE_ELSE:
        return
    phone = (order.guest_phone_number or '').strip()
    if not phone:
        return
    booker = order.user.get_full_name() if order.user else 'Someone'
    pickup, dropoff = _pickup_dropoff(order)
    code = order.order_code or f'#{order.id}'
    body = (
        f'{booker} booked you a Hola Drive ride ({code}). '
        f'Pickup: {pickup}. Dropoff: {dropoff}.'
    )
    _send_guest_sms(phone, body)


def notify_guest_driver_accepted(order: Order, *, pin_code: str | None = None) -> None:
    if getattr(order, 'booked_for', None) != BOOKED_FOR_SOMEONE_ELSE:
        return
    phone = (order.guest_phone_number or '').strip()
    if not phone:
        return
    booker = order.user.get_full_name() if order.user else 'Someone'
    code = order.order_code or f'#{order.id}'
    pin_part = f' PIN: {pin_code}.' if pin_code else ''
    body = (
        f'Hola Drive: a driver accepted the ride {booker} booked for you ({code}).'
        f'{pin_part}'
    )
    _send_guest_sms(phone, body)


def _send_guest_sms(phone: str, body: str) -> None:
    try:
        from apps.accounts.services import send_sms

        ok, err = send_sms(phone, body)
        if not ok:
            logger.warning('Guest ride SMS failed for %s: %s', phone, err)
    except Exception:
        logger.exception('Guest ride SMS error for %s', phone)
