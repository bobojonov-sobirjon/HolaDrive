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
            send_mail(
                subject='Verification Code',
                message=f'Your verification code is: {verification_code.code}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            success = True
        except Exception as e:
            error = str(e)
            success = False
    
    elif phone_number:
        message = f'Your verification code is: {verification_code.code}'
        success, sms_error = send_sms(phone_number, message)
        if not success:
            error = sms_error
    
    return verification_code, success, error
