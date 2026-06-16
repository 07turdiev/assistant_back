"""Report biznes mantig'i — production `ReportServiceImpl` ekvivalenti.

Asosiy oqim:
1. **Task yaratish** (Premier/Head → yordamchilariga):
   - Sender = Premier yoki Head
   - Receiver = sender'ning yordamchilari (`findAllByChief_Id(sender.id)`)
   - Har receiver uchun alohida Report yozuvi
   - WS push channel `report_{receiver_id}` payload `{type:"Task", message:"Tezkor topshiriq!"}`

2. **Request yaratish** (Assistant → rahbariga):
   - Sender = Assistant (`role.name == ASSISTANT` yoki `ASSISTANT_PREMIER`)
   - Receiver = sender.chief
   - Bitta Report yozuvi
   - WS push channel `report_{chief_id}` payload `{type:"Request", message:"Tezkor so'rov!"}`

3. **Reply** — receiver javob beradi:
   - Reply enum yoki notify_time (eslatish vaqti)
   - Ikkalasi ham bo'sh → 400 "Eslatish vaqti ham javob ham tanlanmadi"
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.users.enums import RoleName
from apps.users.models import User

from .enums import Reply, ReportKind
from .models import Report

logger = logging.getLogger(__name__)


# Topshiriq (TASK) faqat shu rollar tomonidan beriladi
TASK_SENDER_ROLES = (RoleName.PREMIER_MINISTER, RoleName.HEAD)


def _send_ws(user_id, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(f'report_{user_id}', {
            'type': 'report.message',
            'payload': payload,
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f'WS report push xatosi (user={user_id}): {e}')


def _is_task_sender(user: User) -> bool:
    return bool(user.role and user.role.name in TASK_SENDER_ROLES)


class ReportService:

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        description: str,
        sender: User,
        kind: str = ReportKind.TASK,
        target_direction_ids: list | None = None,
    ) -> list[Report]:
        """`kind` bo'yicha topshiriq (TASK) yoki umumiy e'lon (ANNOUNCEMENT) yaratadi.

        - TASK: faqat vazir / bo'lim boshlig'i → yordamchilariga
        - ANNOUNCEMENT: istalgan foydalanuvchi → hammaga yoki tanlangan bo'limlarga
          (`target_direction_ids` bo'sh bo'lsa — HAMMAGA)

        Returns: yaratilgan Report yozuvlari ro'yxati.
        """
        description = (description or '').strip()
        if not description:
            raise ValidationError({'description': "Bo'sh bo'lishi mumkin emas"})

        if kind == ReportKind.ANNOUNCEMENT:
            return cls._create_announcement(description, sender, target_direction_ids)

        # Aks holda — topshiriq (faqat Premier/Head)
        if not _is_task_sender(sender):
            raise PermissionDenied("Topshiriq berish faqat vazir va bo'lim boshliqlariga ruxsat")
        return cls._create_tasks(description, sender)

    @staticmethod
    def _create_tasks(description: str, sender: User) -> list[Report]:
        """Premier/Head → yordamchilariga (har biri uchun alohida Report)."""
        assistants = list(User.objects.filter(chief_id=sender.id, enabled=True))
        if not assistants:
            raise ValidationError("Sizning yordamchilaringiz yo'q. Avval yordamchi tayinlang.")

        reports = []
        for assistant in assistants:
            r = Report.objects.create(
                kind=ReportKind.TASK, sender=sender, receiver=assistant, description=description,
            )
            reports.append(r)
            _send_ws(assistant.id, {
                'channel': 'report',
                'type': 'Task',
                'message': "Tezkor topshiriq!",
                'report_id': str(r.id),
            })

            # Telegram (TG_BOT_TOKEN bo'lsa real yuboriladi)
            if assistant.telegram_id:
                try:
                    from apps.telegram_bot.notify import send_message as send_tg
                    send_tg(assistant.telegram_id, f"🔔 Tezkor topshiriq!\n\n{description}")
                except Exception as e:  # noqa: BLE001
                    logger.warning(f'TG dispatch xatosi: {e}')

        # Bulk SMS + Email — barcha yordamchilarga bir API call
        sms_phones = [a.phone_number.strip() for a in assistants if a.phone_number]
        emails_list = [a.email for a in assistants if a.email]
        sms_text = f"Tezkor topshiriq!\n\n{description}"

        if sms_phones:
            try:
                from apps.notifications.sms import send_to_many as send_sms
                send_sms(sms_phones, sms_text)
            except Exception as e:  # noqa: BLE001
                logger.warning(f'Report SMS dispatch xatosi: {e}')
        if emails_list:
            try:
                from apps.notifications.email import send_to_many as send_email
                send_email(emails_list, sms_text, subject='Tezkor topshiriq')
            except Exception as e:  # noqa: BLE001
                logger.warning(f'Report Email dispatch xatosi: {e}')

        return reports

    @staticmethod
    def _create_announcement(
        description: str, sender: User, target_direction_ids: list | None = None,
    ) -> list[Report]:
        """Istalgan foydalanuvchi → umumiy e'lon (bitta Report, receiver yo'q).

        `target_direction_ids` bo'sh bo'lsa — HAMMAGA; aks holda shu bo'limlarga
        (va MPTT bo'yicha ichidagi bo'limlarga). Tarqatish commit'dan keyin
        NotificationService.dispatch_announcement orqali bajariladi.
        """
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

    @classmethod
    @transaction.atomic
    def reply(cls, *, report: Report, user: User, reply: str | None = None,
              notify_time: int | None = None) -> Report:
        """Hisobotga javob berish.

        - reply yoki notify_time'dan kamida biri bo'lishi shart
        - faqat receiver javob bera oladi
        """
        if report.kind == ReportKind.ANNOUNCEMENT:
            raise ValidationError("E'longa javob berilmaydi")

        if report.receiver_id != user.id and not user.is_superuser:
            raise PermissionDenied("Faqat hisobot oluvchi javob bera oladi")

        if not reply and notify_time is None:
            raise ValidationError("Eslatish vaqti ham javob ham tanlanmadi")

        # Reply enum tekshiruvi
        if reply:
            valid = [c[0] for c in Reply.choices]
            if reply not in valid:
                raise ValidationError({'reply': f"Yaroqsiz qiymat. Mumkin: {valid}"})
            report.reply = reply
            report.reply_at = timezone.now()

        if notify_time is not None:
            if notify_time <= 0:
                raise ValidationError({'notify_time': "Musbat son bo'lishi kerak"})
            report.notify_time = notify_time

        report.seen = True
        report.save()

        # Eslatmani rejalashtirish — notify_time bo'lsa va hali javob berilmagan bo'lsa
        if notify_time is not None and not reply:
            try:
                from apps.scheduler.services import schedule_report_followup
                schedule_report_followup(report, notify_time)
            except Exception as e:  # noqa: BLE001
                logger.warning(f'Report followup rejalashtirish xatosi: {e}')
        # Final reply kelgan bo'lsa — kutayotgan eslatmani bekor qilamiz
        elif reply:
            try:
                from apps.scheduler.services import cancel_report_followups
                cancel_report_followups(report.id)
            except Exception as e:  # noqa: BLE001
                logger.warning(f'Report followup bekor qilish xatosi: {e}')

        # Sender'ga javob keldi push
        is_task = _is_task_sender(report.sender) if report.sender else False
        ws_type = 'Task' if is_task else 'Request'
        message = "Tezkor topshiriqqa javob berildi" if is_task else "Tezkor so'rovga javob berildi"
        if notify_time is not None and not reply:
            message = f"Tezkor so'rovga {notify_time} minutdan so'ng javob beriladi"

        if report.sender_id:
            _send_ws(report.sender_id, {
                'channel': 'report',
                'type': ws_type,
                'message': message,
                'report_id': str(report.id),
            })

        return report
