import os
import re
import logging

from django.conf import settings
from django.core.mail import send_mail
from twilio.rest import Client

logger = logging.getLogger(__name__)


def normalize_phone_number(phone_number):
    if not phone_number:
        return phone_number
    cleaned = re.sub(r'[^\d+]', '', str(phone_number))
    if cleaned.startswith('+'):
        return cleaned
    return f'+{cleaned}'


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
    from .models import VerificationCode

    verification_code = VerificationCode.objects.create(
        user=user,
        email=email,
        phone_number=phone_number
    )

    if code:
        verification_code.code = code
        verification_code.save()

    success = False
    error = None

    if email:
        try:
            if email_message:
                message_text = email_message.format(code=verification_code.code)
            else:
                message_text = f'Your verification code is: {verification_code.code}'
            send_mail(
                subject=email_subject,
                message=message_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            success = True
        except Exception as e:
            error = str(e)
            success = False
            logger.exception("Failed to send verification email to %s", email)

    elif phone_number:
        message = f'Your verification code is: {verification_code.code}'
        success, sms_error = send_sms(phone_number, message)
        if not success:
            error = sms_error
            logger.error("Failed to send verification SMS to %s: %s", phone_number, sms_error)

    return verification_code, success, error
