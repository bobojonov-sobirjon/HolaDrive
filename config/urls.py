from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from pathlib import Path


def voice_call_test_page(_request):
    """Local HTML tester for rider/driver support calls (same-origin → no CORS)."""
    path = Path(settings.BASE_DIR) / 'voice_call_test.html'
    return FileResponse(path.open('rb'), content_type='text/html; charset=utf-8')


urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('voice-call-test/', voice_call_test_page, name='voice-call-test'),
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/admin-panel/', include('apps.admin_panel.urls')),
    path('api/v1/order/', include('apps.order.urls')),
    path('api/v1/payment/', include('apps.payment.urls')),
    path('api/v1/notification/', include('apps.notification.urls')),
    path('api/v1/chat/', include('apps.chat.urls')),
    path('api/v1/voice-call/', include('apps.voice_call.urls')),
    path('admin/', admin.site.urls),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
