"""Fuzzy (foizli o'xshashlik) matn taqqoslash — `difflib` asosida (qo'shimcha kutubxonasiz).

AI/STT ajratgan nomlar DB'dagi nomlarga to'liq mos kelmasligi mumkin (imlo, qo'shimcha,
so'z tartibi). Shu sababli aniq mos topilmasa, o'xshashlik foizi bo'yicha eng yaqinini olamiz.

Foydalanish:
    from apps.core.fuzzy import best_match, similarity
    hall = best_match(text, Hall.objects.all(), key=lambda h: h.name, threshold=0.7)
"""
from __future__ import annotations

import difflib
from typing import Callable, Iterable, Optional, TypeVar

T = TypeVar('T')


def _norm(s: str | None) -> str:
    """Kichik harf, ortiqcha bo'shliqlarni tozalash, apostrof variantlarini birxillashtirish."""
    if not s:
        return ''
    s = s.lower().replace('ʻ', "'").replace('ʼ', "'").replace('’', "'").replace('`', "'")
    return ' '.join(s.split())


def similarity(a: str | None, b: str | None) -> float:
    """0..1 oralig'ida o'xshashlik koeffitsiyenti (1 — to'liq mos)."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    score = difflib.SequenceMatcher(None, na, nb).ratio()
    # So'z tartibidan mustaqil — tokenlarni saralab ham solishtiramiz
    # ("Akmal Karimov" ~ "Karimov Akmal")
    ta = ' '.join(sorted(na.split()))
    tb = ' '.join(sorted(nb.split()))
    score = max(score, difflib.SequenceMatcher(None, ta, tb).ratio())
    # Biri ikkinchisining ichida bo'lsa (substring) — yuqori ball
    if na in nb or nb in na:
        score = max(score, 0.92)
    return score


def best_match(
    query: str | None,
    candidates: Iterable[T],
    *,
    key: Callable[[T], str] = lambda x: str(x),
    threshold: float = 0.7,
) -> Optional[T]:
    """`candidates` ichidan `query`'ga eng o'xshash (foiz threshold'dan yuqori) elementni qaytaradi.

    Args:
        query: qidirilayotgan matn (AI ajratgan nom)
        candidates: nomzodlar ro'yxati
        key: nomzoddan taqqoslanadigan matnni oluvchi funksiya
        threshold: minimal o'xshashlik (0..1). Pastida bo'lsa — None.
    """
    q = _norm(query)
    if not q:
        return None
    best: Optional[T] = None
    best_score = 0.0
    for c in candidates:
        score = similarity(query, key(c))
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= threshold else None
