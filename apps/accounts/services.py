import os
import re
from django.conf import settings
from django.core.mail import send_mail
from twilio.rest import Client


def normalize_phone_number(phone_number):
    if not phone_number:
        return phone_number
    cleaned = re.sub(r'[^\d+]', '', str(phone_number))
    if cleaned.startswith('+'):
        return cleaned
    return f'+{cleaned}'


def send_sms(phone_number, message):
    normalized_phone = normalize_phone_number(phone_number)
    
    try:
        account_sid = os.getenv('TWILIO_ACCOUNT_SID', settings.TWILIO_ACCOUNT_SID if hasattr(settings, 'TWILIO_ACCOUNT_SID') else None)
        auth_token = os.getenv('TWILIO_AUTH_TOKEN', settings.TWILIO_AUTH_TOKEN if hasattr(settings, 'TWILIO_AUTH_TOKEN') else None)
        from_number = os.getenv('TWILIO_PHONE_NUMBER', settings.TWILIO_PHONE_NUMBER if hasattr(settings, 'TWILIO_PHONE_NUMBER') else None)
        
        if not all([account_sid, auth_token, from_number]):
            return False, "Twilio credentials not configured"
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=normalized_phone
        )
        
        return True, message.sid
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


def send_verification_code(user, email=None, phone_number=None, code=None):
    import logging
    logger = logging.getLogger(__name__)
    
    from .models import VerificationCode
    
    logger.info(f"SEND_VERIFICATION_CODE DEBUG: Starting - User: {user.id}, Email: {email}, Phone: {phone_number}")
    
    verification_code = VerificationCode.objects.create(
        user=user,
        email=email,
        phone_number=phone_number
    )
    
    logger.info(f"SEND_VERIFICATION_CODE DEBUG: VerificationCode created - ID: {verification_code.id}, Code: {verification_code.code}")
    
    if code:
        verification_code.code = code
        verification_code.save()
        logger.info(f"SEND_VERIFICATION_CODE DEBUG: Code updated to: {code}")
    
    success = False
    error = None
    
    if email:
        logger.info(f"SEND_VERIFICATION_CODE DEBUG: Preparing to send email to: {email}")
        logger.info(f"SEND_VERIFICATION_CODE DEBUG: Email settings check:")
        logger.info(f"  - EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        logger.info(f"  - EMAIL_HOST: {settings.EMAIL_HOST}")
        logger.info(f"  - EMAIL_PORT: {settings.EMAIL_PORT}")
        logger.info(f"  - EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        logger.info(f"  - EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        logger.info(f"  - EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
        logger.info(f"  - DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        try:
            logger.info(f"SEND_VERIFICATION_CODE DEBUG: Calling send_mail()...")
            result = send_mail(
                subject='Verification Code',
                message=f'Your verification code is: {verification_code.code}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"SEND_VERIFICATION_CODE DEBUG: send_mail() returned: {result}")
            success = True
            logger.info(f"SEND_VERIFICATION_CODE DEBUG: Email sent successfully to {email}")
        except Exception as e:
            error = str(e)
            success = False
            logger.error(f"SEND_VERIFICATION_CODE DEBUG: Exception occurred: {type(e).__name__}: {error}")
            import traceback
            logger.error(f"SEND_VERIFICATION_CODE DEBUG: Traceback:\n{traceback.format_exc()}")
    
    elif phone_number:
        logger.info(f"SEND_VERIFICATION_CODE DEBUG: Preparing to send SMS to: {phone_number}")
        message = f'Your verification code is: {verification_code.code}'
        success, sms_error = send_sms(phone_number, message)
        if not success:
            error = sms_error
            logger.error(f"SEND_VERIFICATION_CODE DEBUG: SMS send failed: {error}")
        else:
            logger.info(f"SEND_VERIFICATION_CODE DEBUG: SMS sent successfully")
    
    logger.info(f"SEND_VERIFICATION_CODE DEBUG: Final result - Success: {success}, Error: {error}")
    return verification_code, success, error
