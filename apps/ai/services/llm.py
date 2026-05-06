"""Ollama HTTP client.

Lokal Ollama serverga `/api/chat` orqali so'rov yuboradi va JSON formatdagi javobni qaytaradi.
Konfiguratsiya `settings.OLLAMA_URL` va `settings.OLLAMA_MODEL` orqali.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Ollama bilan bog'liq xatolik."""


class OllamaClient:
    """Ollama lokal serveriga sodda klient.

    Misol:
        client = OllamaClient()
        data = client.chat_json(
            system="Sen vazirlik yordamchisisan...",
            user="Ertaga 14 da kollegiya",
        )
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 600.0,
    ):
        self.base_url = (base_url or getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')).rstrip('/')
        self.model = model or getattr(settings, 'OLLAMA_MODEL', 'qwen3:14b')
        self.timeout = timeout

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        num_ctx: int = 8192,
    ) -> dict[str, Any]:
        """Modelga so'rov yuborib, JSON dict qaytaradi.

        `format='json'` parametri Ollama'ga JSON sxemasiga rioya qilishni majbur qiladi.
        Qwen 3 reasoning'ini o'chirish uchun system prompt'ga `/no_think` qo'shilgan bo'lishi kerak.
        """
        url = f'{self.base_url}/api/chat'
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': f'{user}\n\n/no_think'},
            ],
            'format': 'json',
            'stream': False,
            # qwen3 reasoning rejimini o'chirish — CPU'da 5-10x tezlashtiradi.
            'think': False,
            # `keep_alive` — modelni xotirada nechta vaqt ushlab turish.
            # Productionda 30 daqiqa, sovuq start xarajatini sezilarli kamaytiradi.
            'keep_alive': '30m',
            'options': {
                'temperature': temperature,
                'num_ctx': num_ctx,
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error('Ollama bilan bog\'lanishda xato: %s', e)
            raise OllamaError(f'Ollama serverga ulanmadi: {e}') from e

        body = response.json()
        content = body.get('message', {}).get('content', '').strip()
        if not content:
            raise OllamaError('Ollama bo\'sh javob qaytardi')

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error('Ollama noto\'g\'ri JSON qaytardi: %s', content[:500])
            raise OllamaError(f'JSON parse xatosi: {e}. Javob: {content[:200]}') from e

    def health(self) -> bool:
        """Ollama server ishga tushganini tekshiradi."""
        try:
            r = requests.get(f'{self.base_url}/api/tags', timeout=5.0)
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False
