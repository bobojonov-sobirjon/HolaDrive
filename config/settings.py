import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    # Load .env file from BASE_DIR explicitly
    env_path = BASE_DIR / '.env'
    # Windows-edited .env files are sometimes not pure UTF-8; try utf-8 then fallback.
    loaded = False
    for enc in ('utf-8-sig', 'utf-8', 'cp1251', 'latin-1'):
        try:
            load_dotenv(dotenv_path=env_path, encoding=enc, override=False)
            loaded = True
            break
        except UnicodeDecodeError:
            continue
    if not loaded:
        load_dotenv(dotenv_path=env_path)
except ImportError:
    load_dotenv = None

_DEBUG_RAW = (os.getenv('DEBUG', 'False') or 'False').strip().lower()
DEBUG = _DEBUG_RAW in ('1', 'true', 'yes', 'on')

SECRET_KEY = (os.getenv('SECRET_KEY') or '').strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key-change-in-production'
    else:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is False.')

_default_hosts = 'localhost,127.0.0.1,api.holadrive.app,apiss.firepole.ru'
_hosts_raw = os.getenv('ALLOWED_HOSTS', _default_hosts)
ALLOWED_HOSTS = [h.strip() for h in _hosts_raw.split(',') if h.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
elif not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be set when DEBUG is False.')

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
    'apps.voice_call',
    'apps.safety',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
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
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60') or '60'),
        'CONN_HEALTH_CHECKS': True,
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
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.getenv('MEDIA_ROOT', '/var/www/media')

# Prepended to MEDIA paths in WebSocket/API payloads (e.g. https://api.example.com — no trailing slash)
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
_public_host = urlparse(PUBLIC_BASE_URL).hostname if PUBLIC_BASE_URL else None
if _public_host and _public_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_public_host)
# Mobile app deep link (custom scheme), e.g. holadrive → holadrive://trip/share/<token>
APP_DEEP_LINK_SCHEME = (os.getenv('APP_DEEP_LINK_SCHEME', 'holadrive') or 'holadrive').strip().rstrip(':/')
# Optional HTTPS universal / App Link host for share (defaults to PUBLIC_BASE_URL)
APP_SHARE_HTTPS_BASE = (
    os.getenv('APP_SHARE_HTTPS_BASE', '') or os.getenv('PUBLIC_BASE_URL', '') or ''
).rstrip('/')
# Store fallbacks when app is not installed (share link landing page)
IOS_APP_STORE_URL = os.getenv(
    'IOS_APP_STORE_URL',
    'https://apps.apple.com/app/id0000000000',
)
ANDROID_PLAY_STORE_URL = os.getenv(
    'ANDROID_PLAY_STORE_URL',
    'https://play.google.com/store/apps/details?id=com.holadrive.app',
)
SAFETY_SHARE_EXPIRE_HOURS = int(os.getenv('SAFETY_SHARE_EXPIRE_HOURS', '6') or '6')
SAFETY_EMERGENCY_NUMBER = os.getenv('SAFETY_EMERGENCY_NUMBER', '911')
# Deprecated alias (ignored for mobile; kept so old .env does not crash)
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', '').rstrip('/')

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
    'EXCEPTION_HANDLER': 'apps.common.exception_handlers.holadrive_exception_handler',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    "DEFAULT_PARSER_CLASSES": (
        "apps.common.parsers.LenientJSONParser",
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
        'anon': '60/minute',
        'user': '300/minute',
        'login': '5/minute',
        'otp': '5/minute',
        'otp_verify': '10/minute',
        'order_create': '20/minute',
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
        {'name': 'Rider: Live tracking', 'description': 'Assigned driver location (HTTP). WebSocket: ws/order/{id}/tracking/ (driver_location_update + rider_location_update).'},
        {'name': 'Driver: Location', 'description': 'Driver GPS update + rider live location for active order.'},
        {'name': 'Driver: Orders & trips', 'description': 'Offers, accept/reject, pickup, complete, cancel, active trip.'},
        {'name': 'Driver: Location', 'description': 'Driver GPS updates for live tracking.'},
        {'name': 'Driver: Earnings & wallet', 'description': 'Dashboard, earnings, history, and cash-out requests.'},
        {'name': 'Driver: Availability', 'description': 'Online / offline status.'},
        {'name': 'Admin Panel', 'description': 'React admin panel: drivers, riders, orders, cash-outs, analytics.'},
        {'name': 'Trip ratings', 'description': 'Post-trip ratings and feedback tags.'},
        {'name': 'Trip chat', 'description': 'Order-scoped rider–driver chat (HTTP).'},
        {'name': 'Safety tools', 'description': 'Share trip link, safety agent chat, voice recording, 911 config.'},
        {'name': 'Payment: Saved cards', 'description': 'Stripe saved cards (rider/driver): GET/POST/PUT/DELETE.'},
        {'name': 'Payment: Stripe', 'description': 'Stripe Customer id (cus_) for riders.'},
        {'name': 'Stripe — Driver', 'description': 'Stripe Connect: bank account, balance, checkout history.'},
    ],
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
    'SERVE_PERMISSIONS': [
        'rest_framework.permissions.AllowAny' if DEBUG else 'rest_framework.permissions.IsAdminUser'
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "30"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
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
    "https://apiss.firepole.ru",
    "https://api.holadrive.app",
]

