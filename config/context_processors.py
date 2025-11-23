"""
Custom context processors for Django templates
"""
from django.conf import settings


def websocket_url(request):
    """
    Add websocket_url to all template contexts
    """
    # Get WEBSOCKET_URL from settings
    websocket_url_value = getattr(settings, 'WEBSOCKET_URL', None)
    
    # If WEBSOCKET_URL is not set or empty, construct it from HOST and PORT
    if not websocket_url_value:
        websocket_host = getattr(settings, 'WEBSOCKET_HOST', None)
        websocket_port = getattr(settings, 'WEBSOCKET_PORT', None)
        if websocket_host and websocket_port:
            websocket_url_value = f'{websocket_host}:{websocket_port}'
        else:
            # Fallback to request host if nothing is configured
            websocket_url_value = request.get_host()
    
    return {
        'websocket_url': websocket_url_value
    }

