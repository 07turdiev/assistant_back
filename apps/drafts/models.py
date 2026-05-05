"""EventDraft va ReportDraft — AI tomonidan yaratilgan qoralamalar.

Oqim:
1. Foydalanuvchi Telegram'da ovozli xabar yuboradi
2. STT → matn → AI parser → JSON
3. Backend qoralama yaratadi (status=PENDING_REVIEW)
4. Belgilangan xodim (assignee) saytda ko'radi, tahrir qiladi
5. "Joylash" tugmasi → Event yoki Report obyekti yaratiladi
   va qoralama status=PUBLISHED ga o'tadi
"""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import AuditMixin

from .enums import DraftSource, DraftStatus


def _voice_upload_to(instance, filename: str) -> str:
    """voice/{YYYY}/{MM}/{uuid}_{filename}"""
    today = timezone.now()
    return f'voice/{today.year}/{today.month:02d}/{instance.pk}_{filename}'


def _default_voice_expires_at():
    """Ovoz fayl `VOICE_FILE_RETENTION_DAYS` (default 30) kunlik amal qiladi."""
    days = getattr(settings, 'VOICE_FILE_RETENTION_DAYS', 30)
    return timezone.now() + timedelta(days=days)


class _DraftBase(AuditMixin):
    """Event va Report draftlari uchun umumiy maydonlar."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')

    status = models.CharField(
        max_length=32,
        choices=DraftStatus.choices,
        default=DraftStatus.PENDING_REVIEW,
        db_index=True,
    )

    # Routing — kim tahrir qilib joylashi kerak
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Qoralamani tahrir qilib joylashi kerak bo\'lgan xodim',
    )
    target_direction = models.ForeignKey(
        'directions.Direction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Bo\'lim aytilgan bo\'lsa — bu yerda. assigned_to esa shu bo\'lim HEAD\'i',
    )

    # AI tomonidan extract qilingan, lekin DB'da topilmagan ism-familiyalar
    unresolved_participant_names = models.JSONField(
        default=list,
        blank=True,
        help_text='AI matnda topib olgan, lekin User jadvalida moslashmagan ismlar',
    )

    is_important = models.BooleanField(default=False)
    notify_minutes_before = models.JSONField(default=list, blank=True)

    # Manba va audit
    source = models.CharField(
        max_length=32,
        choices=DraftSource.choices,
        default=DraftSource.MANUAL,
    )
    raw_transcript = models.TextField(
        blank=True,
        default='',
        help_text='STT chiqargan asl matn (audit uchun)',
    )
    parsed_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='AI qaytargan asl JSON (debug uchun)',
    )
    voice_file = models.FileField(
        upload_to=_voice_upload_to,
        null=True,
        blank=True,
        help_text='Ovozli xabarning asl fayli',
    )
    voice_file_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        default=_default_voice_expires_at,
        help_text='Ovoz fayl shu sanadan keyin Celery task tomonidan o\'chiriladi',
    )

    # Joylash audit
    published_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        abstract = True

    @property
    def is_pending(self) -> bool:
        return self.status == DraftStatus.PENDING_REVIEW

    @property
    def is_published(self) -> bool:
        return self.status == DraftStatus.PUBLISHED


class EventDraft(_DraftBase):
    """Tadbir qoralamasi.

    Joylanganda `Event` obyekti yaratiladi va `published_event` shunga ulanadi.
    """

    # Event-specific maydonlar (barchasi nullable — partial fill bo'lishi mumkin)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default='')
    is_private = models.BooleanField(default=False)

    # Event majburiy maydonlari — AI to'ldirmaydi, foydalanuvchi tahrirda tanlaydi
    sphere = models.CharField(max_length=128, blank=True, default='', help_text='Joylashdan oldin tanlanishi kerak')
    event_type = models.CharField(max_length=32, blank=True, default='', help_text='Joylashdan oldin tanlanishi kerak')
    speaker = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Ma\'ruzachi — joylashdan oldin tanlanadi (default: assigned_to)',
    )

    suggested_participants = models.ManyToManyField(
        'users.User',
        blank=True,
        related_name='+',
        help_text='AI taklif qilgan qatnashchilar (DB\'dan topilgan)',
    )

    # Joylangach — yaratilgan Event'ga link
    published_event = models.OneToOneField(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_draft',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['created_by', '-created_at']),
        ]
        verbose_name = 'Tadbir qoralamasi'
        verbose_name_plural = 'Tadbir qoralamalari'

    def __str__(self) -> str:
        return f'EventDraft({self.title} — {self.status})'


class ReportDraft(_DraftBase):
    """Topshiriq/so'rov qoralamasi.

    Joylanganda `Report` obyekti yaratiladi (sender = created_by, receiver = assigned_to).
    """

    # Qo'shma topshiriq holati uchun — bir nechta xodimlar nomidan
    suggested_participants = models.ManyToManyField(
        'users.User',
        blank=True,
        related_name='+',
        help_text='AI taklif qilgan qo\'shma javobgar shaxslar',
    )

    deadline_text = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='"3 kun ichida" kabi so\'z bilan aytilgan muddat (description ichida ham bo\'lishi mumkin)',
    )

    published_report = models.OneToOneField(
        'reports.Report',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_draft',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['created_by', '-created_at']),
        ]
        verbose_name = 'Topshiriq qoralamasi'
        verbose_name_plural = 'Topshiriq qoralamalari'

    def __str__(self) -> str:
        return f'ReportDraft({self.title} — {self.status})'
