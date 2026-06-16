"""Report — production sxemasiga to'liq mos."""
from django.db import models

from apps.core.models import AuditMixin

from .enums import Reply, ReportKind


class Report(AuditMixin):
    """Hisobot — topshiriq (task) yoki e'lon (announcement).

    - **TASK**: Premier/Head → yordamchilariga (1:1, receiver bor, javobli)
    - **ANNOUNCEMENT**: istalgan foydalanuvchi → hammaga (receiver yo'q, javobsiz)

    Maydonlar:
    - kind (TASK | ANNOUNCEMENT | REQUEST-legacy)
    - sender (User), receiver (User, nullable — e'londa yo'q)
    - description (text)
    - reply (Reply enum, nullable — faqat task uchun)
    - reply_at (DateTime, nullable)
    - notify_time (Integer, nullable — eslatma vaqti minutlarda)
    - seen (Boolean)
    """

    kind = models.CharField(
        max_length=16,
        choices=ReportKind.choices,
        default=ReportKind.TASK,
        db_index=True,
    )

    sender = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports_sent',
    )
    receiver = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reports_received',
    )
    # Umumiy e'lon auditoriyasi: bo'sh = HAMMAGA, aks holda shu bo'limlar (va ichidagilar)
    target_directions = models.ManyToManyField(
        'directions.Direction',
        blank=True,
        related_name='announcements',
    )
    description = models.TextField()

    reply = models.CharField(max_length=32, choices=Reply.choices, null=True, blank=True)
    reply_at = models.DateTimeField(null=True, blank=True)

    notify_time = models.IntegerField(null=True, blank=True)  # minutlarda
    seen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['receiver', '-created_at']),
            models.Index(fields=['reply']),
        ]

    def __str__(self) -> str:
        return f'Report({self.sender_id} → {self.receiver_id})'

    @property
    def is_active(self) -> bool:
        """Faol — hali javob berilmagan."""
        return self.reply is None
