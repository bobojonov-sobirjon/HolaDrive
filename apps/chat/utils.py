from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
import base64
import logging
import uuid
from datetime import datetime
import os

logger = logging.getLogger(__name__)

_support_user_cache = None


def get_support_admin_random():
    """
    Pick a random support admin from Django Group 'Admin'.
    Falls back to get_support_user() if group is empty/not configured.
    """
    try:
        from django.contrib.auth.models import Group
        from apps.accounts.models import CustomUser

        g = Group.objects.filter(name='Admin').first()
        if g:
            qs = (
                CustomUser.objects.filter(groups=g, is_active=True)
                .filter(models.Q(is_staff=True) | models.Q(is_superuser=True))
                .order_by('?')
            )
            u = qs.first()
            if u:
                return u
    except Exception:
        logger.exception('Failed to pick random support admin')
    return get_support_user()


def get_support_user():
    """
    Resolve the support mailbox user. Never creates accounts or resets passwords.
    """
    global _support_user_cache

    if _support_user_cache is not None:
        try:
            _support_user_cache.refresh_from_db()
            if _support_user_cache.is_active:
                return _support_user_cache
        except Exception:
            _support_user_cache = None

    from django.conf import settings
    from apps.accounts.models import CustomUser

    email = (getattr(settings, 'SUPPORT_USER_EMAIL', '') or '').strip()
    if email:
        user = CustomUser.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            logger.error('SUPPORT_USER_EMAIL %s is not an active user', email)
        _support_user_cache = user
        return user

    user = (
        CustomUser.objects.filter(is_superuser=True, is_active=True)
        .order_by('id')
        .first()
    )
    _support_user_cache = user
    return user


def save_base64_file(base64_string, file_type='file', file_name=None):
    """
    Save base64 encoded file to storage
    
    Args:
        base64_string: Base64 encoded file string (with or without data URI prefix)
        file_type: Type of file ('image', 'file', 'audio')
        file_name: Original file name (optional)
    
    Returns:
        tuple: (file_path, file_name) - Path where file is saved and final file name
    """
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Remove whitespace and newlines
        base64_string = base64_string.strip().replace('\n', '').replace('\r', '').replace(' ', '')
        
        # Fix padding - base64 strings must be multiple of 4 characters
        # Add padding if needed
        missing_padding = len(base64_string) % 4
        if missing_padding:
            base64_string += '=' * (4 - missing_padding)
        
        file_data = base64.b64decode(base64_string, validate=True)
        
        if file_name:
            _, ext = os.path.splitext(file_name)
            if not ext:
                ext_map = {
                    'image': '.jpg',
                    'audio': '.mp3',
                    'file': '.bin'
                }
                ext = ext_map.get(file_type, '.bin')
        else:
            ext_map = {
                'image': '.jpg',
                'audio': '.mp3',
                'file': '.bin'
            }
            ext = ext_map.get(file_type, '.bin')
        
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_file_name = f"{timestamp}_{unique_id}{ext}"
        
        upload_path = f'chat/attachments/{file_type}/{final_file_name}'
        
        saved_path = default_storage.save(upload_path, ContentFile(file_data))
        
        return saved_path, final_file_name
        
    except Exception as e:
        raise ValueError(f"Error saving base64 file: {str(e)}")


def get_file_type_from_mime(mime_type):
    """
    Determine file_type from MIME type
    
    Args:
        mime_type: MIME type string (e.g., 'image/jpeg', 'audio/mpeg')
    
    Returns:
        str: File type ('image', 'file', 'audio')
    """
    if not mime_type:
        return 'file'
    
    mime_lower = mime_type.lower()
    
    if mime_lower.startswith('image/'):
        return 'image'
    elif mime_lower.startswith('audio/'):
        return 'audio'
    else:
        return 'file'


def get_file_type_from_extension(file_name):
    """
    Determine file_type from file extension
    
    Args:
        file_name: File name with extension
    
    Returns:
        str: File type ('image', 'file', 'audio')
    """
    if not file_name:
        return 'file'
    
    ext = os.path.splitext(file_name)[1].lower()
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
    
    if ext in image_extensions:
        return 'image'
    elif ext in audio_extensions:
        return 'audio'
    else:
        return 'file'
