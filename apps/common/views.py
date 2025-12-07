"""
Base async APIView class for Django REST Framework
This class properly handles async methods in DRF views
"""
import inspect
from asgiref.sync import sync_to_async
from rest_framework.views import APIView


class AsyncAPIView(APIView):
    """
    Async version of APIView that properly handles async methods
    """
    
    async def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to properly handle async methods
        """
        self.args = args
        self.kwargs = kwargs
        request = await sync_to_async(self.initialize_request)(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            await sync_to_async(self.initial)(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            # Check if handler is async
            if inspect.iscoroutinefunction(handler):
                response = await handler(request, *args, **kwargs)
            else:
                response = await sync_to_async(handler)(request, *args, **kwargs)

        except Exception as exc:
            response = await sync_to_async(self.handle_exception)(exc)

        self.response = await sync_to_async(self.finalize_response)(request, response, *args, **kwargs)
        return self.response

