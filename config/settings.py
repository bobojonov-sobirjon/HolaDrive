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
    'apps.admin_panel',
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
    "daphne",
    'django.contrib.admin',
    'django.contrib.sites',
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
    'TITLE': 'Hola Drive API',
    'DESCRIPTION': (
        'REST API for Hola Drive (rider) and Hola Driver mobile apps, plus the React admin panel. '
        'Authenticate with JWT (Bearer). WebSocket paths are documented in endpoint descriptions where relevant.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': r'/api/v1',
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Rider: Orders', 'description': 'Create, list, detail, cancel, extra passengers, and scheduling.'},
        {'name': 'Rider: Preferences', 'description': 'Pre-order rider preference profile.'},
        {'name': 'Rider: Pricing', 'description': 'Price estimates and pre-order price validation.'},
        {'name': 'Rider: Order items', 'description': 'Stops, price, and ride type updates on an order.'},
        {'name': 'Rider: Active ride', 'description': 'Resume the rider’s current in-progress trip.'},
        {'name': 'Rider: Live tracking', 'description': 'Assigned driver location (HTTP). WebSocket: ws/order/{id}/tracking/.'},
        {'name': 'Driver: Orders & trips', 'description': 'Offers, accept/reject, pickup, complete, cancel, active trip.'},
        {'name': 'Driver: Location', 'description': 'Driver GPS updates for live tracking.'},
        {'name': 'Driver: Earnings & wallet', 'description': 'Dashboard, earnings, history, and cash-out requests.'},
        {'name': 'Driver: Availability', 'description': 'Online / offline status.'},
        {'name': 'Admin Panel', 'description': 'React admin panel: drivers, riders, orders, cash-outs, analytics.'},
        {'name': 'Trip ratings', 'description': 'Post-trip ratings and feedback tags.'},
        {'name': 'Trip chat', 'description': 'Order-scoped rider–driver chat (HTTP).'},
        {'name': 'Payment: Saved cards', 'description': 'Stripe saved cards (rider/driver): GET/POST/PUT/DELETE.'},
        {'name': 'Payment: Stripe', 'description': 'Stripe Customer id (cus_) for riders.'},
        {'name': 'Stripe — Driver', 'description': 'Stripe Connect: bank account, balance, checkout history.'},
    ],
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
    "http://localhost:5173", 
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "https://localhost:3000",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
    "https://127.0.0.1:5174",
    "https://hola-admin-nu.vercel.app",
]

_cors_origins = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174,'
    'https://localhost:3000,https://localhost:5173,https://127.0.0.1:5173,https://127.0.0.1:5174,https://hola-admin-nu.vercel.app'
)
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins.split(',') if origin.strip()]

CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'
CORS_ALLOW_CREDENTIALS = True

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_USER_MODEL = 'accounts.CustomUser'

SITE_ID = 1

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

# Stripe (saved cards, payments). Keys from https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
# Trip card charges (PaymentIntent): ISO currency, platform fee % when using Stripe Connect destination
STRIPE_CHARGE_CURRENCY = os.getenv('STRIPE_CHARGE_CURRENCY', 'cad').strip().lower() or 'cad'
STRIPE_APPLICATION_FEE_PERCENT = os.getenv('STRIPE_APPLICATION_FEE_PERCENT', '0').strip() or '0'

# Stripe Connect (driver payouts) — see docs/STRIPE_HolaDrive_INTEGRATION.md
STRIPE_CONNECT_ACCOUNT_TYPE = os.getenv('STRIPE_CONNECT_ACCOUNT_TYPE', 'custom').strip().lower() or 'custom'
STRIPE_CONNECT_COUNTRY = os.getenv('STRIPE_CONNECT_COUNTRY', 'US').strip().upper() or 'US'
STRIPE_CONNECT_PAYOUT_INTERVAL = os.getenv('STRIPE_CONNECT_PAYOUT_INTERVAL', 'weekly').strip().lower() or 'weekly'
STRIPE_CONNECT_PAYOUT_WEEKLY_ANCHOR = os.getenv('STRIPE_CONNECT_PAYOUT_WEEKLY_ANCHOR', 'monday').strip().lower() or 'monday'
STRIPE_CONNECT_PAYOUT_DELAY_DAYS = os.getenv('STRIPE_CONNECT_PAYOUT_DELAY_DAYS', '').strip()
STRIPE_CONNECT_APPLY_PAYOUT_SCHEDULE = os.getenv('STRIPE_CONNECT_APPLY_PAYOUT_SCHEDULE', 'true').lower() == 'true'
STRIPE_PLATFORM_MCC = os.getenv('STRIPE_PLATFORM_MCC', '4121').strip() or '4121'
STRIPE_PLATFORM_STATEMENT_DESCRIPTOR = os.getenv('STRIPE_PLATFORM_STATEMENT_DESCRIPTOR', 'HolaDrive').strip()[:22]
STRIPE_PLATFORM_PRODUCT_DESCRIPTION = os.getenv(
    'STRIPE_PLATFORM_PRODUCT_DESCRIPTION', 'Ride-hailing and on-demand transport'
).strip()
STRIPE_CONNECTED_ACCOUNT_AGREEMENT_URL = (
    'https://stripe.com/legal/connect-account'
)
# Optional marketplace fee lines (checkout-preview)
CUSTOMER_PLATFORM_FEE_PERCENT = os.getenv('CUSTOMER_PLATFORM_FEE_PERCENT', '0').strip() or '0'
CUSTOMER_SERVICE_FEE_PERCENT = os.getenv('CUSTOMER_SERVICE_FEE_PERCENT', '0').strip() or '0'
PROVIDER_PLATFORM_FEE_PERCENT = os.getenv(
    'PROVIDER_PLATFORM_FEE_PERCENT',
    os.getenv('STRIPE_APPLICATION_FEE_PERCENT', '0'),
).strip() or '0'


# Django Channels Configuration
ASGI_APPLICATION = 'config.asgi.application'

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
