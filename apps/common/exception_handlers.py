"""DRF exception handler overrides."""
from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def holadrive_exception_handler(exc, context):
    """
    Never let UnicodeDecodeError bubble to middleware as a raw 500.
    Login/OTP flows must return a usable JSON body instead.
    """
    if isinstance(exc, UnicodeDecodeError):
        return Response(
            {
                'message': 'Failed to read request or email settings text encoding',
                'status': 'error',
                'errors': {
                    'encoding': [
                        'Use UTF-8 JSON. On the server, re-save .env EMAIL_HOST_PASSWORD '
                        'and DEFAULT_FROM_EMAIL as plain UTF-8 (no smart quotes).'
                    ]
                },
            },
            status=500,
        )

    return drf_exception_handler(exc, context)
