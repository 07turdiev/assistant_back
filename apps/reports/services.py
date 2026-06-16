"""Report biznes mantig'i — faqat umumiy e'lon (Topshiriq moduli olib tashlandi)."""
import logging

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.users.models import User

from .enums import ReportKind
from .models import Report

logger = logging.getLogger(__name__)


class ReportService:

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        description: str,
        sender: User,
        target_direction_ids: list | None = None,
    ) -> list[Report]:
        """Umumiy e'lon yaratadi (istalgan foydalanuvchi).

        `target_direction_ids` bo'sh bo'lsa — HAMMAGA; aks holda shu bo'limlarga
        (va MPTT bo'yicha ichidagi bo'limlarga).
        """
        description = (description or '').strip()
        if not description:
            raise ValidationError({'description': "Bo'sh bo'lishi mumkin emas"})
        return cls._create_announcement(description, sender, target_direction_ids)

    @staticmethod
    def _create_announcement(
        description: str, sender: User, target_direction_ids: list | None = None,
    ) -> list[Report]:
        r = Report.objects.create(
            kind=ReportKind.ANNOUNCEMENT,
            sender=sender,
            receiver=None,
            description=description,
        )
        if target_direction_ids:
            from apps.directions.models import Direction
            dirs = list(Direction.objects.filter(id__in=target_direction_ids))
            if dirs:
                r.target_directions.set(dirs)

        def _dispatch():
            try:
                from apps.notifications.services import NotificationService
                NotificationService.dispatch_announcement(r)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"E'lon tarqatish xatosi: {e}")

        transaction.on_commit(_dispatch)
        return [r]
