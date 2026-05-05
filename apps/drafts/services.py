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

from .enums import DraftSource, DraftStatus
from .models import EventDraft, ReportDraft


# ---------- AI INTENT → DRAFT ----------

def create_event_draft_from_intent(
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
        is_important=bool(intent.get('is_important')),
        is_private=bool(intent.get('is_private')),
        notify_minutes_before=intent.get('notify_minutes_before') or [60, 1440],

        unresolved_participant_names=unresolved_names or [],

        assigned_to=assigned_to,
        target_direction=target_direction,
        speaker=assigned_to,  # default — keyin tahrirlanishi mumkin

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

    direction = draft.target_direction or (draft.speaker.direction if draft.speaker else None)
    if direction is None:
        raise ValidationError('Yo\'nalish (Direction) aniqlanmadi — speaker yoki target_direction kerak')

    event = Event.objects.create(
        title=draft.title,
        description=draft.description,
        date=draft.date,
        start_time=draft.start_time,
        end_time=draft.end_time,
        address=draft.location,
        sphere=draft.sphere,
        type=draft.event_type,
        is_important=draft.is_important,
        is_private=draft.is_private,
        direction=direction,
        speaker=draft.speaker,
        notify_time=draft.notify_minutes_before,
    )

    # Qatnashchilar — suggested + assigned_to
    participant_users = set(draft.suggested_participants.all())
    if draft.assigned_to:
        participant_users.add(draft.assigned_to)
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
        sender=draft.created_by,
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
    if not draft.speaker:
        missing.append('ma\'ruzachi (speaker)')
    if missing:
        raise ValidationError(
            'Tadbir qoralamasini joylash uchun quyidagilar to\'ldirilishi kerak: '
            + ', '.join(missing)
        )


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
