"""Reply enum — production Reply.java bilan to'liq mos.

Har bir qiymat: (label_uz, label_ru, reply_for, color)
- reply_for: TASK | REQUEST | BOTH (qaysi turdagi hisobotga javob bera oladi)
- color: frontend tag rangi
"""
from django.db import models


class Reply(models.TextChoices):
    REJECTED = 'REJECTED', 'Rad etildi'
    MUST_REJECT = 'MUST_REJECT', 'Rad etilishi kerak'
    BY_PHONE = 'BY_PHONE', 'Telefon orqali'
    QUICKLY = 'QUICKLY', 'Tezda'
    EXECUTE = 'EXECUTE', 'Bajarish kerak'


# Frontend va info endpoint uchun metadata
REPLY_META = {
    'REJECTED': {'label_uz': 'Rad etildi', 'label_ru': 'Отклонено',
                 'reply_for': 'TASK', 'color': '#f56c6c'},
    'MUST_REJECT': {'label_uz': 'Rad etilishi kerak', 'label_ru': 'Подлежит отклонению',
                    'reply_for': 'REQUEST', 'color': '#e6a23c'},
    'BY_PHONE': {'label_uz': 'Telefon orqali', 'label_ru': 'По телефону',
                 'reply_for': 'BOTH', 'color': '#909399'},
    'QUICKLY': {'label_uz': 'Tezda', 'label_ru': 'Срочно',
                'reply_for': 'BOTH', 'color': '#67c23a'},
    'EXECUTE': {'label_uz': 'Bajarish kerak', 'label_ru': 'Выполнить',
                'reply_for': 'TASK', 'color': '#409eff'},
}


# Hisobot turi (sender roli bo'yicha aniqlanadi)
class ReportKind:
    TASK = 'TASK'        # Premier/Head → yordamchiga
    REQUEST = 'REQUEST'  # Assistant → rahbariga
