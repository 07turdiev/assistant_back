"""Eskirgan voice fayllarni diskdan o'chiradi.

Foydalanish:
    python manage.py cleanup_voice_files                # eskirganlarini o'chiradi
    python manage.py cleanup_voice_files --dry-run      # nima o'chirilishini ko'rsatadi
    python manage.py cleanup_voice_files --older-than 7 # 7 kundan oldingilarni majburan

Cron'da kuniga 1 marta ishga tushirish tavsiya etiladi:
    0 3 * * * cd /opt/assistant && .venv/bin/python manage.py cleanup_voice_files
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.drafts.models import EventDraft, ReportDraft


class Command(BaseCommand):
    help = 'Eskirgan voice fayllarni diskdan va DB FileField\'idan tozalaydi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Faqat ko\'rsatadi, o\'chirmaydi',
        )
        parser.add_argument(
            '--older-than',
            type=int,
            default=None,
            help='N kundan eski fayllarni o\'chiradi (voice_file_expires_at o\'rniga)',
        )

    def handle(self, *args, **options):
        dry_run: bool = options['dry_run']
        older_than: int | None = options['older_than']

        if older_than is not None:
            cutoff = timezone.now() - timedelta(days=older_than)
            voice_filter = Q(created_at__lte=cutoff)
            mode = f'created_at <= {cutoff.isoformat()}'
        else:
            now = timezone.now()
            voice_filter = Q(voice_file_expires_at__isnull=False) & Q(voice_file_expires_at__lte=now)
            mode = f'voice_file_expires_at <= {now.isoformat()}'

        total_deleted = 0
        total_skipped = 0

        for model_cls, label in ((EventDraft, 'EventDraft'), (ReportDraft, 'ReportDraft')):
            qs = model_cls.objects.filter(voice_filter).exclude(voice_file='')
            count = qs.count()
            self.stdout.write(f'{label}: {count} ta nomzod ({mode})')

            for draft in qs.iterator(chunk_size=200):
                if not draft.voice_file:
                    total_skipped += 1
                    continue
                path = draft.voice_file.name
                try:
                    if dry_run:
                        self.stdout.write(f'  [DRY] {label} {draft.pk} → {path}')
                    else:
                        draft.voice_file.delete(save=False)
                        # FileField bo'sh holatga o'tkazib, expires'ni ham tozalaymiz
                        model_cls.objects.filter(pk=draft.pk).update(
                            voice_file='',
                            voice_file_expires_at=None,
                        )
                    total_deleted += 1
                except Exception as e:  # noqa: BLE001
                    self.stderr.write(f'  XATO: {label} {draft.pk} ({path}): {e}')
                    total_skipped += 1

        action = 'O\'chirilishi mumkin' if dry_run else 'O\'chirildi'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action}: {total_deleted} ta fayl. O\'tkazib yuborilgan: {total_skipped}',
        ))
