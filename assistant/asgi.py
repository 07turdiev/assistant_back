"""ASGI config — HTTP + WebSocket (Channels)."""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings.dev')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from apps.notifications.middleware import JWTCookieAuthMiddleware  # noqa: E402
from apps.notifications.routing import websocket_urlpatterns  # noqa: E402

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTCookieAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
