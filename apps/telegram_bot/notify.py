"""Telegram message yuborish (sync) — Bot HTTP API orqali.

Aiogram async, biz esa NotificationService'dan sync chaqirishimiz kerak.
Shu sababdan to'g'ridan-to'g'ri Bot API'ga POST qilamiz (httpx/requests).
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_BASE = 'https://api.telegram.org'


def _get_token() -> str | None:
    return getattr(settings, 'TG_BOT_TOKEN', '') or None


def send_message(telegram_id: int, text: str, *, parse_mode: str = 'HTML') -> bool:
    """Telegram'ga xabar yuborish (sync). Returns True if sent successfully."""
    token = _get_token()
    if not token:
        logger.info(f'[TG noop] token yo\'q, xabar yuborilmadi → {telegram_id}')
        return False
    if not telegram_id:
        return False

    url = f'{API_BASE}/bot{token}/sendMessage'
    try:
        resp = requests.post(
            url,
            json={
                'chat_id': telegram_id,
                'text': text,
                'parse_mode': parse_mode,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        logger.warning(f'TG send xatosi (HTTP {resp.status_code}): {resp.text[:200]}')
        return False
    except requests.RequestException as e:
        logger.warning(f'TG network xatosi: {e}')
        return False


def send_to_many(telegram_ids: list[int], text: str) -> int:
    """Bir nechta foydalanuvchiga yuborish. Returns yuborilgan xabarlar soni."""
    sent = 0
    for tg_id in telegram_ids:
        if tg_id and send_message(tg_id, text):
            sent += 1
    return sent
