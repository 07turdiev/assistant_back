"""WebSocket JWT cookie auth middleware (Channels uchun).

Frontend axios `withCredentials: true` orqali cookie'da JWT yuboradi.
Channels'da cookie'dan o'qib `scope['user']` ni to'ldiradi.
"""
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(user_id):
    from apps.users.models import User
    try:
        return User.objects.select_related('role', 'direction').get(pk=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


def _parse_cookies(headers: list) -> dict:
    raw = b''
    for name, value in headers:
        if name == b'cookie':
            raw = value
            break
    if not raw:
        return {}
    cookies = {}
    for part in raw.decode('latin-1').split(';'):
        if '=' in part:
            k, v = part.strip().split('=', 1)
            cookies[k] = v
    return cookies


class JWTCookieAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        cookies = _parse_cookies(scope.get('headers', []))
        token = cookies.get(settings.COOKIE_ACCESS_NAME)

        user = AnonymousUser()
        if token:
            try:
                validated = AccessToken(token)
                user_id = validated.payload.get(settings.SIMPLE_JWT['USER_ID_CLAIM'])
                if user_id:
                    user = await _get_user(user_id)
            except (TokenError, InvalidToken):
                pass

        scope['user'] = user
        return await super().__call__(scope, receive, send)
