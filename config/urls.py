from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from rest_framework import permissions
from config.swagger_auth import SwaggerTokenView

schema_view: get_schema_view = get_schema_view(
    openapi.Info(
        title="Holo Drive APIs",
        default_version='v1',
        description="Holo Drive APIs - JWT Authentication Required",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
    patterns=[
        path('api/v1/accounts/', include('apps.accounts.urls')),
        path('api/v1/order/', include('apps.order.urls')),
        path('api/v1/payment/', include('apps.payment.urls')),
        path('api/v1/notification/', include('apps.notification.urls')),
        path('api/v1/chat/', include('apps.chat.urls')),
    ],
)

urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += [
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

urlpatterns += [
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/order/', include('apps.order.urls')),
    path('api/v1/payment/', include('apps.payment.urls')),
    path('api/v1/notification/', include('apps.notification.urls')),
    path('api/v1/chat/', include('apps.chat.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT, }, ), ]