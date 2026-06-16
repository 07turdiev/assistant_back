"""LLM provayder abstraktsiyasi.

Barcha LLM klientlari (Ollama, Gemini) bir xil interfeysga ega:

    client.chat_json(system: str, user: str, *, temperature: float = 0.1) -> dict

`get_llm_client()` `settings.AI_PROVIDER` ga qarab mos klientni qaytaradi.
Shu tufayli `intent_parser` va boshqa chaqiruvchilar provayderdan mustaqil bo'ladi —
provayderni almashtirish faqat konfiguratsiya (`.env`) orqali amalga oshiriladi.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from django.conf import settings


class LLMError(RuntimeError):
    """Har qanday LLM provayderi bilan bog'liq umumiy xatolik.

    `OllamaError` va `GeminiError` shundan meros oladi — shu tufayli
    chaqiruvchilar bitta `except LLMError` bilan ikkalasini ham tutib oladi.
    """


@runtime_checkable
class LLMClient(Protocol):
    """LLM klient interfeysi (Ollama / Gemini umumiy shartnoma)."""

    def chat_json(self, system: str, user: str, *, temperature: float = ...) -> dict[str, Any]:
        ...


def get_llm_client() -> LLMClient:
    """`settings.AI_PROVIDER` ga qarab LLM klientini qaytaradi.

    - ``'gemini'`` → :class:`GeminiClient` (Google bulut, CPU lokaldan ancha tez)
    - ``'ollama'`` (default) → :class:`OllamaClient` (lokal server)

    Provayder modullari kech (lazy) import qilinadi — sirkulyar importdan saqlanish
    va kerak bo'lmagan provayder bog'liqliklarini yuklamaslik uchun.
    """
    provider = (getattr(settings, 'AI_PROVIDER', 'ollama') or 'ollama').strip().lower()
    if provider == 'gemini':
        from .gemini import GeminiClient
        return GeminiClient()
    from .llm import OllamaClient
    return OllamaClient()
