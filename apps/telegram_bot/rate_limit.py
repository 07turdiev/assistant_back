"""Brute-force himoyasi — telegram bot login parolini cheksiz urinishdan to'xtatadi.

Strategiya:
- Har bir chat_id uchun urinishlar soni va lock paytini cache'da saqlaymiz
- 5 ta noto'g'ri urinishdan keyin 15 daqiqa lock
- Muvaffaqiyatli login → counter reset
"""
from __future__ import annotations

from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.core.cache import cache

# Konfiguratsiya — agar kerak bo'lsa settings'dan olish mumkin
MAX_ATTEMPTS = 5
LOCK_DURATION_SECONDS = 15 * 60  # 15 daqiqa
ATTEMPT_WINDOW_SECONDS = 30 * 60  # 30 daqiqa ichidagi urinishlar hisoblanadi


def _attempts_key(chat_id: int) -> str:
    return f'tgbot:auth:attempts:{chat_id}'


def _lock_key(chat_id: int) -> str:
    return f'tgbot:auth:lock_until:{chat_id}'


@sync_to_async
def is_locked(chat_id: int) -> tuple[bool, int]:
    """Foydalanuvchi lock'da bo'lsa (True, qolgan_soniya); aks holda (False, 0)."""
    locked_until = cache.get(_lock_key(chat_id))
    if not locked_until:
        return False, 0
    now = datetime.utcnow().timestamp()
    if locked_until <= now:
        cache.delete(_lock_key(chat_id))
        cache.delete(_attempts_key(chat_id))
        return False, 0
    return True, int(locked_until - now)


@sync_to_async
def record_failure(chat_id: int) -> tuple[int, bool]:
    """Noto'g'ri urinishni qayd qiladi.

    Returns:
        (attempts_count, lock_triggered)
    """
    key = _attempts_key(chat_id)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=ATTEMPT_WINDOW_SECONDS)
    if attempts >= MAX_ATTEMPTS:
        lock_until = (datetime.utcnow() + timedelta(seconds=LOCK_DURATION_SECONDS)).timestamp()
        cache.set(_lock_key(chat_id), lock_until, timeout=LOCK_DURATION_SECONDS)
        return attempts, True
    return attempts, False


@sync_to_async
def reset(chat_id: int) -> None:
    """Muvaffaqiyatli auth — counter va lock'ni tozalaymiz."""
    cache.delete(_attempts_key(chat_id))
    cache.delete(_lock_key(chat_id))


def format_remaining(seconds: int) -> str:
    """`903` → `15 daq.` ko'rinishida."""
    if seconds < 60:
        return f'{seconds} soniya'
    minutes = (seconds + 59) // 60
    return f'{minutes} daq.'
