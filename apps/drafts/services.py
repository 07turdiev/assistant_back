"""Qoralamani Event/Report obyektiga aylantirish (publish) servisi.

Asosiy funksiyalar:
- `publish_event_draft(draft)` — EventDraft → Event
- `publish_report_draft(draft)` — ReportDraft → Report
- `create_event_draft_from_intent(...)` — AI parser natijasidan EventDraft yaratish
- `create_report_draft_from_intent(...)` — AI parser natijasidan ReportDraft yaratish
"""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.events.models import Event, EventParticipant
from apps.reports.models import Report
from apps.users.delegation import resolve_principal

from .enums import DraftSource, DraftStatus
from .models import EventDraft, ReportDraft


# ---------- AI INTENT → DRAFT ----------

def create_event_draft_from_intent(
    *,
    intent: dict[str, Any],
    created_by,
    assigned_to=None,
    target_direction=None,
    participant_directions=None,
    suggested_participants=None,
    unresolved_names: list[str] | None = None,
    raw_transcript: str = '',
    voice_file=None,
    source: str = DraftSource.VOICE_TELEGRAM,
) -> EventDraft:
    """AI parser chiqargan intent dict'idan EventDraft yaratadi.

    Args:
        intent: parse_intent() natijasi
        created_by: ovozli xabarni yuborgan foydalanuvchi
        assigned_to: tahrir qilib joylash kerak bo'lgan foydalanuvchi (resolver topgan)
        target_direction: agar bo'lim aytilgan bo'lsa
        suggested_participants: DB'da topilgan User obyektlari
        unresolved_names: DB'da topilmagan ismlar
        raw_transcript: STT chiqargan asl matn
        voice_file: ovoz fayl (Django File obyekti)
    """
    draft = EventDraft.objects.create(
        title=intent.get('title') or 'Sarlavhasiz',
        description=intent.get('description') or '',

        date=_parse_date(intent.get('date')),
        start_time=_parse_time(intent.get('start_time')),
        end_time=_parse_time(intent.get('end_time')),
        duration_minutes=intent.get('duration_minutes'),
        location=intent.get('location') or '',
        event_type=_map_event_type(intent.get('event_type')),
        # Soha — boshqariladigan ro'yxatdan yordamchi tahrirda tanlaydi
        sphere='',
        is_important=bool(intent.get('is_important')),
        is_private=bool(intent.get('is_private')),
        notify_minutes_before=intent.get('notify_minutes_before') or [60, 1440],

        unresolved_participant_names=unresolved_names or [],

        assigned_to=assigned_to,
        target_direction=target_direction,

        raw_transcript=raw_transcript,
        parsed_json=intent,
        source=source,
        voice_file=voice_file,

        # Bot HTTP middleware'siz ishlaydi — created_by ni qo'lda beramiz
        created_by=created_by,
        updated_by=created_by,
    )
    if suggested_participants:
        draft.suggested_participants.set(suggested_participants)
    # AI aniqlagan asosiy bo'lim + qatnashuvchi bo'lim/boshqarmalar — barchasi tanlangan ro'yxatga
    dirs: list = []
    seen_ids: set = set()
    for d in [target_direction, *(participant_directions or [])]:
        if d is not None and d.id not in seen_ids:
            dirs.append(d)
            seen_ids.add(d.id)
    if dirs:
        draft.target_directions.set(dirs)
    return draft


