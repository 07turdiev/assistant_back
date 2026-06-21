"""Lookup enum'lar — events/reports apps yaratilguncha bu yerda yashaydi.

Qiymatlar production `assistant.jar` dan to'liq ko'chirilgan (mavjud ma'lumotlar bilan
mos kelishi shart).
"""
from django.db import models


class EventType(models.TextChoices):
    """Tadbir turi — production'da PascalCase saqlanadi (UPPERCASE EMAS!)."""
    COLLECTION = 'Collection', "Yig'ilish"
    PRESIDIUM = 'Presidium', 'Prezidium'
    SELECTOR = 'Selector', 'Selektor'
    DISCUSSION = 'Discussion', 'Muhokama'
    PRESENTATION = 'Presentation', 'Taqdimot'
    MEETING = 'Meeting', 'Uchrashuv'
    FORUM = 'Forum', 'Forum'
    SEMINAR = 'Seminar', 'Seminar'


REPLY_CHOICES = [
    ('REJECTED', {'label_uz': 'Rad etildi', 'label_ru': 'Отклонено', 'reply_for': 'TASK', 'color': '#f56c6c'}),
    ('MUST_REJECT', {'label_uz': 'Rad etilishi kerak', 'label_ru': 'Подлежит отклонению', 'reply_for': 'REQUEST', 'color': '#e6a23c'}),
    ('BY_PHONE', {'label_uz': 'Telefon orqali', 'label_ru': 'По телефону', 'reply_for': 'BOTH', 'color': '#909399'}),
    ('QUICKLY', {'label_uz': 'Tezda', 'label_ru': 'Срочно', 'reply_for': 'BOTH', 'color': '#67c23a'}),
    ('EXECUTE', {'label_uz': 'Bajarish kerak', 'label_ru': 'Выполнить', 'reply_for': 'TASK', 'color': '#409eff'}),
]


class NotificationType(models.TextChoices):
    """Bildirishnoma turi (production NotificationType bilan mos)."""
    NEW = 'NEW', 'Yangi'
    EDITED = 'EDITED', "O'zgartirildi"
    DELETED = 'DELETED', 'Bekor qilindi'
    REMINDED = 'REMINDED', 'Eslatma'
    PRE_EVENT = 'PRE_EVENT', "Boshlang'ich tadbir"
    ANNOUNCEMENT = 'ANNOUNCEMENT', "E'lon"


class TgState(models.TextChoices):
    """Telegram bot FSM holati (production TgState bilan mos)."""
    AUTHENTICATED = 'AUTHENTICATED', "Autentifikatsiya o'tilgan"
    FIRST_STATE = 'FIRST_STATE', 'Login kutilmoqda'
    SECOND_STATE = 'SECOND_STATE', 'Parol kutilmoqda'
