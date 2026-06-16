"""Google Gemini API klienti (`generativelanguage` REST).

Ollama bilan bir xil interfeys: ``chat_json(system, user) -> dict``.
JSON chiqishi ``responseMimeType: "application/json"`` orqali kafolatlanadi —
bu Ollama'ning ``format='json'`` ekvivalenti, lekin ishonchliroq.

Konfiguratsiya (`settings` → `.env`):
    GEMINI_API_KEY  — Google AI Studio kaliti (https://aistudio.google.com/apikey)
    GEMINI_MODEL    — masalan 'gemini-2.5-flash' (tez), 'gemini-2.5-flash-lite' (eng tez)
    GEMINI_API_URL  — bazaviy URL (odatda o'zgartirilmaydi)
"""
from __future__ import annotations

import json
import logging
from typing import Any

import requests
from django.conf import settings

from .base import LLMError

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta'


class GeminiError(LLMError):
    """Gemini API bilan bog'liq xatolik."""


class GeminiClient:
    """Google Gemini'ga sodda REST klient.

    Misol:
        client = GeminiClient()
        data = client.chat_json(
            system="Sen vazirlik yordamchisisan...",
            user="Ertaga 14 da kollegiya",
        )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, 'GEMINI_API_KEY', '')
        self.model = model or getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')
        self.base_url = (base_url or getattr(settings, 'GEMINI_API_URL', _DEFAULT_BASE_URL)).rstrip('/')
        self.timeout = timeout

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        **_ignored: Any,
    ) -> dict[str, Any]:
        """Gemini'ga so'rov yuborib, JSON dict qaytaradi.

        `**_ignored` — Ollama'ga xos `num_ctx` kabi parametrlarni yutib yuboradi,
        shu tufayli interfeys ikkala provayderda bir xil ishlaydi.
        """
        if not self.api_key:
            raise GeminiError('GEMINI_API_KEY sozlanmagan — .env ga kalit qo\'shing')

        url = f'{self.base_url}/models/{self.model}:generateContent'
        payload = {
            'system_instruction': {'parts': [{'text': system}]},
            'contents': [{'role': 'user', 'parts': [{'text': user}]}],
            'generationConfig': {
                'temperature': temperature,
                # JSON sxemasiga rioya qilishni majbur qiladi (Ollama format='json' ekvivalenti)
                'responseMimeType': 'application/json',
            },
        }
        headers = {
            'x-goog-api-key': self.api_key,
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            detail = _extract_api_error(e)
            logger.error('Gemini bilan bog\'lanishda xato: %s %s', e, detail)
            raise GeminiError(f'Gemini API ulanmadi: {e}. {detail}'.strip()) from e

        body = response.json()
        candidates = body.get('candidates') or []
        if not candidates:
            # Xavfsizlik filtri yoki boshqa sabab bilan bloklangan bo'lishi mumkin
            feedback = body.get('promptFeedback') or {}
            raise GeminiError(f'Gemini javob qaytarmadi (bloklangan bo\'lishi mumkin): {feedback}')

        parts = candidates[0].get('content', {}).get('parts') or []
        content = ''.join(p.get('text', '') for p in parts).strip()
        if not content:
            raise GeminiError('Gemini bo\'sh javob qaytardi')

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error('Gemini noto\'g\'ri JSON qaytardi: %s', content[:500])
            raise GeminiError(f'JSON parse xatosi: {e}. Javob: {content[:200]}') from e

    def health(self) -> bool:
        """Kalit va model ishlashini tekshiradi (model metadata so'rovi)."""
        if not self.api_key:
            return False
        try:
            r = requests.get(
                f'{self.base_url}/models/{self.model}',
                headers={'x-goog-api-key': self.api_key},
                timeout=5.0,
            )
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False


def _extract_api_error(exc: requests.exceptions.RequestException) -> str:
    """Gemini xato javobidan o'qiladigan xabar ajratib oladi (mavjud bo'lsa)."""
    resp = getattr(exc, 'response', None)
    if resp is None:
        return ''
    try:
        return resp.json().get('error', {}).get('message', '') or ''
    except (ValueError, AttributeError):
        return (resp.text or '')[:200]
