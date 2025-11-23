"""
Custom context processors for Django templates
"""
from django.conf import settings


def websocket_url(request):
    """
    Add websocket_url to all template contexts
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Get WEBSOCKET_URL from settings
    websocket_url_value = getattr(settings, 'WEBSOCKET_URL', None)
    websocket_host = getattr(settings, 'WEBSOCKET_HOST', None)
    websocket_port = getattr(settings, 'WEBSOCKET_PORT', None)
    
    # Debug logging
    logger.warning(f"DEBUG context_processor: WEBSOCKET_URL={websocket_url_value}, HOST={websocket_host}, PORT={websocket_port}")
    
    # If WEBSOCKET_URL is not set or empty, construct it from HOST and PORT
    if not websocket_url_value:
        if websocket_host and websocket_port:
            websocket_url_value = f'{websocket_host}:{websocket_port}'
            logger.warning(f"DEBUG context_processor: Constructed URL from HOST:PORT = {websocket_url_value}")
        else:
            # Fallback to request host if nothing is configured
            websocket_url_value = request.get_host()
            logger.warning(f"DEBUG context_processor: Using request.get_host() = {websocket_url_value}")
    else:
        logger.warning(f"DEBUG context_processor: Using WEBSOCKET_URL from settings = {websocket_url_value}")
    
    return {
        'websocket_url': websocket_url_value
    }

