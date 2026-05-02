"""JWT auth from HTTP-only cookie (frontend `withCredentials: true` ishlatadi)."""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

from .middleware import set_current_user


class JWTCookieAuthentication(JWTAuthentication):
    """SimpleJWT auth — token cookie'dan o'qiladi.

    Auth muvaffaqiyatli bo'lganda `current_user` thread-local'ni ham to'ldiradi
    (AuditMixin avtomatik `created_by`/`updated_by` to'ldirishi uchun).
    """

    def authenticate(self, request):
        # 1) Avval cookie'dan urinib ko'ramiz
        raw_token = request.COOKIES.get(settings.COOKIE_ACCESS_NAME)
        result = None
        if raw_token:
            try:
                validated = self.get_validated_token(raw_token)
                result = (self.get_user(validated), validated)
            except Exception:  # noqa: BLE001
                pass

        # 2) Header fallback (Swagger UI, mobile clients)
        if result is None:
            result = super().authenticate(request)

        # 3) Thread-local'ni to'ldirish (AuditMixin uchun)
        if result is not None:
            user, _ = result
            set_current_user(user)

        return result
