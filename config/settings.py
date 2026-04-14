import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    # Load .env file from BASE_DIR explicitly
    env_path = BASE_DIR / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    load_dotenv = None

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-only-key-change-in-production')

DEBUG = True

ALLOWED_HOSTS = ['*']

# WebSocket Configuration
WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', None)
WEBSOCKET_PORT = os.getenv('WEBSOCKET_PORT', None)
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', f'{WEBSOCKET_HOST}:{WEBSOCKET_PORT}')



# Application definition

LOCAL_APPS = [
    'apps.accounts',
    'apps.order',
    'apps.payment',
    'apps.notification',
    'apps.chat',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'corsheaders',
    'django_filters',
    *LOCAL_APPS,
]

INSTALLED_APPS = [
    'nested_admin',
    'jazzmin',
    "daphne",
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ckeditor',
    'channels',
    *THIRD_PARTY_APPS,
]

LOCAL_MIDDLEWARE = [
    'config.middleware.middleware.JsonErrorResponseMiddleware',
    'config.middleware.middleware.Custom404Middleware',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    *LOCAL_MIDDLEWARE,
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'config.context_processors.websocket_url',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'holo-drive'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', '0576'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Toronto'

USE_I18N = True

USE_TZ = True



STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = os.getenv('MEDIA_ROOT', '/var/www/media')

# Prepended to MEDIA paths in WebSocket/API payloads (e.g. https://api.example.com — no trailing slash)
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Full',
        'height': 320,
        'width': '100%',
    },
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FileUploadParser",
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/minute',
        'user': '1000/minute',
        'login': '5/minute',
        'order_create': '30/minute',
        'burst': '60/minute',
        'sustained': '1000/day',
    },
    "PAGE_SIZE": 100,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Hola Drive and Hola Driver APIs',
    'DESCRIPTION': 'Hola Drive and Hola Driver APIs - JWT Authentication Required',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': r'/api/v1',
    'COMPONENT_SPLIT_REQUEST': True,
    # Swagger UI: guruhlar tartibi va qisqa tushuntirish (tags alfavit emas, shu ro‘yxat bo‘yicha).
    'TAGS': [
        {'name': 'Rider: Orders', 'description': 'Buyurtma yaratish, ro‘yxat, bitta order, bekor qilish, qo‘shimcha yo‘lovchi, jadval.'},
        {'name': 'Rider: Preferences', 'description': 'Buyurtma oldidan saqlanadigan rider sozlamalari (pre-order).'},
        {'name': 'Rider: Pricing', 'description': 'Narx baholash va reja bosqichida narxni tekshirish.'},
        {'name': 'Rider: Order items', 'description': 'Buyurtma ichidagi stop/narx/ride type tahriri.'},
        {'name': 'Rider: Active ride', 'description': 'Aktiv safarni qayta yuklash (resume) uchun bitta GET.'},
        {'name': 'Rider: Live tracking', 'description': 'Rider: tayinlangan haydovchi lokatsiyasi (HTTP). WebSocket: ws/order/{id}/tracking/.'},
        {'name': 'Driver: Orders & trips', 'description': 'Takliflar, qabul/rad, pickup, tugatish, haydovchi bekor, aktiv safar.'},
        {'name': 'Driver: Location', 'description': 'Haydovchi GPS yangilashi (real-time tracking uchun).'},
        {'name': 'Driver: Earnings & wallet', 'description': 'Dashboard, daromad, tarix, naqd chiqarish.'},
        {'name': 'Driver: Availability', 'description': 'Onlayn / oflayn holat.'},
        {'name': 'Trip ratings', 'description': 'Safar tugagach baholash va feedback teglari.'},
        {'name': 'Trip chat', 'description': 'Buyurtma bo‘yicha rider va haydovchi chat (HTTP).'},
    ],
    # Test uchun: Authorize qilingan JWT Swagger sahifasini yangilaganda saqlanadi (browser localStorage).
    # O‘chirish: SWAGGER_UI_SETTINGS blokini olib tashlang yoki brauzerda localStorage tozalang.
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
]

_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8000,http://127.0.0.1:5173')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins.split(',') if origin.strip()]

CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'
CORS_ALLOW_CREDENTIALS = True

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_USER_MODEL = 'accounts.CustomUser'

SITE_ID = 1

