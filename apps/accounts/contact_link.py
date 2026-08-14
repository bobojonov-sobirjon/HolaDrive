"""
Attach email or phone to an existing authenticated account via OTP.
Flow: request OTP → confirm OTP → contact saved on user.
"""
from __future__ import annotations

from apps.accounts.models import CustomUser, VerificationCode
from apps.accounts.phone_auth import is_phone_signup_user
from apps.accounts.services import (
    email_already_taken,
    normalize_phone_number,
    phone_already_taken,
    send_verification_code,
    validate_phone_number,
)


class ContactLinkError(ValueError):
    def __init__(self, message: str, *, code: str = 'invalid', field: str | None = None):
        super().__init__(message)
        self.code = code
        self.field = field


def request_contact_link(*, user: CustomUser, email: str | None = None, phone_number: str | None = None):
    email = (email or '').strip().lower() or None
    phone_raw = (phone_number or '').strip() or None

    if bool(email) == bool(phone_raw):
        raise ContactLinkError(
            'Provide either email or phone_number (not both).',
            code='invalid_payload',
        )

    if phone_raw:
        try:
            phone = validate_phone_number(phone_raw, required=True)
        except ValueError as exc:
            raise ContactLinkError(str(exc), code='invalid_phone', field='phone_number') from exc

        current = normalize_phone_number(user.phone_number) if user.phone_number else None
        if current and current == phone:
            raise ContactLinkError(
                'This phone number is already on your account.',
                code='already_linked',
                field='phone_number',
            )
        if phone_already_taken(phone, exclude_user_id=user.pk):
            raise ContactLinkError(
                'This phone number is already linked to another account.',
                code='phone_taken',
                field='phone_number',
            )

        vc, success, error = send_verification_code(
            user,
            phone_number=phone,
            email_subject='Phone verification',
        )
        if not success:
            raise ContactLinkError(
                error or 'Failed to send verification SMS.',
                code='send_failed',
                field='phone_number',
            )
        return {
            'channel': 'phone',
            'sent_to': phone,
            'expires_at': vc.expires_at.isoformat() if vc.expires_at else None,
        }

    # email
    if email_already_taken(email, exclude_user_id=user.pk):
        # Allow replacing only when current email is a phone placeholder and email is free —
        # still block if another real account owns it (already checked).
        raise ContactLinkError(
            'This email is already linked to another account.',
            code='email_taken',
            field='email',
        )

    current_email = (user.email or '').strip().lower()
    if current_email == email and not is_phone_signup_user(user):
        raise ContactLinkError(
            'This email is already on your account.',
            code='already_linked',
            field='email',
        )

    vc, success, error = send_verification_code(
        user,
        email=email,
        email_subject='Confirm your email for HolaDrive',
        email_message='Your verification code to link this email is: {code}',
    )
    if not success:
        raise ContactLinkError(
            error or 'Failed to send verification email.',
            code='send_failed',
            field='email',
        )
    return {
        'channel': 'email',
        'sent_to': email,
        'expires_at': vc.expires_at.isoformat() if vc.expires_at else None,
    }


def confirm_contact_link(
    *,
    user: CustomUser,
    code: str,
    email: str | None = None,
    phone_number: str | None = None,
) -> CustomUser:
    email = (email or '').strip().lower() or None
    phone_raw = (phone_number or '').strip() or None
    code = (code or '').strip()

    if bool(email) == bool(phone_raw):
        raise ContactLinkError(
            'Provide either email or phone_number (not both).',
            code='invalid_payload',
        )
    if not code:
        raise ContactLinkError('Verification code is required.', code='invalid_code', field='code')

    if phone_raw:
        try:
            phone = validate_phone_number(phone_raw, required=True)
        except ValueError as exc:
            raise ContactLinkError(str(exc), code='invalid_phone', field='phone_number') from exc

        if phone_already_taken(phone, exclude_user_id=user.pk):
            raise ContactLinkError(
                'This phone number is already linked to another account.',
                code='phone_taken',
                field='phone_number',
            )

        vc = (
            VerificationCode.objects.filter(
                user=user,
                phone_number=phone,
                code=code,
                is_used=False,
            )
            .order_by('-created_at')
            .first()
        )
        # Also match if stored with slight format difference
        if not vc:
            candidates = VerificationCode.objects.filter(
                user=user,
                code=code,
                is_used=False,
                phone_number__isnull=False,
            ).order_by('-created_at')[:10]
            for row in candidates:
                if normalize_phone_number(row.phone_number) == phone:
                    vc = row
                    break

        if not vc or not vc.is_valid():
            raise ContactLinkError(
                'Invalid or expired verification code.',
                code='invalid_code',
                field='code',
            )

        vc.is_used = True
        vc.save(update_fields=['is_used'])
        user.phone_number = phone
        user.save(update_fields=['phone_number', 'updated_at'])
        return user

    if email_already_taken(email, exclude_user_id=user.pk):
        raise ContactLinkError(
            'This email is already linked to another account.',
            code='email_taken',
            field='email',
        )

    vc = (
        VerificationCode.objects.filter(
            user=user,
            email__iexact=email,
            code=code,
            is_used=False,
        )
        .order_by('-created_at')
        .first()
    )
    if not vc or not vc.is_valid():
        raise ContactLinkError(
            'Invalid or expired verification code.',
            code='invalid_code',
            field='code',
        )

    vc.is_used = True
    vc.save(update_fields=['is_used'])

    was_phone_signup = is_phone_signup_user(user)
    user.email = email
    update_fields = ['email', 'updated_at']
    if was_phone_signup or not user.is_verified:
        user.is_verified = True
        update_fields.append('is_verified')
    user.save(update_fields=update_fields)
    return user
