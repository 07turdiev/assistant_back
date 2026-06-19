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
from apps.users.models import User

from .booking import assert_no_conflict, sync_event_booking
from .models import Event, EventParticipant, HallBooking, Visitor

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


def _dispatch_notification_to(event, notification_type: str, only_user_ids) -> None:
    """Tadbir bildirishnomasini faqat tanlangan foydalanuvchilarga yuborish (delegatsiya)."""
    try:
        from apps.notifications.services import NotificationService
        NotificationService.dispatch_event(
            event, notification_type=notification_type, only_user_ids=only_user_ids,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(f'Targeted notification dispatch xatosi: {e}')


class EventService:
    """Tadbir yaratish/tahrirlash/o'chirish."""

    @staticmethod
    def _validate_in_future(event_date: date, end_time: time):
        end_dt = datetime.combine(event_date, end_time, tzinfo=timezone.get_current_timezone())
        if end_dt < timezone.now():
            raise ValidationError("Hozirgi vaqtdan oldin uchun topshiriq qo'shib bo'lmaydi")

    @staticmethod
    def _resolve_participants(participant_ids):
        if not participant_ids:
            return []
        users = list(User.objects.filter(pk__in=participant_ids))
        if len(users) != len(set(participant_ids)):
            found_ids = {str(u.id) for u in users}
            missing = set(map(str, participant_ids)) - found_ids
            raise ValidationError({'participant_ids': f"Foydalanuvchilar topilmadi: {missing}"})
        return users

    @staticmethod
    def _resolve_directions_and_heads(direction_ids):
        """Tanlangan bo'limlar → (directions, head'lar ro'yxati).

        Yuqori rollar bo'lim tanlaydi; har bo'limning `head` (ma'sul shaxsi) qatnashchi bo'ladi.
        """
        if not direction_ids:
            return [], []
        directions = list(Direction.objects.filter(pk__in=direction_ids).select_related('head'))
        heads = [d.head for d in directions if d.head_id and d.head and d.head.enabled]
        return directions, heads

    @staticmethod
    def _merge_participants(*user_lists):
        """Bir nechta ro'yxatdagi User'larni birlashtirib, takrorlanmaslarni qaytaradi."""
        seen, result = set(), []
        for lst in user_lists:
            for u in lst:
                if u and u.id not in seen:
                    seen.add(u.id)
                    result.append(u)
        return result

    @staticmethod
    def _resolve_on_behalf_of(user: User):
        """Kim nomidan: yordamchi yaratsa — uning rahbari (vazir/o'rinbosar); aks holda — o'zi."""
        from apps.users.delegation import resolve_principal
        return resolve_principal(user)

    @staticmethod
    def _resolve_direction(user: User, direction_id, fallback_directions=None):
        if direction_id:
            try:
                return Direction.objects.get(pk=direction_id)
            except Direction.DoesNotExist as exc:
                raise ValidationError({'direction_id': "Yo'nalish topilmadi"}) from exc
        if user.direction_id:
            return user.direction
        # Yuqori rollarda (VAZIR) bo'lim yo'q — tanlangan bo'limlardan birinchisini olamiz
        if fallback_directions:
            return fallback_directions[0]
        raise ValidationError("Yo'nalishni aniqlab bo'lmadi (bo'lim yoki xodim tanlang)")

    @staticmethod
    def _resolve_location(validated_data):
        """Manzil: hona tanlansa (hall) — vazirlik binosi; aks holda region/district (tashqi).

        Returns (hall, region, district). Hona tanlansa region/district e'tiborga olinmaydi.
        """
        from .models import Hall
        hall = region = district = None
        hall_id = validated_data.get('hall_id')
        if hall_id:
            try:
                hall = Hall.objects.get(pk=hall_id)
            except Hall.DoesNotExist as exc:
                raise ValidationError({'hall_id': 'Zal topilmadi'}) from exc
            return hall, None, None
        from apps.organisations.models import District, Region
        region_id = validated_data.get('region_id')
        district_id = validated_data.get('district_id')
        if region_id:
            region = Region.objects.filter(pk=region_id).first()
        if district_id:
            district = District.objects.filter(pk=district_id).first()
        return None, region, district

    @classmethod
    @transaction.atomic
    def create(cls, *, validated_data, files, user: User) -> Event:
        cls._validate_in_future(validated_data['date'], validated_data['end_time'])

        # Qatnashchilar: to'g'ridan-to'g'ri odamlar (boshliq tanlasa) + bo'limlar boshliqlari
        people = cls._resolve_participants(validated_data.get('participant_ids'))
        directions, dir_heads = cls._resolve_directions_and_heads(
            validated_data.get('participant_direction_ids'),
        )
        participants = cls._merge_participants(people, dir_heads)
        direction = cls._resolve_direction(user, validated_data.get('direction_id'), directions)

        # Manzil + zal bandligini tekshirish (zal bo'lsa to'qnashuv qattiq bloklanadi)
        hall, region, district = cls._resolve_location(validated_data)
        if hall is not None:
            assert_no_conflict(
                hall_id=hall.id, date=validated_data['date'],
                start_time=validated_data['start_time'], end_time=validated_data['end_time'],
            )

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
            on_behalf_of=cls._resolve_on_behalf_of(user),
            hall=hall,
            region=region,
            district=district,
        )

        # Zal bandligini yozish (tadbirga bog'langan bron)
        sync_event_booking(event)

        # Qatnashchilar (bo'lim boshliqlari + tanlangan odamlar)
        EventParticipant.objects.bulk_create([
            EventParticipant(event=event, user=u) for u in participants
        ])
        # Tanlangan bo'limlarni saqlash (ko'rsatish uchun)
        if directions:
            event.participant_directions.set(directions)

        # Visitors
        for v in validated_data.get('visitors') or []:
            Visitor.objects.create(event=event, **v)

        # Fayllar
        for f in files or []:
            att = secure_upload(f, target='documents')
            att.file_event = event
            att.save(update_fields=['file_event'])

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

        people = cls._resolve_participants(validated_data.get('participant_ids'))
        directions, dir_heads = cls._resolve_directions_and_heads(
            validated_data.get('participant_direction_ids'),
        )
        participants = cls._merge_participants(people, dir_heads)
        direction = cls._resolve_direction(user, validated_data.get('direction_id'), directions)

        # Manzil + zal bandligi (o'z bronini istisno qilib tekshiramiz)
        hall, region, district = cls._resolve_location(validated_data)
        if hall is not None:
            own_booking_id = (
                HallBooking.objects.filter(event_id=event.id)
                .values_list('pk', flat=True).first()
            )
            assert_no_conflict(
                hall_id=hall.id, date=validated_data['date'],
                start_time=validated_data['start_time'], end_time=validated_data['end_time'],
                exclude_booking_id=own_booking_id,
            )

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
        event.direction = direction
        event.hall = hall
        event.region = region
        event.district = district
        event.save()

        # Zal bronini yangilash/yaratish/o'chirish
        sync_event_booking(event)

        # Tanlangan bo'limlarni yangilash (ko'rsatish uchun)
        event.participant_directions.set(directions)

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
    def forward_to_subordinates(
        cls, event: Event, *, user: User, subordinate_ids=None, direction_ids=None,
    ) -> int:
        """Boshliq tadbirni o'z quyi xodimlari yoki quyi bo'limlariga yo'naltiradi.

        - Faqat tadbir qatnashchisi (yoki yaratuvchi/superuser) yo'naltira oladi
        - Xodimlar: faqat o'zining quyi xodimlari (chief=user)
        - Bo'limlar: faqat o'z bo'limidan past (MPTT descendants) — har birining boshlig'i
          qatnashchi bo'ladi (u keyin yana o'z quyi bo'limlariga yo'naltira oladi)
        - Yangi qo'shilganlargagina bildirishnoma yuboriladi
        """
        is_participant = event.participant_links.filter(user_id=user.id).exists()
        if not is_participant and event.created_by_id != user.id and not user.is_superuser:
            raise PermissionDenied("Faqat tadbir qatnashchisi yo'naltira oladi")

        seen = set(event.participants.values_list('id', flat=True))
        to_add: list = []

        # 1) To'g'ridan-to'g'ri xodimlar (chief=user)
        if subordinate_ids:
            for u in User.objects.filter(pk__in=subordinate_ids, chief_id=user.id, enabled=True):
                if u.id not in seen:
                    seen.add(u.id)
                    to_add.append(u)

        # 2) Quyi bo'limlar — boshlig'ini qatnashchi qilamiz (faqat o'z bo'limidan past)
        if direction_ids:
            dirs = list(
                Direction.objects.filter(pk__in=direction_ids).select_related('head'),
            )
            if user.direction_id:
                allowed = set(
                    Direction.objects.get_queryset_descendants(
                        Direction.objects.filter(pk=user.direction_id), include_self=False,
                    ).values_list('id', flat=True),
                )
                dirs = [d for d in dirs if d.id in allowed]
            for d in dirs:
                event.participant_directions.add(d)  # ko'rsatish uchun
                head = d.head if (d.head_id and d.head and d.head.enabled) else None
                if head and head.id not in seen:
                    seen.add(head.id)
                    to_add.append(head)

        if not to_add:
            return 0

        EventParticipant.objects.bulk_create([
            EventParticipant(event=event, user=u) for u in to_add
        ])

        add_ids = [u.id for u in to_add]
        transaction.on_commit(
            lambda: _dispatch_notification_to(event, NotificationType.NEW, add_ids),
        )
        return len(to_add)

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

    Delegatsiya: YORDAMCHI o'z rahbari (chief) kabi ko'radi — "ikkala hisob bir xil".
    """
    from apps.users.delegation import resolve_principal
    base = resolve_principal(user)  # yordamchi bo'lsa — boshliq qamrovi
    ids = {base.id, user.id}
    frontier = {base.id}
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
