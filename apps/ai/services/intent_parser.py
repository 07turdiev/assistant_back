"""Intent parser pipeline: matn → strukturalangan JSON.

Foydalanish:
    from apps.ai.services import parse_intent

    result = parse_intent("Ertaga soat 14 da kollegiya")
    # {'type': 'event', 'title': '...', ...}
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.ai.prompts import build_intent_system_prompt

from .llm import OllamaClient, OllamaError

logger = logging.getLogger(__name__)


REQUIRED_FIELDS = {
    'type', 'title', 'description',
    'date', 'start_time', 'end_time', 'duration_minutes',
    'location', 'is_important', 'is_private',
    'target_department', 'mentioned_participants',
    'notify_minutes_before',
}


def parse_intent(
    text: str,
    *,
    today: date | None = None,
    client: OllamaClient | None = None,
) -> dict[str, Any]:
    """Foydalanuvchi matnini tahlil qilib, strukturalangan dict qaytaradi.

    Args:
        text: foydalanuvchi yuborgan o'zbekcha matn (STT natijasi)
        today: hisob asoslangan sana (default: bugungi)
        client: Ollama klient (default: yangi yaratiladi)

    Raises:
        OllamaError: model yetishilmagan yoki noto'g'ri javob qaytargan bo'lsa
        ValueError: javobda zarur maydonlar yo'q bo'lsa

    Returns:
        type, title, date, start_time va boshqa maydonlardan iborat dict.
    """
    if not text or not text.strip():
        raise ValueError('Bo\'sh matn berildi')

    client = client or OllamaClient()
    system_prompt = build_intent_system_prompt(today=today)

    logger.debug('Intent parser chaqirilmoqda: %s', text[:200])
    raw = client.chat_json(system=system_prompt, user=text.strip())
    return _normalize(raw)


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Ollama javobini normallashtiradi: yetishmagan maydonlarga default to'ldiradi."""
    # `type` validatsiya
    intent_type = raw.get('type')
    if intent_type not in ('event', 'report'):
        raise ValueError(f'Noto\'g\'ri type: {intent_type!r}. "event" yoki "report" kutilgan.')

    # Default qiymatlar
    normalized: dict[str, Any] = {
        'type': intent_type,
        'title': (raw.get('title') or '').strip() or 'Sarlavhasiz',
        'description': raw.get('description'),

        'date': raw.get('date'),
        'start_time': raw.get('start_time'),
        'end_time': raw.get('end_time'),
        'duration_minutes': raw.get('duration_minutes'),
        'location': raw.get('location'),
        'is_important': bool(raw.get('is_important', False)),
        'is_private': bool(raw.get('is_private', False)),

        'target_department': raw.get('target_department'),
        'mentioned_participants': list(raw.get('mentioned_participants') or []),

        'notify_minutes_before': list(raw.get('notify_minutes_before') or _default_notifies(intent_type)),
    }

    # description = null bo'lsa, bo'sh string
    if normalized['description'] is None:
        normalized['description'] = ''

    return normalized


def _default_notifies(intent_type: str) -> list[int]:
    """Eslatma vaqtlari uchun standart qiymatlar."""
    if intent_type == 'event':
        return [60, 1440]  # 1 soat, 1 kun oldin
    return [60]
