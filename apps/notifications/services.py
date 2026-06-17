"""NotificationService — production `SendNotificationService` ekvivalenti.

Multi-channel dispatch:
- DB'ga `Notification` yozish
- WebSocket push (Channels) — `/ws/` orqali ulangan brauzerlarga
- Web Push (pywebpush) — yopiq tab/orqa fonda ham yetib boradi
- SMS / Email / Telegram — Celery worker yo'q paytda log qilinadi (kelajakda)

Recursive subordinate logikasi: agar tadbir qatnashchisi rahbar bo'lsa,
uning `chief_id` bo'yicha bog'langan yordamchilari ham xabar oladi.
"""
import logging
from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.info.enums import NotificationType
from apps.users.models import User

from .models import Notification
from .webpush import send_to_user as send_webpush_to_user

logger = logging.getLogger(__name__)


# --- Matn shabloni (production EventServiceImpl'dan) ---

EVENT_NOTIFY_TEXTS = {
    NotificationType.NEW: {
        'sms': "Sizga yangi topshiriq!",
        'ws': "Янги топширик!",
        'web_push': "Yangi topshiriq",
    },
    NotificationType.EDITED: {
        'sms': "Topshiriq ma'lumotlari o'zgartirildi:",
        'ws': "Топширикда ўзгариш!",
        'web_push': "Topshiriqda o'zgarish",
    },
    NotificationType.DELETED: {
        'sms': "🛑 Topshiriq bekor qilindi:",
        'ws': "Топширик бекор қилинди",
        'web_push': "Topshiriq bekor qilindi",
    },
    NotificationType.REMINDED: {
        'sms': "🔔 Eslatma!!!",
        'ws': "Эслатма!",
        'web_push': "Eslatma",
    },
    NotificationType.PRE_EVENT: {
        'sms': "Boshlang'ich topshiriq yaratildi",
        'ws': "Бошлангич топширик!",
        'web_push': "Boshlang'ich topshiriq",
    },
}


def _format_event_body(event) -> str:
    """SMS/Email/Web Push uchun tadbir tafsiloti (production format)."""
    speaker = event.speaker
    speaker_full = ' '.join(filter(None, [speaker.last_name, speaker.first_name, speaker.father_name]))
    when = f"{event.date.strftime('%d-%m-%Y')} {event.start_time.strftime('%H:%M')}"
    return (
        f"📂 Mavzu: {event.title}\n"
        f"📖 Mazmuni: {event.description or '—'}\n"
        f"👤 Ijrochi: {speaker_full}\n"
        f"⏰ Ijro muddati: {when}"
    )


# --- Ichki dispatch funksiyalari ---

