from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import base64
import uuid
from datetime import datetime
import os


# Cache for support user to avoid repeated database queries
_support_user_cache = None

def get_support_user():
    """
    Get or create the support user (admin@admin.com)
    Uses caching to avoid repeated database queries
    """
    global _support_user_cache
    
    # Return cached user if available
    if _support_user_cache is not None:
        try:
            # Verify user still exists
            _support_user_cache.refresh_from_db()
            return _support_user_cache
        except Exception:
            # User was deleted, clear cache
            _support_user_cache = None
    
    from apps.accounts.models import CustomUser
    
    try:
        support_user, created = CustomUser.objects.get_or_create(
            email='admin@admin.com',
            defaults={
                'username': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created or not support_user.check_password('1'):
            support_user.set_password('1')
            support_user.save()
        
        # Cache the user
        _support_user_cache = support_user
        return support_user
    except Exception as e:
        print(f"❌ Error getting support user: {e}")
        import traceback
        traceback.print_exc()
        return None


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
