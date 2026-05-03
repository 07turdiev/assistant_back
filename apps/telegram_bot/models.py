"""TelegramState — production sxemasiga mos.

User'ning Telegram bot bilan login flow holati. Production'da `User.telegram_id`
va `User.telegram_state` (FK) bor edi — biz `User.telegram_id` ni saqlaymiz,
state'ni esa Redis storage (aiogram FSM) yoki shu jadvalda saqlaymiz.

Hozir oddiy yondashuv: state'ni shu jadvalda saqlaymiz (DB-backed FSM).
"""
from django.db import models

from apps.core.models import AuditMixin
from apps.info.enums import TgState


class TelegramState(AuditMixin):
    telegram_id = models.BigIntegerField(unique=True)
    tg_state = models.CharField(max_length=64, choices=TgState.choices, default=TgState.FIRST_STATE)
    # Username login flow vaqtida vaqtinchalik saqlash uchun
    pending_username = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'TelegramState({self.telegram_id}: {self.tg_state})'
