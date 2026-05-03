"""SMS yuborish — production'da `91.204.239.44/broker-api/send` ga POST.

Production SmsService.java mantig'i:
- Endpoint: settings.SMS_API_URL
- Auth: Basic (login + password)
- Body: {"messages": [{"recipient": "...", "message-id": "...", "sms": {"originator": "3700", "content": {"text": "..."}}}]}
- recipient — `+` belgisi olib tashlangan E.164 format
"""
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _credentials() -> tuple[str, str] | None:
    login = getattr(settings, 'SMS_API_LOGIN', '')
    password = getattr(settings, 'SMS_API_PASSWORD', '')
    if not login or not password:
        return None
    return (login, password)


def send_to_many(phone_numbers: list[str], text: str) -> int:
    """Bir nechta raqamga SMS yuborish.

    Returns: muvaffaqiyatli yuborilgan SMS soni.
    """
    if not phone_numbers or not text:
        return 0

    creds = _credentials()
    url = getattr(settings, 'SMS_API_URL', '')
    originator = getattr(settings, 'SMS_API_ORIGINATOR', '3700')
    if not creds or not url:
        logger.info(f'[SMS noop] credentials/URL yo\'q ({len(phone_numbers)} ta raqam)')
        return 0

    base_id = int(time.time() * 1000)
    messages = []
    valid_recipients = 0
    for i, phone in enumerate(phone_numbers):
        cleaned = (phone or '').strip().lstrip('+')
        if not cleaned or not cleaned.isdigit():
            continue
        valid_recipients += 1
        messages.append({
            'recipient': cleaned,
            'message-id': str(base_id + i),
            'sms': {
                'originator': originator,
                'content': {'text': text},
            },
        })

    if not messages:
        return 0

    try:
        resp = requests.post(
            url, json={'messages': messages}, auth=creds, timeout=15,
        )
        if 200 <= resp.status_code < 300:
            logger.info(f'SMS yuborildi: {valid_recipients} ta raqam')
            return valid_recipients
        logger.warning(f'SMS xatosi (HTTP {resp.status_code}): {resp.text[:200]}')
        return 0
    except requests.RequestException as e:
        logger.warning(f'SMS network xatosi: {e}')
        return 0


def send_one(phone: str, text: str) -> bool:
    return send_to_many([phone], text) > 0