def create_report_draft_from_intent(
    *,
    intent: dict[str, Any],
    created_by,
    assigned_to=None,
    target_direction=None,
    suggested_participants=None,
    unresolved_names: list[str] | None = None,
    raw_transcript: str = '',
    voice_file=None,
    source: str = DraftSource.VOICE_TELEGRAM,
) -> ReportDraft:
    """AI parser chiqargan intent dict'idan ReportDraft yaratadi."""
    description = intent.get('description') or ''
    deadline_text = ''
    # `description` ichidan "N kun ichida" / "muddat ..." iborasini saqlab qo'yish
    for marker in ('kun ichida', 'kungacha', 'muddat'):
        if marker in description.lower():
            deadline_text = description
            break

    draft = ReportDraft.objects.create(
        title=intent.get('title') or 'Sarlavhasiz',
        description=description,
        is_important=bool(intent.get('is_important')),
        notify_minutes_before=intent.get('notify_minutes_before') or [60],

        unresolved_participant_names=unresolved_names or [],
        deadline_text=deadline_text,

        assigned_to=assigned_to,
        target_direction=target_direction,

        raw_transcript=raw_transcript,
        parsed_json=intent,
        source=source,
        voice_file=voice_file,

        # Bot HTTP middleware'siz ishlaydi — created_by ni qo'lda beramiz
        created_by=created_by,
        updated_by=created_by,
    )
    if suggested_participants:
        draft.suggested_participants.set(suggested_participants)
    return draft


# ---------- DRAFT → EVENT/REPORT (publish) ----------

@transaction.atomic
def publish_event_draft(draft: EventDraft) -> Event:
    """Tadbir qoralamasini Event obyektiga aylantiradi.

    Validatsiya:
    - status == PENDING_REVIEW
    - date, start_time, end_time, sphere, event_type, speaker majburiy
    - direction — draft.target_direction yoki speaker.direction'dan olinadi

    Joylangach:
    - draft.status = PUBLISHED
    - draft.published_event = yaratilgan Event
    - draft.published_at = now
    """
    if draft.status != DraftStatus.PENDING_REVIEW:
        raise ValidationError(f'Qoralama joylanmaydi — holati: {draft.status}')

    _validate_event_publish_requirements(draft)

    # Tanlangan bo'lim/boshqarmalar (tahrirda ko'p tanlanishi mumkin)
    selected_dirs = list(draft.target_directions.all())
    direction = (
        (selected_dirs[0] if selected_dirs else None)
        or draft.target_direction
        or (draft.created_by.direction if draft.created_by else None)
    )
    if direction is None:
        raise ValidationError('Yo\'nalish aniqlanmadi — kamida bitta bo\'lim yoki boshqarma tanlang')

    # Aytilgan manzilni vazirlik zaliga moslashtirish: nom mos kelsa — zal band qilinadi
    # (to'qnashuv qattiq bloklanadi), aks holda manzil oddiy matn (tashqi hudud) bo'lib qoladi.
    from apps.core.fuzzy import best_match
    from apps.events.booking import assert_no_conflict, sync_event_booking
    from apps.events.models import Hall
    loc = (draft.location or '').strip()
    hall = None
    if loc:
        # Avval aniq mos, so'ng fuzzy (foizli o'xshashlik) — AI nomi to'liq mos kelmasligi mumkin
        hall = Hall.objects.filter(name__iexact=loc).first()
        if hall is None:
            hall = best_match(loc, list(Hall.objects.all()), key=lambda h: h.name, threshold=0.5)
    if hall is not None:
        assert_no_conflict(
            hall_id=hall.id, date=draft.date,
            start_time=draft.start_time, end_time=draft.end_time,
        )

    event = Event.objects.create(
        title=draft.title,
        description=draft.description,
        date=draft.date,
        start_time=draft.start_time,
        end_time=draft.end_time,
        address='' if hall else loc,
        hall=hall,
        sphere=draft.sphere,
        type=draft.event_type,
        is_important=draft.is_important,
        is_private=draft.is_private,
        direction=direction,
        notify_time=draft.notify_minutes_before,
        # Ovozni yuborgan (vazir/o'rinbosar) nomidan — yordamchi joylasa ham.
        # resolve_principal: yaratuvchi yordamchi bo'lsa ham uning rahbariga keltiriladi.
        on_behalf_of=resolve_principal(draft.created_by),
    )

    # Zal tanlangan bo'lsa — bandlikni yozamiz (tadbirga bog'langan bron)
    sync_event_booking(event)

    # Qatnashuvchi bo'lim/boshqarmalar — HAR BIRINING boshlig'i tadbirga qatnashadi
    participant_users = set(draft.suggested_participants.all())
    dirs_for_event = selected_dirs or ([draft.target_direction] if draft.target_direction else [])
    if dirs_for_event:
        event.participant_directions.set(dirs_for_event)
        for d in dirs_for_event:
            head = d.head
            if head and head.enabled:
                participant_users.add(head)
    for user in participant_users:
        EventParticipant.objects.create(event=event, user=user)

    draft.status = DraftStatus.PUBLISHED
    draft.published_event = event
    draft.published_at = timezone.now()
    draft.save(update_fields=['status', 'published_event', 'published_at', 'updated_at'])
    return event


