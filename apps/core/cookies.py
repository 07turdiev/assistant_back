"""Helpers to set/clear JWT cookies."""
from django.conf import settings


def _common_kwargs():
    return {
        'httponly': True,
        'secure': settings.COOKIE_SECURE,
        'samesite': settings.COOKIE_SAMESITE,
        'domain': settings.COOKIE_DOMAIN,
        'path': '/',
    }


def set_access_cookie(response, token: str, max_age: int):
    response.set_cookie(
        settings.COOKIE_ACCESS_NAME,
        token,
        max_age=max_age,
        **_common_kwargs(),
    )


def set_refresh_cookie(response, token: str, max_age: int):
    response.set_cookie(
        settings.COOKIE_REFRESH_NAME,
        token,
        max_age=max_age,
        **_common_kwargs(),
    )


def clear_auth_cookies(response):
    kwargs = {
        'domain': settings.COOKIE_DOMAIN,
        'path': '/',
        'samesite': settings.COOKIE_SAMESITE,
    }
    response.delete_cookie(settings.COOKIE_ACCESS_NAME, **kwargs)
    response.delete_cookie(settings.COOKIE_REFRESH_NAME, **kwargs)
