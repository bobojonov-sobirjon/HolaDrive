"""
Custom context processors for Django templates
"""
from django.conf import settings


def websocket_url(request):
    """
    Add websocket_url to all template contexts
    """
    return {
        'websocket_url': getattr(settings, 'WEBSOCKET_URL', f"{request.get_host()}")
    }

