"""Base Django settings shared across environments."""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-insecure-secret-change-me')
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'daphne',  # ASGI server — `runserver` ni Channels-aware qiladi (boshida turishi shart)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'channels',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'mptt',
    'drf_spectacular',

    'apps.core',
    'apps.users',
    'apps.organisations',
    'apps.directions',
    'apps.attachments',
    'apps.events',
    'apps.reports',
    'apps.chat',
    'apps.notifications',
    'apps.scheduler',
    'apps.telegram_bot',
    'apps.auth_app',
    'apps.info',
    'apps.ai',
    'apps.drafts',
]

# Channels — dev uchun in-memory layer (Redis bo'lmasa ham ishlaydi)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.CurrentUserMiddleware',
]

ROOT_URLCONF = 'assistant.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'assistant.wsgi.application'
ASGI_APPLICATION = 'assistant.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'users.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = config('DJANGO_TIME_ZONE', default='Asia/Tashkent')
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('uz', 'O\'zbek'),
    ('ru', 'Русский'),
]

STATIC_URL = 'django-static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.core.authentication.JWTCookieAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardPageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=config('JWT_ACCESS_LIFETIME_SECONDS', default=86400, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(seconds=config('JWT_REFRESH_LIFETIME_SECONDS', default=604800, cast=int)),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
}

# Cookie auth
COOKIE_ACCESS_NAME = 'access_token'
COOKIE_REFRESH_NAME = 'refresh_token'
COOKIE_DOMAIN = config('COOKIE_DOMAIN', default='') or None
COOKIE_SECURE = config('COOKIE_SECURE', default=False, cast=bool)
COOKIE_SAMESITE = config('COOKIE_SAMESITE', default='Lax')

# CORS
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173',
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Smart assistant API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Web Push (VAPID)
VAPID_PUBLIC_KEY = config('VAPID_PUBLIC_KEY', default='')
VAPID_PRIVATE_KEY = config('VAPID_PRIVATE_KEY', default='')
VAPID_CLAIMS_EMAIL = config('VAPID_CLAIMS_EMAIL', default='mailto:admin@example.com')

# Telegram bot
TG_BOT_TOKEN = config('TG_BOT_TOKEN', default='')
TG_BOT_USERNAME = config('TG_BOT_USERNAME', default='')
# Server ishga tushganda bot ham avtomatik daemon thread'da ishga tushadimi
TG_BOT_AUTOSTART = config('TG_BOT_AUTOSTART', default=False, cast=bool)

# SMS provider (production: 91.204.239.44/broker-api/send)
SMS_API_URL = config('SMS_API_URL', default='')
SMS_API_LOGIN = config('SMS_API_LOGIN', default='')
SMS_API_PASSWORD = config('SMS_API_PASSWORD', default='')
SMS_API_ORIGINATOR = config('SMS_API_ORIGINATOR', default='3700')

# Email (Gmail SMTP)
EMAIL_HOST = config('SMTP_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('SMTP_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('SMTP_USER', default='')
EMAIL_HOST_PASSWORD = config('SMTP_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('SMTP_FROM', default='') or EMAIL_HOST_USER

# AI / LLM (Ollama lokal server)
OLLAMA_URL = config('OLLAMA_URL', default='http://localhost:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='qwen3:14b')

# STT — UzbekVoice.ai
UZBEKVOICE_API_KEY = config('UZBEKVOICE_API_KEY', default='')
UZBEKVOICE_LANGUAGE = config('UZBEKVOICE_LANGUAGE', default='uz')
UZBEKVOICE_MODEL = config('UZBEKVOICE_MODEL', default='general')

# Voice fayllarni saqlash muddati (kun) — keyin auto-delete
VOICE_FILE_RETENTION_DAYS = config('VOICE_FILE_RETENTION_DAYS', default=30, cast=int)

# Admin theme tweaks
ADMIN_SITE_HEADER = 'Smart assistant — Emergency Admin'
ADMIN_SITE_TITLE = 'Emergency Admin'
ADMIN_INDEX_TITLE = "Faqat superuser uchun. Kundalik ish — dashboard."