_public_base = (os.getenv('PUBLIC_BASE_URL') or '').strip().rstrip('/')
if _public_base and _public_base not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_public_base)

_extra_csrf = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if _extra_csrf:
    for origin in (o.strip().rstrip('/') for o in _extra_csrf.split(',') if o.strip()):
        if origin and origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

_cors_origins = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174,'
    'https://localhost:3000,https://localhost:5173,https://127.0.0.1:5173,https://127.0.0.1:5174,'
    'https://hola-admin-nu.vercel.app,https://apiss.firepole.ru,https://api.holadrive.app'
)
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins.split(',') if origin.strip()]
# file:// HTML tester sends Origin: null — allow in DEBUG so local tests work
if DEBUG and 'null' not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = list(CORS_ALLOWED_ORIGINS) + ['null']

CORS_ALLOW_ALL_ORIGINS = (
    DEBUG and os.getenv('CORS_ALLOW_ALL_ORIGINS', 'false').lower() == 'true'
)
CORS_ALLOW_CREDENTIALS = True

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_USER_MODEL = 'accounts.CustomUser'

SITE_ID = 1

def _env_text(key: str, default: str = '') -> str:
    """Read env var as clean UTF-8 text (avoids SMTP/login UnicodeDecodeError)."""
    raw = os.getenv(key, default)
    if raw is None:
        return default
    if isinstance(raw, bytes):
        for enc in ('utf-8', 'utf-8-sig', 'cp1251', 'latin-1'):
            try:
                raw = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raw = raw.decode('utf-8', errors='replace')
    text = str(raw).strip()
    # Strip BOM / nulls that break smtplib AUTH
    text = text.lstrip('\ufeff').replace('\x00', '')
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        text = text.encode('utf-8', errors='replace').decode('utf-8')
    return text