def _send_websocket(user_id, payload: dict) -> None:
    """Channels group_send orqali real-time push."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    group = f'notify_{user_id}'
    try:
        async_to_sync(channel_layer.group_send)(group, {
            'type': 'notify.message',
            'payload': payload,
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f'WS push xatosi (user={user_id}): {e}')


def _collect_recipients(participants: list) -> list:
    """Production'dagi `findAllByChief_Id` rekursiv mantiq.

    Tadbir qatnashchisi rahbar bo'lsa, uning yordamchilari ham xabar oladi.
    """
    seen = {p.id for p in participants}
    result = list(participants)
    for p in participants:
        for sub in User.objects.filter(chief_id=p.id, enabled=True):
            if sub.id not in seen:
                seen.add(sub.id)
                result.append(sub)
    return result


# --- Asosiy dispatcher ---

class NotificationService:
    """Tadbir bildirishnomalarini ko'p kanalga yuboradi."""

    @classmethod
    def dispatch_event(cls, event, *, notification_type: str, only_user_ids=None) -> None:
        """Asosiy entry: tadbir uchun barcha kanallarga xabar yuborish.

        Args:
            event: Event instance
            notification_type: NotificationType qiymati (NEW, EDITED, DELETED, REMINDED, PRE_EVENT)
            only_user_ids: berilsa — faqat shu foydalanuvchilarga (delegatsiya/yo'naltirish uchun)
        """
        texts = EVENT_NOTIFY_TEXTS.get(notification_type, EVENT_NOTIFY_TEXTS[NotificationType.NEW])

        # 1. Qatnashchilarni yig'ish (recursive subordinate bilan)
        participants = list(event.participants.all())
        recipients = _collect_recipients(participants)
        # Speaker o'zi ham xabardor bo'lsin
        if event.speaker_id and not any(r.id == event.speaker_id for r in recipients):
            recipients.append(event.speaker)

        # Yo'naltirishda — faqat tanlangan foydalanuvchilarga
        if only_user_ids is not None:
            only = set(only_user_ids)
            recipients = [r for r in recipients if r.id in only]

        if not recipients:
            return

        body = _format_event_body(event)
        full_sms = f"{texts['sms']}\n\n{body}"

        # WS uchun event uchun start_time DateTime bo'lishi kerak
        start_dt = datetime.combine(event.date, event.start_time)
        end_dt = datetime.combine(event.date, event.end_time)

        # Bulk SMS/Email destinationlarini yig'ib olamiz (har user uchun alohida emas, bir batch)
        sms_phones: list[str] = []
        emails: list[str] = []

        for user in recipients:
            # 2. DB ga Notification yozish (audit/history)
            Notification.objects.create(
                user_id=user.id,
                title=event.title,
                notification_type=notification_type,
                event_id=event.id,
                date=event.date,
                start_time=start_dt,
                end_time=end_dt,
                is_important=event.is_important,
                seen=False,
            )

            # 3. WebSocket real-time (ochiq tab uchun)
            _send_websocket(user.id, {
                'channel': 'notify',
                'type': notification_type,
                'title': event.title,
                'event_id': str(event.id),
                'message': texts['ws'],
                'is_important': event.is_important,
            })

            # 4. Web Push (yopiq tab uchun)
            try:
                send_webpush_to_user(
                    user.id,
                    title=texts['web_push'],
                    body=event.title,
                    url=f'/events/{event.id}',
                    is_important=event.is_important,
                    tag=f'event-{event.id}',
                    data={'event_id': str(event.id), 'type': notification_type},
                )
            except Exception as e:  # noqa: BLE001
                logger.exception(f'Web Push xatosi (user={user.id}): {e}')

            # 5. Telegram (TG_BOT_TOKEN bo'lsa real yuboriladi)
            if user.telegram_id:
                try:
                    from apps.telegram_bot.notify import send_message as send_tg
                    send_tg(user.telegram_id, full_sms)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f'Telegram dispatch xatosi (user={user.id}): {e}')

            # 6. SMS / Email destinationlarini batch'ga yig'amiz
            phone = (user.phone_number or '').strip()
            if phone:
                sms_phones.append(phone)
            if user.email:
                emails.append(user.email)

        # 7. Bulk SMS yuborish (provider bitta API call'da bir nechta xabar qabul qiladi)
        if sms_phones:
            try:
                from .sms import send_to_many as send_sms_batch
                send_sms_batch(sms_phones, full_sms)
            except Exception as e:  # noqa: BLE001
                logger.warning(f'SMS batch dispatch xatosi: {e}')

        # 8. Bulk Email yuborish
        if emails:
            try:
                from .email import send_to_many as send_email_batch
                send_email_batch(emails, full_sms, subject=f'Smart assistant: {event.title}')
            except Exception as e:  # noqa: BLE001
                logger.warning(f'Email batch dispatch xatosi: {e}')

    @classmethod
    def dispatch_pre_event(cls, pre_event, *, recipient_ids: list) -> None:
        """PreEvent yaratilganda xabar (production'da PRE_EVENT type)."""
        for user_id in recipient_ids:
            Notification.objects.create(
                user_id=user_id,
                title=pre_event.title,
                notification_type=NotificationType.PRE_EVENT,
                pre_event_id=pre_event.id,
                date=pre_event.date,
                start_time=pre_event.start_time,
                end_time=pre_event.end_time,
                is_important=False,
                seen=False,
            )
            _send_websocket(user_id, {
                'channel': 'notify',
                'type': NotificationType.PRE_EVENT,
                'title': pre_event.title,
                'pre_event_id': str(pre_event.id),
                'message': EVENT_NOTIFY_TEXTS[NotificationType.PRE_EVENT]['ws'],
            })

    @classmethod
    def dispatch_announcement(cls, announcement, *, exclude_sender: bool = True) -> int:
        """Umumiy e'lon — barcha faol foydalanuvchilarga in-app bildirishnoma + WS.

        Mavjud bildirishnoma tizimini qayta ishlatadi: har foydalanuvchiga `Notification`
        yoziladi (qo'ng'iroqcha + o'qilmagan badge + per-user "seen" avtomatik ishlaydi)
        va `notify` kanali orqali real-time WS push yuboriladi.

        SMS/Email YUBORILMAYDI — umumiy e'lon spam bo'lmasligi uchun.

        Returns: xabardor qilingan foydalanuvchilar soni.
        """
        title = (announcement.description or '').strip()
        if len(title) > 120:
            title = title[:117] + '...'

        recipients = User.objects.filter(enabled=True)

        # Auditoriya: bo'lim(lar) tanlangan bo'lsa — faqat o'sha bo'limlar (va MPTT ichidagilar)
        target_dirs = list(announcement.target_directions.all())
        if target_dirs:
            from apps.directions.models import Direction
            target_qs = Direction.objects.filter(id__in=[d.id for d in target_dirs])
            all_dir_ids = list(
                Direction.objects.get_queryset_descendants(target_qs, include_self=True)
                .values_list('id', flat=True)
            )
            recipients = recipients.filter(direction_id__in=all_dir_ids)

        # Muallif (sender=rahbar) va asl yaratuvchi (created_by=yordamchi) o'ziga e'lon olmaydi
        exclude_ids = set()
        if exclude_sender and announcement.sender_id:
            exclude_ids.add(announcement.sender_id)
        if announcement.created_by_id:
            exclude_ids.add(announcement.created_by_id)
        if exclude_ids:
            recipients = recipients.exclude(pk__in=exclude_ids)
        recipient_ids = list(recipients.values_list('id', flat=True))
        if not recipient_ids:
            return 0

        # Proksi: har bir qabul qiluvchining yordamchisi (YORDAMCHI, chief=qabul qiluvchi)
        # ham e'lonni oladi — "ikkala hisob bir xil" (muallif/yaratuvchidan tashqari).
        from apps.users.enums import RoleName
        assistant_ids = list(
            User.objects.filter(
                chief_id__in=recipient_ids,
                role__name=RoleName.YORDAMCHI,
                enabled=True,
            )
            .exclude(pk__in=exclude_ids)
            .values_list('id', flat=True),
        )
        if assistant_ids:
            recipient_ids = list(dict.fromkeys([*recipient_ids, *assistant_ids]))

        sender = announcement.sender
        sender_name = ''
        if sender:
            sender_name = ' '.join(filter(None, [sender.last_name, sender.first_name])) or sender.username

        # 1. DB — har foydalanuvchiga Notification (bulk INSERT)
        Notification.objects.bulk_create([
            Notification(
                user_id=uid,
                title=title or "E'lon",
                notification_type=NotificationType.ANNOUNCEMENT,
                report_id=announcement.id,
                is_important=False,
                seen=False,
            )
            for uid in recipient_ids
        ])

        # 2. WS real-time push — `notify` kanali orqali qo'ng'iroqchaga
        ws_message = "📢 Yangi e'lon" + (f' — {sender_name}' if sender_name else '')
        for uid in recipient_ids:
            _send_websocket(uid, {
                'channel': 'notify',
                'type': NotificationType.ANNOUNCEMENT,
                'title': title or "E'lon",
                'report_id': str(announcement.id),
                'message': ws_message,
                'is_important': False,
            })

        # 3. Telegram — telegram_id bor qabul qiluvchilarga (plain matn)
        tg_ids = list(
            User.objects.filter(pk__in=recipient_ids, telegram_id__isnull=False)
            .values_list('telegram_id', flat=True),
        )
        if tg_ids:
            try:
                from apps.telegram_bot.notify import send_message as send_tg
                tg_text = f"{ws_message}\n\n{announcement.description or ''}".strip()
                for tg_id in tg_ids:
                    send_tg(tg_id, tg_text, parse_mode='')
            except Exception as e:  # noqa: BLE001
                logger.warning(f"E'lon Telegram dispatch xatosi: {e}")

        return len(recipient_ids)

    @classmethod
    def send_test_to_user(cls, user) -> int:
        """`POST /api/webpush/test/` — har bir subscription'ga test push."""
        return send_webpush_to_user(
            user.id,
            title='Smart assistant — test',
            body='Bildirishnomalar to\'g\'ri sozlangan ✅',
            url='/notifications/settings',
            tag='test',
        )
