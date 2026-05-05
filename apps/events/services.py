"""Event biznes mantig'i — production `EventServiceImpl` ekvivalenti."""
import logging
from datetime import date, datetime, time

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.attachments.models import Attachment
from apps.attachments.services import remove_attachment, secure_upload
from apps.directions.models import Direction
from apps.info.enums import NotificationType
from apps.users.enums import RoleName
from apps.users.models import User

from .models import Event, EventParticipant, PreEvent, Visitor

logger = logging.getLogger(__name__)


def _dispatch_notification(event, notification_type: str) -> None:
    """NotificationService'ga circular import'ni oldini olish uchun lazy import."""
    try:
        from apps.notifications.services import NotificationService
        NotificationService.dispatch_event(event, notification_type=notification_type)
    except Exception as e:  # noqa: BLE001
        # Notification xatosi event yaratish/tahrirlashni buzmasin
        logger.exception(f'Notification dispatch xatosi ({notification_type}): {e}')


def _schedule_reminders(event) -> None:
    """notify_time bo'yicha reminder'larni rejalashtirish."""
    try:
        from apps.scheduler.services import schedule_event_reminders
        schedule_event_reminders(event)
    except Exception as e:  # noqa: BLE001
        logger.exception(f'Schedule reminders xatosi (event={event.id}): {e}')


def _cancel_reminders(event_id) -> None:
    try:
        from apps.scheduler.services import cancel_event_reminders
        cancel_event_reminders(event_id)
    except Exception as e:  # noqa: BLE001
        logger.exception(f'Cancel reminders xatosi (event={event_id}): {e}')


