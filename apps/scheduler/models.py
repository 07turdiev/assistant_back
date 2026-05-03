"""ScheduledTask — production `Schedule` jadvaliga mos.

Production sxemasi:
- id (UUID), createdAt, updatedAt
- eventId (UUID), userId (UUID)
- schedulerTime (DateTime — qachon ishga tushishi kerak)
- notifyTime (Integer — eslatma vaqti minutlarda, audit uchun)

Yangi qo'shildi:
- kind (ScheduledTaskKind) — task turi (event reminder / report followup / ...)
- executed (bool) — bajarilgan
- locked_until (DateTime) — multi-worker locking (TODO: prod'da kerak)
"""
import uuid

from django.db import models
from django.utils import timezone


class ScheduledTaskKind(models.TextChoices):
    EVENT_REMINDER = 'EVENT_REMINDER', 'Tadbir eslatmasi'
    REPORT_FOLLOWUP = 'REPORT_FOLLOWUP', 'Hisobot eslatmasi'


class ScheduledTask(models.Model):
    """Rejalashtirilgan vazifa.

    AuditMixin ishlatmaymiz — bu task'lar tizim tomonidan yaratiladi,
    user audit izi kerak emas.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    kind = models.CharField(max_length=32, choices=ScheduledTaskKind.choices)

    # Tegishli obyekt ID'lari (bare UUID — FK yo'q, audit uchun)
    event_id = models.UUIDField(null=True, blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    notify_time = models.IntegerField(null=True, blank=True)  # minut

    run_at = models.DateTimeField(db_index=True)
    executed = models.BooleanField(default=False, db_index=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default='')

    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['run_at']
        indexes = [
            models.Index(fields=['executed', 'run_at']),
            models.Index(fields=['event_id']),
        ]

    def __str__(self) -> str:
        return f'{self.kind}@{self.run_at} (executed={self.executed})'
