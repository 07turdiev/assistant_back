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
    intent_type_hint: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Foydalanuvchi matnini tahlil qilib, strukturalangan dict + ogohlantirishlar qaytaradi.

    Agar Ollama yiqilsa yoki javobi noto'g'ri bo'lsa — best-effort fallback ishga tushadi:
    bo'sh draft yaratiladi, foydalanuvchi saytda qo'lda to'ldirib joylash mumkin.
    Warning ro'yxati `[2]` element sifatida qaytadi va summary'da ko'rsatiladi.

    Args:
        text: foydalanuvchi yuborgan o'zbekcha matn (STT natijasi)
        today: hisob asoslangan sana (default: bugungi)
        client: Ollama klient (default: yangi yaratiladi)
        intent_type_hint: 'event' yoki 'task' (Telegram tugmasidan kelgan ipucu)

    Returns:
        (intent_dict, warnings) — intent doimo qaytadi (fallback bo'lsa ham).
    """
    if not text or not text.strip():
        raise ValueError('Bo\'sh matn berildi')

    client = client or OllamaClient()
    system_prompt = build_intent_system_prompt(today=today)

    logger.debug('Intent parser chaqirilmoqda: %s', text[:200])
    try:
        raw = client.chat_json(system=system_prompt, user=text.strip())
        intent = _normalize(raw)
        return intent, []
    except (OllamaError, ValueError) as e:
        logger.warning('AI parser yiqildi, fallback ishlatilmoqda: %s', e)
        fallback = _build_fallback(text, intent_type_hint)
        warnings = [
            'AI tahlilchi javob bermadi — bo\'sh qoralama yaratildi. '
            'Saytda barcha maydonlarni qo\'lda to\'ldiring.',
        ]
        return fallback, warnings


def _build_fallback(text: str, intent_type_hint: str | None) -> dict[str, Any]:
    """AI ishlamasa — foydalanuvchi matnini sarlavha sifatida bo'sh draft yaratadi."""
    intent_type = 'event' if intent_type_hint == 'event' else 'report'
    # Sarlavha sifatida birinchi 80 ta belgini olamiz, qolgani — description
    title = text.strip()
    if len(title) > 80:
        title = title[:77] + '...'
    return {
        'type': intent_type,
        'title': title or 'Sarlavhasiz',
        'description': text.strip(),
        'date': None,
        'start_time': None,
        'end_time': None,
        'duration_minutes': None,
        'location': None,
        'is_important': False,
        'is_private': False,
        'target_department': None,
        'mentioned_participants': [],
        'notify_minutes_before': _default_notifies(intent_type),
    }


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
