import os
import re
import logging

from django.conf import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)


def normalize_phone_number(phone_number):
    """Normalize to E.164-like form: leading '+' + digits only."""
    if not phone_number:
        return phone_number
    cleaned = re.sub(r'[^\d+]', '', str(phone_number).strip())
    if not cleaned:
        return phone_number
    if cleaned.startswith('+'):
        digits = re.sub(r'\D', '', cleaned)
        return f'+{digits}' if digits else phone_number
    digits = re.sub(r'\D', '', cleaned)
    return f'+{digits}' if digits else phone_number


def validate_phone_number(phone_number, *, required=False):
    """
    Validate international phone numbers (any country).
    Expects country code; stores as +XXXXXXXX (E.164-style, 8–15 digits).
    """
    if not phone_number or not str(phone_number).strip():
        if required:
            raise ValueError('Phone number is required.')
        return None

    normalized = normalize_phone_number(phone_number)
    digits = re.sub(r'\D', '', normalized or '')

    if not digits:
        raise ValueError('Invalid phone number format.')

    if len(digits) < 8 or len(digits) > 15:
        raise ValueError(
            'Phone number must include country code and be 8-15 digits '
            '(example: +1 514 555 1234 or +998 90 123 45 67).'
        )

    return f'+{digits}'


def phone_already_taken(phone_number, *, exclude_user_id=None) -> bool:
    """True if another user already has this phone (normalized or raw)."""
    from .models import CustomUser
    from .phone_auth import find_user_by_phone

    normalized = normalize_phone_number(phone_number)
    if not normalized:
        return False

    existing = find_user_by_phone(normalized)
    if existing and (exclude_user_id is None or existing.pk != exclude_user_id):
        return True

    digits = re.sub(r'\D', '', normalized)
    qs = CustomUser.objects.exclude(phone_number__isnull=True).exclude(phone_number='')
    if exclude_user_id is not None:
        qs = qs.exclude(pk=exclude_user_id)
    for other in qs.only('id', 'phone_number').iterator():
        if re.sub(r'\D', '', other.phone_number or '') == digits:
            return True
    return False


def email_already_taken(email, *, exclude_user_id=None) -> bool:
    from .models import CustomUser

    email = (email or '').strip().lower()
    if not email:
        return False
    qs = CustomUser.objects.filter(email__iexact=email)
    if exclude_user_id is not None:
        qs = qs.exclude(pk=exclude_user_id)
    return qs.exists()


def validate_canadian_tax_number(value, *, field_label='Tax number'):
    """GST/HST or TVQ — digits and letters, 9–15 chars after cleanup."""
    if value is None or not str(value).strip():
        return None
    cleaned = re.sub(r'[\s\-]', '', str(value).strip()).upper()
    if len(cleaned) < 9 or len(cleaned) > 15:
        raise ValueError(f'{field_label} must be 9–15 characters.')
    if not re.fullmatch(r'[A-Z0-9]+', cleaned):
        raise ValueError(f'{field_label} may contain letters and digits only.')
    return cleaned


def _twilio_credentials():
    account_sid = (os.getenv('TWILIO_ACCOUNT_SID') or getattr(settings, 'TWILIO_ACCOUNT_SID', None) or '').strip() or None
    auth_token = (os.getenv('TWILIO_AUTH_TOKEN') or getattr(settings, 'TWILIO_AUTH_TOKEN', None) or '').strip() or None
    from_number = (os.getenv('TWILIO_PHONE_NUMBER') or getattr(settings, 'TWILIO_PHONE_NUMBER', None) or '').strip() or None
    return account_sid, auth_token, from_number


def send_sms(phone_number, message):
    normalized_phone = normalize_phone_number(phone_number)

    if getattr(settings, 'SMS_OTP_LOG_ONLY', False):
        logger.warning(
            '[SMS_OTP_LOG_ONLY] OTP SMS to %s (not sent via Twilio): %s',
            normalized_phone,
            message,
        )
        return True, 'log_only'

    try:
        account_sid, auth_token, from_number = _twilio_credentials()

        if not all([account_sid, auth_token, from_number]):
            logger.error(
                'Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env'
            )
            return False, 'Twilio credentials not configured'

        client = Client(account_sid, auth_token)

        twilio_message = client.messages.create(
            body=message,
            from_=from_number,
            to=normalized_phone,
        )

        return True, twilio_message.sid
    except Exception as e:
        error_message = str(e)

        if '21408' in error_message or 'Permission to send an SMS has not been enabled' in error_message:
            return False, "SMS sending is not enabled for this region. Please enable international SMS in your Twilio account settings."

        elif '21211' in error_message or ('Invalid' in error_message and 'Phone Number' in error_message):
            return False, f"Invalid phone number format: {normalized_phone}. Please ensure the phone number is correct."

        elif '21608' in error_message or 'The number provided is not a valid mobile number' in error_message:
            return False, "The provided phone number is not a valid mobile number. Please provide a valid mobile number."

        elif '20003' in error_message or 'Authenticate' in error_message:
            return False, "Invalid Twilio credentials. Please check your Account SID and Auth Token."

        elif '20001' in error_message or 'Unauthorized' in error_message:
            return False, "Unauthorized access. Your Twilio credentials may be incorrect or expired."

        return False, error_message


