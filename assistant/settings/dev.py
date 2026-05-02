from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS

DEBUG = True
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = False  # explicit list in base.py

# Use console email backend in dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INTERNAL_IPS = ['127.0.0.1', 'localhost']
