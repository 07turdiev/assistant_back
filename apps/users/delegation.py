"""Delegatsiya — "nomidan" ish ko'rish yordamchilari (yagona manba).

Tashkiliy qoida: YORDAMCHI o'z rahbari (chief — VAZIR yoki ORINBOSAR) nomidan
tadbir va e'lon yaratadi. Yaratuvchining o'zi `created_by`'da audit sifatida qoladi,
ammo jamoatchilikка ko'rinadigan muallif — rahbar (principal).

Bu mantiqdan foydalanadigan joylar:
- events.services.EventService — `on_behalf_of`
- reports.services.ReportService — e'lon `sender`'i
- drafts.services — qoralama publish
- reports.views — tahrirlash/o'chirish ruxsati
"""
from __future__ import annotations

from .enums import RoleName


def resolve_principal(user):
    """Asl muallif (principal): yordamchi bo'lsa — uning rahbari (chief), aks holda — o'zi."""
    if (
        user is not None
        and getattr(user, 'role', None) is not None
        and user.role.name == RoleName.YORDAMCHI
        and user.chief_id
    ):
        return user.chief
    return user


def can_act_as(user, principal_id) -> bool:
    """`user` `principal_id` (rahbar) nomidan ish ko'ra oladimi?

    True bo'ladi agar:
    - foydalanuvchining o'zi shu rahbar bo'lsa, yoki
    - foydalanuvchi shu rahbarning yordamchisi (YORDAMCHI, chief == principal_id) bo'lsa.
    """
    if user is None or principal_id is None:
        return False
    if user.id == principal_id:
        return True
    return (
        getattr(user, 'role', None) is not None
        and user.role.name == RoleName.YORDAMCHI
        and user.chief_id == principal_id
    )