@transaction.atomic
def publish_report_draft(draft: ReportDraft) -> Report:
    """Topshiriq qoralamasini Report obyektiga aylantiradi."""
    if draft.status != DraftStatus.PENDING_REVIEW:
        raise ValidationError(f'Qoralama joylanmaydi — holati: {draft.status}')
    if not draft.assigned_to:
        raise ValidationError('Topshiriq oluvchisi (assigned_to) tanlanmagan')
    if not draft.description.strip():
        raise ValidationError('Topshiriq matni (description) bo\'sh')

    report = Report.objects.create(
        sender=resolve_principal(draft.created_by),
        receiver=draft.assigned_to,
        description=draft.description,
        notify_time=(draft.notify_minutes_before or [None])[0],
    )

    draft.status = DraftStatus.PUBLISHED
    draft.published_report = report
    draft.published_at = timezone.now()
    draft.save(update_fields=['status', 'published_report', 'published_at', 'updated_at'])
    return report


@transaction.atomic
def reject_draft(draft, reason: str = '') -> None:
    """Qoralamani rad etadi (Event/Report yaratmasdan)."""
    if draft.status != DraftStatus.PENDING_REVIEW:
        raise ValidationError(f'Qoralama rad etilmaydi — holati: {draft.status}')
    draft.status = DraftStatus.REJECTED
    draft.rejected_reason = reason or ''
    draft.save(update_fields=['status', 'rejected_reason', 'updated_at'])


# ---------- HELPERS ----------

def _validate_event_publish_requirements(draft: EventDraft) -> None:
    missing = []
    if not draft.date:
        missing.append('sana (date)')
    if not draft.start_time:
        missing.append('boshlanish vaqti (start_time)')
    if not draft.end_time:
        missing.append('tugash vaqti (end_time)')
    if not draft.sphere:
        missing.append('soha (sphere)')
    if not draft.event_type:
        missing.append('tadbir turi (event_type)')
    if missing:
        raise ValidationError(
            'Tadbir qoralamasini joylash uchun quyidagilar to\'ldirilishi kerak: '
            + ', '.join(missing)
        )


def _map_event_type(value) -> str:
    """AI bergan tadbir turini EventType qiymatiga moslaydi (aniq, label yoki fuzzy)."""
    if not value:
        return ''
    from apps.core.fuzzy import best_match
    from apps.info.enums import EventType
    val = str(value).strip()
    pairs = list(EventType.choices)  # (value, label)
    if val in {v for v, _ in pairs}:
        return val
    m = (best_match(val, pairs, key=lambda p: p[1], threshold=0.5)
         or best_match(val, pairs, key=lambda p: p[0], threshold=0.5))
    return m[0] if m else ''


def _parse_date(value):
    if not value:
        return None
    if hasattr(value, 'year'):
        return value
    from datetime import date as date_cls
    try:
        return date_cls.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_time(value):
    if not value:
        return None
    if hasattr(value, 'hour'):
        return value
    from datetime import time as time_cls
    try:
        return time_cls.fromisoformat(value)
    except (ValueError, TypeError):
        return None