# -----------------------------------------------------------------------------
# Django Jazzmin — admin UI (https://github.com/farridav/django-jazzmin)
# Branding aligns with Hola Drive / Hola Driver (dark + warm accent).
# -----------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    'site_title': 'Hola Drive Admin',
    'site_header': 'Hola Drive',
    'site_brand': 'Hola Drive',
    'welcome_sign': 'Sign in to manage riders, drivers, orders, and content.',
    'copyright': 'Hola Drive',
    'search_model': [
        'accounts.RiderUser',
        'accounts.DriverUser',
        'order.Order',
    ],
    'user_avatar': None,
    'topmenu_links': [
        {'name': 'Dashboard', 'url': 'admin:index', 'permissions': ['auth.view_user']},
        {
            'name': 'Swagger',
            'url': '/swagger/',
            'new_window': True,
            'icon': 'fas fa-book',
            'permissions': ['auth.view_user'],
        },
        {
            'name': 'API schema',
            'url': '/api/schema/',
            'new_window': True,
            'icon': 'fas fa-code',
            'permissions': ['auth.view_user'],
        },
    ],
    'usermenu_links': [
        {'model': 'accounts.rideruser'},
        {'model': 'accounts.driveruser'},
    ],
    'show_sidebar': True,
    'navigation_expanded': False,
    'hide_apps': [],
    'hide_models': [
        'sites.site',
    ],
    'order_with_respect_to': [
        'accounts',
        'order',
        'chat',
        'notification',
        'auth',
        'sites',
    ],
    'custom_links': {
        'order': [
            {
                'name': 'Order preferences API',
                'url': '/api/v1/order/preferences/',
                'icon': 'fas fa-sliders-h',
                'new_window': True,
            }
        ],
    },
    'icons': {
        'auth': 'fas fa-key',
        'auth.group': 'fas fa-users-cog',
        'accounts.rideruser': 'fas fa-user',
        'accounts.driveruser': 'fas fa-id-badge',
        'accounts.verificationcode': 'fas fa-shield-alt',
        'accounts.userpreferences': 'fas fa-cog',
        'accounts.driverpreferences': 'fas fa-taxi',
        'accounts.vehicledetails': 'fas fa-car-side',
        'accounts.vehicleimages': 'fas fa-images',
        'accounts.driververification': 'fas fa-clipboard-check',
        'accounts.driveridentificationuploadtype': 'fas fa-cloud-upload-alt',
        'accounts.driveridentificationlegaltype': 'fas fa-balance-scale',
        'accounts.driveridentificationregistrationtype': 'fas fa-clipboard-list',
        'accounts.driveridentificationtermstype': 'fas fa-file-contract',
        'accounts.userdevicetoken': 'fas fa-mobile-alt',
        'accounts.invitationgenerate': 'fas fa-paper-plane',
        'accounts.invitationusers': 'fas fa-user-plus',
        'accounts.pinverificationforuser': 'fas fa-lock',
        'order.order': 'fas fa-route',
        'order.orderitem': 'fas fa-list-ul',
        'order.orderpreferences': 'fas fa-sliders-h',
        'order.additionalpassenger': 'fas fa-user-friends',
        'order.orderdriver': 'fas fa-car',
        'order.cancelorder': 'fas fa-ban',
        'order.ridetype': 'fas fa-tag',
        'order.surgepricing': 'fas fa-chart-line',
        'order.orderpaymentsplit': 'fas fa-money-bill-wave',
        'order.promocode': 'fas fa-percent',
        'order.orderpromocode': 'fas fa-ticket-alt',
        'order.ratingfeedbacktag': 'fas fa-comment-dots',
        'order.triprating': 'fas fa-star',
        'order.driverriderrating': 'fas fa-star-half-alt',
        'order.drivercashout': 'fas fa-wallet',
        'chat.chatroom': 'fas fa-comments',
        'chat.chatmessage': 'fas fa-comment',
        'notification.notification': 'fas fa-bell',
    },
    'default_icon_parents': 'fas fa-folder',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': True,
    'custom_css': 'admin/css/jazzmin_sidebar_multiline.css',
    'custom_js': None,
    'use_google_fonts_cdn': True,
    'show_ui_builder': False,
    'show_theme_chooser': True,
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {
        'accounts.driveruser': 'collapsible',
        'accounts.rideruser': 'collapsible',
        'order.order': 'horizontal_tabs',
    },
    'language_chooser': False,
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': 'navbar-orange',
    'accent': 'accent-warning',
    'navbar': 'navbar-dark',
    'no_navbar_border': False,
    'navbar_fixed': True,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-dark-primary',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': True,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': False,
    'theme': 'darkly',
    'default_theme_mode': 'dark',
    'button_classes': {
        'primary': 'btn-warning',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
    'actions_sticky_top': True,
}

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', '')

FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY', '')


TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')


# Django Channels Configuration
ASGI_APPLICATION = 'config.asgi.application'

# Channel Layers Configuration
# InMemoryChannelLayer - Redis o'rnatilmagan bo'lsa ishlatiladi
# Real-time new_order/order_timeout (Celery dan) uchun Redis kerak: pip install channels-redis
# Redis o'rnatilgan bo'lsa default=true. O'chirish uchun CHANNEL_LAYERS_REDIS=false
# Redis 5.0 dan eski bo'lsa RedisChannelLayer "BZPOPMIN" xatosi beradi — RedisPubSubChannelLayer ishlatamiz
_use_redis = os.getenv('CHANNEL_LAYERS_REDIS', 'true').lower() == 'true'
_channel_backend = (
    'channels_redis.pubsub.RedisPubSubChannelLayer'  # Redis 4.x ham ishlaydi (BZPOPMIN kerak emas)
    if _use_redis
    else None
)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': _channel_backend or 'channels.layers.InMemoryChannelLayer',
        'CONFIG': {'hosts': [os.getenv('REDIS_URL', 'redis://localhost:6379/1')]} if _channel_backend else {},
    } if _use_redis else {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
    except Exception:
        pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.accounts': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.notification': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.order': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'config.middleware': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

if os.path.exists(LOGS_DIR):
    LOGGING['handlers']['file'] = {
        'class': 'logging.FileHandler',
        'filename': os.path.join(LOGS_DIR, 'django.log'),
        'formatter': 'verbose',
    }
    LOGGING['loggers']['django']['handlers'].append('file')
    LOGGING['loggers']['apps.accounts']['handlers'].append('file')
    LOGGING['loggers']['apps.notification']['handlers'].append('file')
    LOGGING['loggers']['apps.order']['handlers'].append('file')
    LOGGING['loggers']['config.middleware']['handlers'].append('file')

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
