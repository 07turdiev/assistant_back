"""Thread-local current_user middleware — AuditMixin avtomatik to'ldirish uchun."""
from contextvars import ContextVar
from django.contrib.auth.models import AnonymousUser

_current_user: ContextVar = ContextVar('current_user', default=None)


def get_current_user():
    return _current_user.get()


def set_current_user(user):
    _current_user.set(user)


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if isinstance(user, AnonymousUser):
            user = None
        token = _current_user.set(user)
        try:
            return self.get_response(request)
        finally:
            _current_user.reset(token)
