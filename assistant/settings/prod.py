from .base import *  # noqa: F401,F403

DEBUG = False

# Production: PostgreSQL via DATABASE_URL (parser kerak — placeholder)
# DATABASES = {'default': dj_database_url.parse(os.environ['DATABASE_URL'])}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