EMAIL_BACKEND = _env_text('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = _env_text('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(_env_text('EMAIL_PORT', '587') or '587')
EMAIL_USE_TLS = _env_text('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = _env_text('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = _env_text('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = _env_text('DEFAULT_FROM_EMAIL', '') or EMAIL_HOST_USER
EMAIL_USE_LOCALTIME = False
# Force SMTP conversation charset (avoids decode crashes on some servers)
EMAIL_CHARSET = 'utf-8'
# Prevent Swagger/UI "Loading..." forever when Gmail SMTP hangs
EMAIL_TIMEOUT = int(_env_text('EMAIL_TIMEOUT', '15') or '15')
# If true: do not call SMTP; log OTP to server logs (same idea as SMS_OTP_LOG_ONLY)
EMAIL_OTP_LOG_ONLY = DEBUG and _env_text('EMAIL_OTP_LOG_ONLY', 'false').lower() in ('1', 'true', 'yes')
# If true: on SMTP failure still succeed and log OTP (off by default — real email like SMS)
EMAIL_OTP_FALLBACK_ON_ERROR = DEBUG and _env_text('EMAIL_OTP_FALLBACK_ON_ERROR', 'false').lower() in (
    '1',
    'true',
    'yes',
)
# Temporary: force every OTP to this value and skip SMTP/SMS. Ignored when DEBUG is False.
FIXED_OTP_CODE = (_env_text('FIXED_OTP_CODE', '') or '').strip() if DEBUG else ''

FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY', '')


TWILIO_ACCOUNT_SID = (os.getenv('TWILIO_ACCOUNT_SID') or '').strip() or None
TWILIO_AUTH_TOKEN = (os.getenv('TWILIO_AUTH_TOKEN') or '').strip() or None
TWILIO_PHONE_NUMBER = (os.getenv('TWILIO_PHONE_NUMBER') or '').strip() or None
# Dev/staging only: log OTP to server logs instead of Twilio SMS (never enable on production).
SMS_OTP_LOG_ONLY = DEBUG and os.getenv('SMS_OTP_LOG_ONLY', 'False').lower() == 'true'

# Stripe (saved cards, payments). Keys from https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
# Trip card charges (PaymentIntent): ISO currency, platform fee % when using Stripe Connect destination
STRIPE_CHARGE_CURRENCY = os.getenv('STRIPE_CHARGE_CURRENCY', 'cad').strip().lower() or 'cad'
STRIPE_APPLICATION_FEE_PERCENT = os.getenv('STRIPE_APPLICATION_FEE_PERCENT', '0').strip() or '0'

# Stripe Connect (driver payouts) — see docs/STRIPE_HolaDrive_INTEGRATION.md
STRIPE_CONNECT_ACCOUNT_TYPE = os.getenv('STRIPE_CONNECT_ACCOUNT_TYPE', 'custom').strip().lower() or 'custom'
STRIPE_CONNECT_COUNTRY = os.getenv('STRIPE_CONNECT_COUNTRY', 'US').strip().upper() or 'US'
STRIPE_CONNECT_PAYOUT_INTERVAL = os.getenv('STRIPE_CONNECT_PAYOUT_INTERVAL', 'manual').strip().lower() or 'manual'
STRIPE_CONNECT_PAYOUT_WEEKLY_ANCHOR = os.getenv('STRIPE_CONNECT_PAYOUT_WEEKLY_ANCHOR', 'monday').strip().lower() or 'monday'
STRIPE_CONNECT_PAYOUT_DELAY_DAYS = os.getenv('STRIPE_CONNECT_PAYOUT_DELAY_DAYS', '').strip()
STRIPE_CONNECT_APPLY_PAYOUT_SCHEDULE = os.getenv('STRIPE_CONNECT_APPLY_PAYOUT_SCHEDULE', 'true').lower() == 'true'
STRIPE_PLATFORM_MCC = os.getenv('STRIPE_PLATFORM_MCC', '4121').strip() or '4121'
STRIPE_PLATFORM_STATEMENT_DESCRIPTOR = os.getenv('STRIPE_PLATFORM_STATEMENT_DESCRIPTOR', 'HolaDrive').strip()[:22]
STRIPE_PLATFORM_BUSINESS_URL = (
    os.getenv('STRIPE_PLATFORM_BUSINESS_URL', '').strip()
    or PUBLIC_BASE_URL
).strip()
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

_redis_cache_url = os.getenv('CACHE_URL') or os.getenv('REDIS_URL', 'redis://localhost:6379/2')
if _use_redis:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_cache_url,
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'holadrive-local',
        }
    }

SUPPORT_USER_EMAIL = os.getenv('SUPPORT_USER_EMAIL', '').strip()
LOCATION_DB_THROTTLE_SECONDS = int(os.getenv('LOCATION_DB_THROTTLE_SECONDS', '10') or '10')
OTP_MAX_ATTEMPTS = int(os.getenv('OTP_MAX_ATTEMPTS', '5') or '5')
OTP_LOCKOUT_SECONDS = int(os.getenv('OTP_LOCKOUT_SECONDS', '900') or '900')

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    if (PUBLIC_BASE_URL or '').startswith('https://'):
        SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'false').lower() == 'true'
        SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000') or '0')
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = False

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
        'json': {
            '()': 'config.json_logging.JsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if DEBUG else 'json',
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
        'formatter': 'verbose' if DEBUG else 'json',
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

# Agora voice calls (RTC)
AGORA_APP_ID = os.getenv('AGORA_APP_ID', '')
AGORA_APP_CERTIFICATE = os.getenv('AGORA_APP_CERTIFICATE', '')
AGORA_TOKEN_EXPIRE_SECONDS = int(os.getenv('AGORA_TOKEN_EXPIRE_SECONDS', '3600'))
