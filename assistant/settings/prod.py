"""Production settings — `DJANGO_SETTINGS_MODULE=assistant.settings.prod` bilan ishga tushirish."""
import dj_database_url
from decouple import config

from .base import *  # noqa: F401,F403
from .base import BASE_DIR  # explicit re-import

# ============================================================
# Core security
# ============================================================
DEBUG = False

# Prod'da SECRET_KEY env'dan kelishi shart — default'siz, yo'q bo'lsa Django crash beradi
SECRET_KEY = config('DJANGO_SECRET_KEY')  # type: ignore[assignment]

# ============================================================
# Database — DATABASE_URL orqali (postgres://user:pass@host:5432/db)
# ============================================================
DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    ),
}

# ============================================================
# Channels — Redis layer (prod'da multi-worker uchun shart)
# ============================================================
REDIS_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# ============================================================
# Cookie / TLS / HSTS
# ============================================================
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# ============================================================
# Email
# ============================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# ============================================================
# Logging — fayl + stderr
# ============================================================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {process:d}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'app.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
