from django.http import JsonResponse
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class JsonErrorResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        logger.exception('Unhandled exception on %s', getattr(request, 'path', ''))
        if isinstance(exception, UnicodeDecodeError):
            return JsonResponse(
                {
                    'message': 'Invalid text encoding in request or server settings.',
                    'status': 'error',
                },
                status=500,
            )
        return JsonResponse(
            {'message': 'Internal server error', 'status': 'error'},
            status=500,
        )


class Custom404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.path.startswith('/api/'):
            if response is None:
                return self.handle_404(request)

            if response.status_code == status.HTTP_404_NOT_FOUND:
                return self.handle_404(request)

        return response

    def handle_404(self, request):
        data = {"detail": "Page not Found"}
        return JsonResponse(data, status=status.HTTP_404_NOT_FOUND)