class EventService:
    """Tadbir yaratish/tahrirlash/o'chirish."""

    @staticmethod
    def _validate_in_future(event_date: date, end_time: time):
        end_dt = datetime.combine(event_date, end_time, tzinfo=timezone.get_current_timezone())
        if end_dt < timezone.now():
            raise ValidationError("Hozirgi vaqtdan oldin uchun topshiriq qo'shib bo'lmaydi")

    @staticmethod
    def _resolve_speaker(speaker_id):
        try:
            return User.objects.get(pk=speaker_id)
        except User.DoesNotExist as exc:
            raise ValidationError({'speaker_id': "Ma'ruzachi topilmadi"}) from exc

    @staticmethod
    def _resolve_participants(participant_ids):
        users = list(User.objects.filter(pk__in=participant_ids))
        if len(users) != len(set(participant_ids)):
            found_ids = {str(u.id) for u in users}
            missing = set(map(str, participant_ids)) - found_ids
            raise ValidationError({'participant_ids': f"Foydalanuvchilar topilmadi: {missing}"})
        return users

    @staticmethod
    def _resolve_direction(user: User, direction_id):
        if direction_id:
            try:
                return Direction.objects.get(pk=direction_id)
            except Direction.DoesNotExist as exc:
                raise ValidationError({'direction_id': "Yo'nalish topilmadi"}) from exc
        if user.direction_id:
            return user.direction
        raise ValidationError("Yo'nalishni aniqlab bo'lmadi (foydalanuvchi yoki dto'da yo'q)")

    @classmethod
    @transaction.atomic
    def create(cls, *, validated_data, files, user: User) -> Event:
        cls._validate_in_future(validated_data['date'], validated_data['end_time'])

        speaker = cls._resolve_speaker(validated_data['speaker_id'])
        participants = cls._resolve_participants(validated_data['participant_ids'])
        direction = cls._resolve_direction(user, validated_data.get('direction_id'))

        event = Event.objects.create(
            title=validated_data['title'],
            description=validated_data.get('description', ''),
            date=validated_data['date'],
            start_time=validated_data['start_time'],
            end_time=validated_data['end_time'],
            address=validated_data.get('address', ''),
            sphere=validated_data['sphere'],
            type=validated_data['type'],
            is_private=validated_data.get('is_private', False),
            is_important=validated_data.get('is_important', False),
            conclusion=validated_data.get('conclusion', ''),
            serial_number=validated_data.get('serial_number') or None,
            notify_time=validated_data.get('notify_time_list') or [],
            direction=direction,
            speaker=speaker,
        )

        # Qatnashchilar
        EventParticipant.objects.bulk_create([
            EventParticipant(event=event, user=u) for u in participants
        ])

        # Visitors
        for v in validated_data.get('visitors') or []:
            Visitor.objects.create(event=event, **v)

        # Fayllar
        for f in files or []:
            att = secure_upload(f, target='documents')
            att.file_event = event
            att.save(update_fields=['file_event'])

        # PreEvent o'chirish
        pre_event_id = validated_data.get('pre_event_id')
        if pre_event_id:
            PreEvent.objects.filter(pk=pre_event_id).delete()

        # Bildirishnoma — barcha qatnashchilar va recursive yordamchilarga
        transaction.on_commit(lambda: _dispatch_notification(event, NotificationType.NEW))

        # Reminder'larni rejalashtirish (har notify_time uchun)
        transaction.on_commit(lambda: _schedule_reminders(event))

        return event

    @classmethod
    @transaction.atomic
    def update(cls, event: Event, *, validated_data, files, user: User) -> Event:
        if event.created_by_id != user.id and not user.is_superuser:
            raise PermissionDenied("Faqat tadbir yaratuvchisi tahrirlashi mumkin")

        cls._validate_in_future(validated_data['date'], validated_data['end_time'])

        speaker = cls._resolve_speaker(validated_data['speaker_id'])
        participants = cls._resolve_participants(validated_data['participant_ids'])
        direction = cls._resolve_direction(user, validated_data.get('direction_id'))

        # Asosiy maydonlar
        for field in ('title', 'description', 'date', 'start_time', 'end_time',
                      'address', 'sphere', 'type', 'is_private', 'is_important',
                      'conclusion'):
            if field in validated_data:
                setattr(event, field, validated_data[field])
        if 'serial_number' in validated_data:
            event.serial_number = validated_data['serial_number'] or None
        if 'notify_time_list' in validated_data:
            event.notify_time = validated_data['notify_time_list'] or []
        event.speaker = speaker
        event.direction = direction
        event.save()

        # Qatnashchilar (replace strategiyasi)
        existing_user_ids = set(event.participants.values_list('id', flat=True))
        new_user_ids = {p.id for p in participants}
        to_remove = existing_user_ids - new_user_ids
        to_add = new_user_ids - existing_user_ids
        if to_remove:
            EventParticipant.objects.filter(event=event, user_id__in=to_remove).delete()
        if to_add:
            EventParticipant.objects.bulk_create([
                EventParticipant(event=event, user_id=uid) for uid in to_add
            ])

        # Visitors (replace strategiyasi — production'da ham shu)
        if 'visitors' in validated_data:
            event.visitors.all().delete()
            for v in validated_data['visitors']:
                Visitor.objects.create(event=event, **v)

        # Fayllar — yangi yuklash
        for f in files or []:
            att = secure_upload(f, target='documents')
            att.file_event = event
            att.save(update_fields=['file_event'])

        # O'chirilgan fayllar
        for fid in validated_data.get('deleted_file_ids', []):
            try:
                att = Attachment.objects.get(pk=fid, file_event=event)
            except Attachment.DoesNotExist:
                continue
            remove_attachment(att)

        # Bildirishnoma EDITED
        transaction.on_commit(lambda: _dispatch_notification(event, NotificationType.EDITED))

        # Eski reminder'larni bekor qilib qaytadan rejalashtirish
        # (notify_time o'zgargan bo'lishi mumkin)
        event_id = event.id
        transaction.on_commit(lambda: _cancel_reminders(event_id))
        transaction.on_commit(lambda: _schedule_reminders(event))

        return event

    @classmethod
    @transaction.atomic
    def delete(cls, event: Event, user: User) -> None:
        if event.created_by_id != user.id and not user.is_superuser:
            raise PermissionDenied("Faqat tadbir yaratuvchisi o'chirishi mumkin")

        # DELETED bildirishnoma o'chirishdan OLDIN dispatch qilinadi
        # (Notification yozuvlari event_id ni bare UUID sifatida saqlaydi —
        # event row o'chgandan keyin ham audit trail sifatida qoladi).
        # WS push esa transaction commit'da yuboriladi.
        _dispatch_notification(event, NotificationType.DELETED)

        # Reminder'larni bekor qilish
        event_id = event.id
        transaction.on_commit(lambda: _cancel_reminders(event_id))

        # Fayllarni diskdan ham tozalash
        for att in list(event.files.all()) + list(event.protocols.all()):
            remove_attachment(att)

        event.delete()

    @staticmethod
    def upload_protocols(event: Event, files: list, user: User) -> int:
        """Tadbirga protokol biriktirish (PATCH /events/{id}/protocols/)."""
        # Production'da har qanday ishtirokchi qila oladi (JAR kodida @Authenticated)
        count = 0
        for f in files:
            att = secure_upload(f, target='protocols')
            att.protocol_event = event
            att.save(update_fields=['protocol_event'])
            count += 1
        return count


# Kalendar query mantig'i
def calendar_user_ids(user: User) -> list:
    """Joriy foydalanuvchi uchun kalendar tarkibi (pyramid hierarchy).

    Foydalanuvchi ko'radi:
    - O'zining tadbirlari
    - Barcha **quyi turuvchilarining** (rekursiv) tadbirlari

    Misol: Vazir → barcha tashkilot xodimlari ko'rinadi.
            Bo'lim boshlig'i → o'zi va bo'limining barcha xodimlari.
            Bosh mutaxassis → faqat o'zi (yordamchisi bo'lmasa).
    """
    ids = {user.id}
    frontier = {user.id}
    # BFS — har qadamda yangi level subordinate'larni topib qo'shamiz
    while frontier:
        subs = set(
            User.objects.filter(chief_id__in=frontier, enabled=True).values_list('id', flat=True),
        )
        new_ids = subs - ids
        if not new_ids:
            break
        ids.update(new_ids)
        frontier = new_ids
    return list(ids)


def calendar_for_vice(vice_id) -> list:
    """Vice ministrning kalendari (Premier shu paramda chaqirsa)."""
    return [vice_id]
