"""Web Push yuborish helper'lari (pywebpush + VAPID)."""
import json
import logging

from django.conf import settings
from django.utils import timezone
from pywebpush import WebPushException, webpush

from .models import WebPushSubscription

logger = logging.getLogger(__name__)


def _vapid_claims() -> dict:
    return {'sub': settings.VAPID_CLAIMS_EMAIL}


def send_to_subscription(sub: WebPushSubscription, payload: dict) -> bool:
    """Bitta subscription'ga push yuborish.

    Returns:
        True — yuborildi
        False — yuborishda xato (404/410 bo'lsa subscription o'chiriladi)
    """
    if not settings.VAPID_PRIVATE_KEY:
        logger.warning('VAPID_PRIVATE_KEY sozlanmagan, Web Push o\'tkazib yuborildi')
        return False

    try:
        webpush(
            subscription_info={
                'endpoint': sub.endpoint,
                'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=_vapid_claims(),
            ttl=86400,  # 24 soat — push servis xabarni saqlash muddati
        )
        sub.last_used_at = timezone.now()
        sub.save(update_fields=['last_used_at'])
        return True
    except WebPushException as e:
        status_code = e.response.status_code if e.response is not None else 0
        if status_code in (404, 410):
            # Subscription endi yaroqsiz — DB'dan o'chiramiz
            logger.info(f'WebPush subscription expired ({status_code}): {sub.id}')
            sub.delete()
        else:
            logger.warning(f'WebPush xatosi (status={status_code}): {e}')
        return False
    except Exception as e:  # noqa: BLE001
        logger.exception(f'WebPush dispatch xatosi: {e}')
        return False


def send_to_user(user_id, *, title: str, body: str = '', url: str = '/',
                 is_important: bool = False, tag: str = '', icon: str = '',
                 data: dict | None = None) -> int:
    """User'ning barcha subscription'lariga push yuborish.

    Args:
        icon: ko'rinadigan rasm URL'i (chat uchun — yuboruvchi avatari). Bo'sh bo'lsa
            frontend sw.js favicon'ga qaytadi.

    Returns: yuborilgan push'lar soni.
    """
    payload = {
        'title': title,
        'body': body,
        'url': url,
        'is_important': is_important,
    }
    if tag:
        payload['tag'] = tag
    if icon:
        payload['icon'] = icon
    if data:
        payload['data'] = data

    sent = 0
    subs = list(WebPushSubscription.objects.filter(user_id=user_id))
    for sub in subs:
        if send_to_subscription(sub, payload):
            sent += 1
    return sent