def send_verification_code(user, email=None, phone_number=None, code=None, email_subject='Verification Code', email_message=None):
    """
    Store OTP and deliver via email (SMTP) or SMS (Twilio).
    Same escape hatch pattern as SMS: EMAIL_OTP_LOG_ONLY / SMS_OTP_LOG_ONLY.
    """
    import time
    from .models import VerificationCode
    from django.core.mail import send_mail

    t0 = time.monotonic()

    def _log(step: str, **extra):
        elapsed = round(time.monotonic() - t0, 3)
        parts = ' '.join(f'{k}={v}' for k, v in extra.items())
        msg = f'[OTP] step={step} elapsed_s={elapsed} {parts}'.strip()
        logger.warning(msg)
        print(msg, flush=True)

    _log(
        'start',
        user_id=getattr(user, 'pk', None),
        email=email or '-',
        phone=phone_number or '-',
        email_host=getattr(settings, 'EMAIL_HOST', ''),
        email_port=getattr(settings, 'EMAIL_PORT', ''),
        email_user=getattr(settings, 'EMAIL_HOST_USER', ''),
        timeout=getattr(settings, 'EMAIL_TIMEOUT', None),
        log_only=getattr(settings, 'EMAIL_OTP_LOG_ONLY', False),
        fallback=getattr(settings, 'EMAIL_OTP_FALLBACK_ON_ERROR', False),
        fixed_otp=bool(getattr(settings, 'FIXED_OTP_CODE', '') or ''),
    )

    fixed = (getattr(settings, 'FIXED_OTP_CODE', '') or '').strip()
    if fixed and not code:
        code = fixed

    verification_code = VerificationCode.objects.create(
        user=user,
        email=email,
        phone_number=phone_number
    )

    if code:
        verification_code.code = code
        verification_code.save(update_fields=['code'])

    _log('otp_created', code=verification_code.code, vc_id=verification_code.pk, fixed=bool(fixed))

    success = False
    error = None

    # SMTP blocked on VPS: skip email/SMS delivery, accept FIXED_OTP_CODE (e.g. 1111)
    if fixed:
        _log(
            'fixed_otp_skip_delivery',
            code=verification_code.code,
            channel='email' if email else ('sms' if phone_number else 'none'),
        )
        print(
            f'[OTP FIXED] code={verification_code.code} email={email or "-"} phone={phone_number or "-"}',
            flush=True,
        )
        return verification_code, True, None

    if email:
        subject = str(email_subject or 'Verification Code')
        if email_message:
            message_text = str(email_message.format(code=verification_code.code))
        else:
            message_text = f'Your verification code is: {verification_code.code}'

        from_email = (
            getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            or getattr(settings, 'EMAIL_HOST_USER', None)
            or ''
        )
        from_email = str(from_email).strip()
        to_email = str(email).strip()

        if getattr(settings, 'EMAIL_OTP_LOG_ONLY', False):
            _log('email_log_only_skip_smtp', to=to_email, code=verification_code.code)
            logger.warning(
                '[EMAIL_OTP_LOG_ONLY] OTP email to %s (not sent via SMTP): %s',
                to_email,
                message_text,
            )
            print(f'[OTP EMAIL_OTP_LOG_ONLY] to={to_email} code={verification_code.code}', flush=True)
            return verification_code, True, None

        try:
            if not from_email:
                _log('email_fail_no_from')
                return (
                    verification_code,
                    False,
                    'DEFAULT_FROM_EMAIL / EMAIL_HOST_USER is empty. Set them in .env',
                )

            # Hard timeout so nginx does not return 504 Gateway Time-out while SMTP hangs
            import socket

            timeout_s = int(getattr(settings, 'EMAIL_TIMEOUT', 15) or 15)
            old_timeout = socket.getdefaulttimeout()
            _log(
                'smtp_connect_begin',
                host=getattr(settings, 'EMAIL_HOST', ''),
                port=getattr(settings, 'EMAIL_PORT', ''),
                use_tls=getattr(settings, 'EMAIL_USE_TLS', None),
                from_email=from_email,
                to=to_email,
                socket_timeout_s=timeout_s,
            )
            socket.setdefaulttimeout(timeout_s)
            try:
                send_mail(
                    subject=subject,
                    message=message_text,
                    from_email=from_email,
                    recipient_list=[to_email],
                    fail_silently=False,
                )
            finally:
                socket.setdefaulttimeout(old_timeout)
            success = True
            _log('smtp_send_ok', to=to_email)
            logger.info('OTP email sent to %s', to_email)
        except Exception as e:
            error = str(e) or repr(e)
            success = False
            _log('smtp_send_fail', to=to_email, error_type=type(e).__name__, error=error)
            logger.exception('Failed to send verification email to %s', email)

            if getattr(settings, 'EMAIL_OTP_FALLBACK_ON_ERROR', False):
                logger.warning(
                    '[EMAIL_OTP_FALLBACK] to=%s code=%s error=%s',
                    email,
                    verification_code.code,
                    error,
                )
                print(
                    f'[OTP EMAIL_OTP_FALLBACK] to={email} code={verification_code.code}',
                    flush=True,
                )
                _log('email_fallback_ok', code=verification_code.code)
                success = True
                error = None
            else:
                # Clearer message for ops / Swagger (instead of hanging until nginx 504)
                if 'timed out' in error.lower() or 'timeout' in error.lower():
                    error = (
                        f'Email SMTP timed out after {getattr(settings, "EMAIL_TIMEOUT", 15)}s. '
                        'Check EMAIL_* on the server or set EMAIL_OTP_FALLBACK_ON_ERROR=true temporarily.'
                    )

    elif phone_number:
        _log('sms_begin', phone=phone_number)
        message = f'Your verification code is: {verification_code.code}'
        success, sms_error = send_sms(phone_number, message)
        if not success:
            error = sms_error
            _log('sms_fail', error=sms_error)
            logger.error('Failed to send verification SMS to %s: %s', phone_number, sms_error)
        else:
            _log('sms_ok')

    _log('done', success=success, error=error or '-')
    return verification_code, success, error
